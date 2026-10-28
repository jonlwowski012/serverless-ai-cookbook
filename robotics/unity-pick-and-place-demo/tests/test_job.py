"""Exercise submission and the actual README download block without cloud access."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class JobTests(unittest.TestCase):
    def test_submission_profile_dry_run_and_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stub = root / 'nebius'
            stub.write_text(f'#!{sys.executable}\nimport json,os,sys\n'
                            'json.dump(sys.argv[1:],open(os.environ["ARGS_FILE"],"w"))\n'
                            'raise SystemExit(int(os.environ.get("STUB_EXIT","0")))\n')
            stub.chmod(0o755)
            env = os.environ | {'PATH': str(root) + os.pathsep + os.environ['PATH'],
                'NEBIUS_PROFILE': 'test-profile', 'NEBIUS_PROJECT_ID': 'project-test',
                'NEBIUS_SUBNET_ID': 'subnet-test', 'NEBIUS_BUCKET_ID': 'bucket-test',
                'NEBIUS_IMAGE': 'example.invalid/ur3:test', 'RUN_ID': 'test-run',
                'ARGS_FILE': str(root / 'args.json')}
            for mode in ('dry-run', 'submit'):
                result = subprocess.run(['bash', str(ROOT / 'scripts/job.sh'), mode],
                                        env=env, text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                args = json.loads((root / 'args.json').read_text())
                self.assertEqual(args[args.index('--profile') + 1], 'test-profile')
                self.assertEqual(args[args.index('--parent-id') + 1], 'project-test')
                self.assertEqual(args[args.index('--subnet-id') + 1], 'subnet-test')
                self.assertIn('--dry-run' if mode == 'dry-run' else '--async', args)
                self.assertEqual('Submitted:' in result.stdout, mode == 'submit')
                if mode == 'submit':
                    self.assertIn('unity-articulations/test-run/result.json', result.stdout)
                    self.assertIn('--profile "test-profile"', result.stdout)
            result = subprocess.run(['bash', str(ROOT / 'scripts/job.sh'), 'submit'],
                                    env=env | {'STUB_EXIT': '7'}, text=True, capture_output=True)
            self.assertEqual(result.returncode, 7)
            self.assertNotIn('Submitted:', result.stdout)
            (root / 'args.json').unlink()
            result = subprocess.run(['bash', str(ROOT / 'scripts/job.sh'), 'submit'],
                                    env=env | {'RUN_ID': '../bad'}, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / 'args.json').exists())

    def test_readme_rejects_stale_results_and_stops_on_remote_failure(self):
        block = re.search(r'## 4\. Download.*?```bash\n(.*?)```',
                          (ROOT / 'README.md').read_text(), re.S).group(1)
        for case in ('existing_results', 'download_failure', 'job_failure'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'bin').mkdir()
                (root / 'check.py').write_text('print("CHECKER_CALLED")')
                for name, body in {'nebius': 'exit "$NEBIUS_STATUS"',
                                   'aws': 'echo AWS_CALLED; exit 1'}.items():
                    path = root / 'bin' / name
                    path.write_text('#!/bin/sh\n' + body + '\n')
                    path.chmod(0o755)
                if case == 'existing_results':
                    (root / 'results/test-run').mkdir(parents=True)
                    (root / 'results/test-run/result.json').write_text('{"success":true}')
                env = os.environ | {'PATH': str(root / 'bin') + os.pathsep + os.environ['PATH'],
                    'NEBIUS_STATUS': '1' if case == 'job_failure' else '0',
                    'NEBIUS_PROFILE': 'test', 'JOB_ID': 'test', 'RUN_ID': 'test-run',
                    'NEBIUS_BUCKET': 'test', 'NEBIUS_S3_ENDPOINT': 'https://example.invalid'}
                result = subprocess.run(['bash'], input=block, text=True, cwd=root,
                                        env=env, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('CHECKER_CALLED', result.stdout)
                if case != 'download_failure':
                    self.assertNotIn('AWS_CALLED', result.stdout)


if __name__ == '__main__':
    unittest.main()
