import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from launch import expand_sweep, job_command, job_id_from_output
from run import evaluate, main as run_case, upload


class RecipeTest(unittest.TestCase):
    def test_readme_download_checks(self):
        recipe = Path(__file__).resolve().parent
        blocks = re.findall(r"```bash\n(.*?)```", (recipe / "README.md").read_text(), re.S)
        block = next(block for block in blocks if "export RESULTS_DIR=" in block)
        target = [-0.4, 0.2, 0.02575]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source" / "case-000"
            source.mkdir(parents=True)
            (source / "COMPLETE").touch()
            result = {"run_id": "test-run", "case_id": "case-000", "controller_done": True,
                      "success": True, "final_cube_position_m": target,
                      "target_position_m": target, "xy_error_m": 0, "z_error_m": 0}
            frame = {"cube_position_m": target, "cube_orientation_wxyz": [1, 0, 0, 0],
                     "link_positions_m": [[0, 0, 0]]}
            recording = {"frames": [{**frame, "time_s": 0}, {**frame, "time_s": 1}]}
            binary = root / "bin"
            binary.mkdir()
            aws = binary / "aws"
            aws.write_text(f"#!{sys.executable}\nimport os, shutil, sys\n"
                           "if os.environ.get('FAIL_DOWNLOAD'): sys.exit(7)\n"
                           "shutil.copytree(os.environ['SOURCE'], os.environ['RESULTS_DIR'], dirs_exist_ok=True)\n")
            aws.chmod(0o755)
            env = {**os.environ, "PATH": f"{binary}:{os.environ['PATH']}",
                   "PYTHONPATH": str(recipe), "RUN_ID": "test-run", "CASE_COUNT": "1",
                   "SOURCE": str(source.parent), "S3_BUCKET": "test", "S3_ENDPOINT_URL": "https://example.invalid"}

            def check(expected_success, **changes):
                (source / "result.json").write_text(json.dumps({**result, **changes}))
                (source / "trajectory.json").write_text(json.dumps(recording))
                work = Path(tempfile.mkdtemp(dir=root))
                completed = subprocess.run(["bash", "-c", block], cwd=work, env=env,
                                           text=True, capture_output=True)
                self.assertEqual(completed.returncode == 0, expected_success, completed.stderr)
                return work

            work = check(True)
            stale = subprocess.run(["bash", "-c", block], cwd=work, env=env, capture_output=True)
            self.assertNotEqual(stale.returncode, 0)
            check(False, success=False)
            check(False, run_id="wrong-run")
            check(False, xy_error_m=1)
            recording["frames"][-1]["time_s"] = 0
            check(False)
            recording["frames"][-1]["time_s"] = 1
            recording["frames"][-1]["cube_orientation_wxyz"] = [2, 0, 0, 0]
            check(False)
            recording["frames"][-1]["cube_orientation_wxyz"] = [1, 0, 0, 0]
            (source / "COMPLETE").unlink()
            check(False)
            (source / "COMPLETE").touch()
            env["CASE_COUNT"] = "2"
            check(False)
            env["CASE_COUNT"] = "1"
            env["FAIL_DOWNLOAD"] = "1"
            check(False)

    def test_four_independent_jobs(self):
        points = expand_sweep(json.loads(Path(__file__).with_name("sweep.json").read_text()))
        self.assertEqual(points, [
            {"pick_x": 0.4, "place_y": 0.2},
            {"pick_x": 0.4, "place_y": 0.22},
            {"pick_x": 0.42, "place_y": 0.2},
            {"pick_x": 0.42, "place_y": 0.22},
        ])
        options = SimpleNamespace(
            image="example/image:tag", platform="gpu-l40s-a", preset="1gpu-8vcpu-32gb",
            timeout="2h", bucket="bucket", region="eu-north1", s3_secret="storage-keys",
            prefix="isaac-pick-place", subnet_id=None,
            profile=None, record_motion=False,
        )
        commands = [job_command(options, "run-1", f"case-{i:03d}", point) for i, point in enumerate(points)]
        self.assertEqual(len({command[command.index("--name") + 1] for command in commands}), 4)
        self.assertTrue(all(command.count("--env-secret") == 2 for command in commands))
        self.assertTrue(all("--args" in command for command in commands))
        self.assertTrue(all("--async" in command for command in commands))
        self.assertTrue(all("--container-command" not in command for command in commands))
        self.assertTrue(all("--inject-file" not in command for command in commands))
        self.assertTrue(all(command[command.index("--image") + 1] == options.image for command in commands))
        self.assertTrue(all("AWS_ACCESS_KEY_ID=storage-keys" in command for command in commands))
        self.assertTrue(all("AWS_SECRET_ACCESS_KEY=storage-keys" in command for command in commands))
        self.assertTrue(all("S3_ENDPOINT_URL=https://storage.eu-north1.nebius.cloud" in command for command in commands))
        self.assertTrue(all("/opt/isaac-sweep/run.py" not in command[command.index("--args") + 1] for command in commands))
        options.record_motion = True
        recorded = job_command(options, "run-1", "case-000", points[0])
        self.assertIn("--record-motion", recorded[recorded.index("--args") + 1])

    def test_task_success_needs_controller_and_final_pose(self):
        target = [-0.4, 0.2, 0.02575]
        self.assertTrue(evaluate(True, target, target)["success"])
        self.assertFalse(evaluate(False, target, target)["success"])
        self.assertFalse(evaluate(True, [-0.2, 0.2, 0.02575], target)["success"])
        self.assertFalse(evaluate(True, [float("nan"), 0.2, 0.02575], target)["success"])

    def test_cli_job_id_from_human_output(self):
        output = "Job ID: aijob-abc123\nJob created successfully.\nID: aijob-abc123\n"
        self.assertEqual(job_id_from_output(output), "aijob-abc123")

    def test_upload_marks_complete_last(self):
        calls = []
        client = SimpleNamespace(
            upload_file=lambda *args: calls.append(("result", args)),
            put_object=lambda **kwargs: calls.append(("complete", kwargs)),
        )
        env = {
            "S3_BUCKET": "bucket", "S3_ENDPOINT_URL": "https://storage.example",
            "AWS_DEFAULT_REGION": "eu-north1", "AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test",
            "S3_PREFIX": "isaac-pick-place",
        }
        with tempfile.TemporaryDirectory() as directory:
            result = Path(directory) / "result.json"
            result.write_text("{}")
            with patch.dict(os.environ, env), patch.dict(sys.modules, {"boto3": SimpleNamespace(client=lambda *a, **k: client)}):
                recording = Path(directory) / "trajectory.json"
                recording.write_text("{}")
                upload(result, "run-1", "case-000", recording)
        self.assertEqual([name for name, _ in calls], ["result", "result", "complete"])
        self.assertEqual(calls[0][1][2], "isaac-pick-place/run-1/case-000/trajectory.json")
        self.assertEqual(calls[1][1][2], "isaac-pick-place/run-1/case-000/result.json")
        self.assertEqual(calls[2][1]["Key"], "isaac-pick-place/run-1/case-000/COMPLETE")

    def test_upload_error_keeps_job_failed(self):
        closed = []
        app = SimpleNamespace(close=lambda: closed.append(True))
        env = {
            "S3_BUCKET": "bucket", "S3_ENDPOINT_URL": "https://storage.example",
            "AWS_DEFAULT_REGION": "eu-north1", "AWS_ACCESS_KEY_ID": "test",
            "AWS_SECRET_ACCESS_KEY": "test",
        }
        with tempfile.TemporaryDirectory() as directory:
            arguments = [
                "run.py", "--run-id", "run-1", "--case-id", "case-000",
                "--pick-x", "0.4", "--place-y", "0.2", "--output-dir", directory,
            ]
            with patch.dict(os.environ, env), patch.dict(sys.modules, {"isaacsim": SimpleNamespace(SimulationApp=lambda _: app)}):
                with patch.object(sys, "argv", arguments), patch("run.simulate", return_value={"success": True}):
                    with patch("run.upload", side_effect=RuntimeError("upload failed")):
                        with self.assertRaisesRegex(RuntimeError, "upload failed"):
                            run_case()
        self.assertEqual(closed, [])


if __name__ == "__main__":
    unittest.main()
