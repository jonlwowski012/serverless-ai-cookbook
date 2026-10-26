"""Exercise the reader-facing artifact check with real files and corrupted weights."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class VerifyTests(unittest.TestCase):
    def test_complete_corrupt_and_missing_marker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            weights = b"small deterministic weights"
            digest = hashlib.sha256(weights).hexdigest()
            checkpoint = root / "checkpoints/step-4"
            checkpoint.mkdir(parents=True)
            marker = checkpoint / "COMPLETE"
            marker.write_text("4\n")
            (root / "export").mkdir()
            model = root / "export/model.safetensors"
            model.write_bytes(weights)
            receipt = {"status": "trained", "optimizer_updates": 4, "checkpoint": "checkpoints/step-4",
                       "export": "export", "export_model_sha256": digest}
            (root / "TRAIN_COMPLETE.json").write_text(json.dumps(receipt))
            command = [sys.executable, str(ROOT / "scripts/verify.py"), str(root)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("PASS:", result.stdout)
            model.write_bytes(b"corrupted")
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("SHA-256 mismatch", result.stderr)
            model.write_bytes(weights)
            marker.unlink()
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
