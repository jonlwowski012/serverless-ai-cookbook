"""Verify a published export in a fresh one-GPU job."""

import json
import os
import re
import shutil
from pathlib import Path

import numpy as np
import torch

from flux_action.config import PolicyConfig
from flux_action.inference.offline import run_inference


def main():
    run_name = os.environ["RUN_NAME"]
    check_name = os.environ.get("CHECK_NAME", "check")
    for name in (run_name, check_name):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
            raise ValueError(f"invalid output name: {name}")
    if not torch.cuda.is_available():
        raise RuntimeError("inference check requires a GPU")
    expected = os.environ.get("EXPECTED_GPU_NAME", "")
    actual = torch.cuda.get_device_name(0)
    if expected.lower() not in actual.lower():
        raise RuntimeError(f"expected {expected}, got {actual}")

    output = Path("/workspace/data/full/output") / run_name
    if not (output / "COMPLETE").is_file():
        raise FileNotFoundError("training run has no final COMPLETE marker")
    destination = output / check_name
    if destination.exists():
        raise FileExistsError(destination)
    work = Path("/workspace/run")
    shutil.copytree(output / "export", work / "export", copy_function=shutil.copyfile)
    config = PolicyConfig(**json.loads((work / "export/config.json").read_text()))
    observation = {camera: np.zeros((360, 640, 3), dtype=np.uint8) for camera in config.camera_order}
    observation["state"] = np.zeros(config.action_dim, dtype=np.float32)
    np.savez(work / "observation.npz", **observation)
    report = run_inference(
        work / "export", work / "observation.npz", work / "check",
        task="pick up the object", device="cuda",
        settings={
            "sampler": "cosmos_unipc",
            "num_inference_steps": 4,
            "sampler_shift": 5.0,
            "guidance_scale": 4.0,
            "guidance_scale_action": 1.0,
            "n_action_steps": 32,
        },
    )
    if report["actions_shape"] != [1, 32, 8]:
        raise ValueError(f"unexpected action shape: {report['actions_shape']}")
    destination.mkdir()
    for name in ("actions.npy", "report.json"):
        source = work / "check" / name
        target = destination / name
        shutil.copyfile(source, target)
        if target.stat().st_size != source.stat().st_size:
            raise ValueError(f"incomplete copy: {target}")
    (destination / "COMPLETE").write_text("1\n")
    print(f"Verified export on {actual}: {report['actions_shape']}", flush=True)


if __name__ == "__main__":
    main()
