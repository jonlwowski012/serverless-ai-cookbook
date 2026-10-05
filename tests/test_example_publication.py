"""Check that completion markers are written only after every artifact is copied."""

import ast
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
TRAINERS = [
    "training/train-and-serve/fine_tune.py",
    "training/image-classifier-finetuning/src/train.py",
]


def load_publisher(path):
    # Exercise the filesystem stage without installing GPU training libraries.
    source = ast.parse(path.read_text())
    function = next(
        node
        for node in source.body
        if isinstance(node, ast.FunctionDef) and node.name == "publish_output"
    )
    namespace = {"Path": Path, "shutil": shutil}
    exec(
        compile(ast.Module(body=[function], type_ignores=[]), str(path), "exec"),
        namespace,
    )
    return namespace["publish_output"]


class PublicationTests(unittest.TestCase):
    def test_publication_contract(self):
        for trainer in TRAINERS:
            with (
                self.subTest(script=trainer),
                tempfile.TemporaryDirectory() as temporary,
            ):
                source = Path(temporary) / "local"
                destination = Path(temporary) / "bucket/run"
                (source / "nested").mkdir(parents=True)
                (source / "nested/weights.bin").write_bytes(b"model weights")
                publish = load_publisher(ROOT / trainer)
                with patch(
                    "shutil.copyfile", side_effect=OSError("bucket write failed")
                ):
                    with self.assertRaisesRegex(OSError, "bucket write failed"):
                        publish(source, destination)
                self.assertFalse((destination / "COMPLETE").exists())
                publish(source, destination)
                self.assertEqual(
                    (destination / "nested/weights.bin").read_bytes(), b"model weights"
                )
                self.assertTrue((destination / "COMPLETE").is_file())


if __name__ == "__main__":
    unittest.main()
