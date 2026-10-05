"""Run LeRobot's trainer, then upload the completed run if S3_BUCKET is set."""

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import boto3


def upload_checkpoint(output_dir: Path) -> None:
    bucket = os.environ.get("S3_BUCKET")
    if not bucket:
        print(f"Local checkpoint: {output_dir}")
        return
    client = boto3.client("s3", endpoint_url=os.environ["S3_ENDPOINT_URL"])
    prefix = os.environ.get("S3_PREFIX", "lerobot").strip("/")
    destination = f"{prefix}/{output_dir.name}" if prefix else output_dir.name
    for path in output_dir.rglob("*"):
        if path.is_file():
            key = f"{destination}/{path.relative_to(output_dir).as_posix()}"
            client.upload_file(str(path), bucket, key)
    print(f"Checkpoint uploaded to s3://{bucket}/{destination}/", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", choices=["act", "diffusion"], default="act")
    parser.add_argument("--dataset", default="lerobot/pusht")
    parser.add_argument("--steps", type=int, default=5000)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.steps < 1 or args.batch_size < 1 or not args.dataset.strip():
        parser.error("steps and batch size must be positive; dataset must not be empty")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    run_name = f"lerobot-{args.policy}-{args.dataset.replace('/', '-')}-{timestamp}"
    output_dir = args.output_dir or Path("outputs/train") / run_name
    if output_dir.exists():
        raise FileExistsError(f"use a new output directory: {output_dir}")
    output_dir.parent.mkdir(parents=True, exist_ok=True)

    print(f"Training {args.policy} on {args.dataset} for {args.steps} steps", flush=True)
    # The pinned LeRobot 0.5.1 package supplies this module and its configuration checks.
    subprocess.run(
        [
            sys.executable,
            "-m",
            "lerobot.scripts.lerobot_train",
            f"--policy.type={args.policy}",
            "--policy.push_to_hub=false",
            f"--dataset.repo_id={args.dataset}",
            f"--steps={args.steps}",
            f"--batch_size={args.batch_size}",
            f"--output_dir={output_dir}",
            "--wandb.enable=false",
        ],
        check=True,
    )

    checkpoints = list((output_dir / "checkpoints").glob("*/pretrained_model/model.safetensors"))
    if not checkpoints:
        raise FileNotFoundError(f"trainer did not save policy weights under {output_dir}")
    upload_checkpoint(output_dir)
    print("TRAINING COMPLETE", flush=True)


if __name__ == "__main__":
    main()
