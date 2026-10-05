"""Upload a simulation directory when S3_BUCKET is configured."""

import os
from pathlib import Path

import boto3


def upload_results_to_s3(sim_dir: Path) -> None:
    bucket = os.environ.get("S3_BUCKET")
    if not bucket:
        print(f"Local results: {sim_dir}. Set S3_BUCKET to upload them.")
        return

    # boto3 reads AWS credentials and region from the environment.
    client = boto3.client("s3", endpoint_url=os.environ["S3_ENDPOINT_URL"])
    prefix = os.environ.get("S3_PREFIX", "openmm").strip("/")
    destination = f"{prefix}/{sim_dir.name}" if prefix else sim_dir.name
    for path in sim_dir.rglob("*"):
        if path.is_file():
            key = f"{destination}/{path.relative_to(sim_dir).as_posix()}"
            client.upload_file(str(path), bucket, key)
    # Upload exceptions propagate: a required output must not silently disappear.
    print(f"Results uploaded to s3://{bucket}/{destination}/", flush=True)
