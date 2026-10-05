"""Required uploads must preserve paths and propagate transfer failures."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
UPLOADERS = [
    ("life-science/openmm-simulation/sim/storage.py", "upload_results_to_s3"),
    ("robotics/lerobot-finetune-job/train/run.py", "upload_checkpoint"),
]


class UploadTests(unittest.TestCase):
    def test_upload_contract(self):
        for relative_path, function_name in UPLOADERS:
            with (
                self.subTest(script=relative_path),
                tempfile.TemporaryDirectory() as temporary,
            ):
                spec = importlib.util.spec_from_file_location(
                    "uploader", ROOT / relative_path
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                upload = getattr(module, function_name)
                run = Path(temporary) / "run-1"
                (run / "nested").mkdir(parents=True)
                artifact = run / "nested/result.txt"
                artifact.write_text("result")
                client = Mock()
                environment = {
                    "S3_BUCKET": "demo-bucket",
                    "S3_ENDPOINT_URL": "https://storage.eu-north1.nebius.cloud",
                    "S3_PREFIX": "/demo/",
                }
                with (
                    patch.dict(os.environ, environment, clear=True),
                    patch.object(module.boto3, "client", return_value=client),
                ):
                    upload(run)
                    client.upload_file.assert_called_once_with(
                        str(artifact), "demo-bucket", "demo/run-1/nested/result.txt"
                    )
                    client.upload_file.side_effect = RuntimeError("transfer failed")
                    with self.assertRaisesRegex(RuntimeError, "transfer failed"):
                        upload(run)
                # Local runs have no remote output contract; do not contact S3.
                with (
                    patch.dict(os.environ, {}, clear=True),
                    patch.object(module.boto3, "client") as create_client,
                ):
                    upload(run)
                    create_client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
