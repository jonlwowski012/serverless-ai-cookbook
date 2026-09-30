---
title: Fine-tune FLUX 3 Action on DROID with eight Nebius GPUs
category: robotics
type: batch-job
runtime: nebius-ai-jobs
frameworks: [pytorch, huggingface]
keywords: [robotics, flux-action, droid, distributed-training, fsdp, serverless-jobs]
difficulty: advanced
---

# Fine-tune FLUX 3 Action on DROID

This cookbook runs the **full 30,000-update DROID fine-tune** on one Nebius AI Job with eight GPUs. `torchrun` launches eight ranks; the FLUX Action trainer shards the model across them with PyTorch FSDP2. A CPU job first stages the pinned public DROID success split and builds its index in a bucket. Training reads videos from that mounted bucket and publishes resumable checkpoints, metrics, and a final inference export there.

This directory can be copied into `serverless-ai-cookbook/robotics/` and built from there. The Dockerfile fetches [FLUX Action](https://github.com/black-forest-labs/flux-action) at commit `e2dd1d8dbc5977b54315d61f7548c63c043d6d4f`, with its own dependency lockfile. No local FLUX Action checkout or files outside this directory are needed. Docker build and the jobs need network access to the pinned source, Python packages, Hugging Face dataset, and model weights.

## Requirements and size

- Nebius CLI, Docker, and AWS CLI configured for your Nebius account; a project with Serverless AI Jobs, a subnet, a bucket, a Container Registry, and eight GPUs of one supported type.
- A region with a supported GPU platform: `gpu-rtx6000-a`, `gpu-b200-sxm-a`, `gpu-h200-sxm`, or `gpu-h100-sxm`. The GPU is selected by `NEBIUS_GPU_PLATFORM`; `job.sh` selects that platform's one- or eight-GPU preset. Available inventory is not guaranteed. `eu-south1` did not support Serverless AI Jobs when this recipe was prepared.
- Object Storage space for about **628 GB of source data**, a **1.2 GB index**, and approximately **42 GB per published checkpoint**. The recipe retains remote checkpoints so a new job can resume. Account for storage and GPU charges before submitting.
- Access to the [FLUX 3 Action base model](https://huggingface.co/black-forest-labs/flux-3-action-base). The dataset, filter, and model revisions are pinned in `stage_full.py` and `train.json`.

The training config uses one window per rank and two accumulation rounds: **16 windows per optimizer update**. It is a full parameter fine-tune, but this smaller batch differs from the 2,048-window reference recipe. It uses BF16 parameters, omits power EMAs, and exports the final raw model weights.

## 1. Configure resources

Work from this cookbook directory. Create a bucket and registry in the same project and region if needed:

```bash
nebius storage bucket create --profile YOUR_NEBIUS_PROFILE \
  --parent-id YOUR_PROJECT_ID --name YOUR_UNIQUE_BUCKET_NAME
nebius registry create --profile YOUR_NEBIUS_PROFILE \
  --parent-id YOUR_PROJECT_ID --name flux-action-droid
nebius registry configure-helper
```

Set the IDs returned by those commands and your project's subnet ID. Choose the region and GPU platform in the block **before** computing `NEBIUS_IMAGE`. The registry hostname uses the registry ID **without** `registry-`; the bucket mount uses the full `storagebucket-` ID.

```bash
export NEBIUS_PROFILE=YOUR_NEBIUS_PROFILE
export NEBIUS_PROJECT_ID=YOUR_PROJECT_ID
export NEBIUS_SUBNET_ID=YOUR_SUBNET_ID
export NEBIUS_REGION=uk-south2
export NEBIUS_BUCKET=YOUR_UNIQUE_BUCKET_NAME
export NEBIUS_BUCKET_ID=YOUR_STORAGEBUCKET_ID
export NEBIUS_REGISTRY_ID=YOUR_REGISTRY_ID
export NEBIUS_GPU_PLATFORM=gpu-rtx6000-a
export NEBIUS_IMAGE="cr.$NEBIUS_REGION.nebius.cloud/${NEBIUS_REGISTRY_ID#registry-}/flux-action-droid:$(date -u +%Y%m%dT%H%M%SZ)"
export NEBIUS_S3_ENDPOINT="https://storage.$NEBIUS_REGION.nebius.cloud"
export AWS_PROFILE=YOUR_AWS_PROFILE_WITH_NEBIUS_OBJECT_STORAGE_ACCESS
```

For an eight-B200 node, use `me-west1` and `gpu-b200-sxm-a` in that block, together with the me-west1 resource IDs. The image, bucket, project, and subnet must all belong to that region. Use a separate, region-local copy of the data for each training region.

## 2. Build the image

```bash
docker build --platform linux/amd64 -t "$NEBIUS_IMAGE" .
docker push "$NEBIUS_IMAGE"
```

The image includes this cookbook's stage script, training runner, and config. It does **not** include the dataset or model weights. Build and push can take several minutes because the CUDA/PyTorch image is large.

## 3. Stage and index DROID

The CPU job downloads the pinned `nvidia/Cosmos3-DROID` `success/` split, downloads the pinned `KarlP/droid` filter, and writes `full/source/` and `full/index/` into the bucket. The dataset is hundreds of GB; this is a real staging job, not a sample download.

```bash
bash job.sh stage dry-run
bash job.sh stage submit
```

Record the returned stage job ID, then wait for terminal `COMPLETED` and check its logs:

```bash
nebius ai job get STAGE_JOB_ID --profile "$NEBIUS_PROFILE"
nebius ai job logs STAGE_JOB_ID --profile "$NEBIUS_PROFILE" --tail 30
aws s3api head-object --bucket "$NEBIUS_BUCKET" \
  --key full/index/manifest.json --endpoint-url "$NEBIUS_S3_ENDPOINT"
aws s3api head-object --bucket "$NEBIUS_BUCKET" \
  --key full/index/rows.f32.npy --endpoint-url "$NEBIUS_S3_ENDPOINT"
```

Do not submit training until the stage job is `COMPLETED` and both index objects exist. If staging fails, inspect its logs; rerunning the stage job skips source files whose sizes already match. No GPU is used in this step.

If a bucket-mounted write fails with `OSError: [Errno 5] Input/output error`, test a direct `aws s3 cp` of a small file into that bucket. Nebius may report the underlying `QuotaLimitExceeded` error through S3 even when the mount only reports an I/O error. Free capacity or use a project with sufficient Object Storage quota before retrying.

## 4. Submit the eight-GPU training job

Use one run name for dry-run, submission, and artifact inspection:

```bash
export RUN_NAME="flux-droid-$(date -u +%Y%m%dT%H%M%SZ)"
bash job.sh train dry-run
bash job.sh train submit
```

The helper requires project inputs and selects the eight-GPU preset. The job checks its actual GPU names and rank count before training. It stages only the index on local disk, streams source videos from the mounted bucket, and checkpoints every 1,000 updates. The local 300 GiB disk is for model downloads, working state, and a checkpoint; it does not need to hold the 628 GB dataset.

Record the returned training job ID and monitor it:

```bash
nebius ai job get TRAIN_JOB_ID --profile "$NEBIUS_PROFILE"
nebius ai job logs TRAIN_JOB_ID --profile "$NEBIUS_PROFILE" --tail 20
```

The step logs report loss, global windows, step time, and GPU memory. A checkpoint is durable only once its `COMPLETE` marker is visible in the bucket. For example, after step 1,000:

```bash
aws s3api head-object --bucket "$NEBIUS_BUCKET" \
  --key "full/output/$RUN_NAME/step-1000/COMPLETE" \
  --endpoint-url "$NEBIUS_S3_ENDPOINT"
aws s3 cp "s3://$NEBIUS_BUCKET/full/output/$RUN_NAME/step-1000/COMPLETE" - \
  --quiet --endpoint-url "$NEBIUS_S3_ENDPOINT"
```

For a **completed** full run, require the Nebius job state `COMPLETED` and the final marker `full/output/$RUN_NAME/COMPLETE`, which contains `30000`. The output also contains `metrics.jsonl`, `train.json`, `step-N/` resumable checkpoints, and `export/` inference weights. Download the export with:

```bash
aws s3api head-object --bucket "$NEBIUS_BUCKET" \
  --key "full/output/$RUN_NAME/COMPLETE" \
  --endpoint-url "$NEBIUS_S3_ENDPOINT"
aws s3 cp "s3://$NEBIUS_BUCKET/full/output/$RUN_NAME/COMPLETE" - \
  --quiet --endpoint-url "$NEBIUS_S3_ENDPOINT"
aws s3 cp "s3://$NEBIUS_BUCKET/full/output/$RUN_NAME/export/" \
  "./export-$RUN_NAME/" --recursive --endpoint-url "$NEBIUS_S3_ENDPOINT"
python3 - <<'PY'
import hashlib
import json
import os
from pathlib import Path

folder = Path('export-' + os.environ['RUN_NAME'])
manifest = json.loads((folder / 'manifest.json').read_text())
for name, expected in manifest['sha256'].items():
    with (folder / name).open('rb') as stream:
        actual = hashlib.file_digest(stream, 'sha256').hexdigest()
    assert actual == expected, f'{name}: checksum mismatch'
    print(name, actual)
PY
```

The export is an offline model artifact; this cookbook does not measure robot task success. Keep `step-N/` for resume because the export has no optimizer state.

For a fresh-process check, submit a one-GPU job after the training job completes. It reads the published export, verifies its manifest, runs one DROID-shaped inference request, and publishes a finite `(1, 32, 8)` action tensor and report.

```bash
bash job.sh check dry-run
bash job.sh check submit
nebius ai job get CHECK_JOB_ID --profile "$NEBIUS_PROFILE"
aws s3 cp "s3://$NEBIUS_BUCKET/full/output/$RUN_NAME/check/report.json" - \
  --quiet --endpoint-url "$NEBIUS_S3_ENDPOINT"
```

Require terminal `COMPLETED` and `full/output/$RUN_NAME/check/COMPLETE`. This check uses a synthetic camera/state input to verify the inference path; it is not a policy-quality evaluation.

## Short end-to-end test

To validate the cookbook before the 30,000-update run, use a **separate bucket** with the same setup above. These modes keep the eight-rank, full-parameter model path but stage one pinned DROID file group and train for four updates. The smoke checkpoint and export still need tens of GB of Object Storage.

```bash
export NEBIUS_STAGE_MODE=sample
export NEBIUS_TRAIN_MODE=smoke
bash job.sh stage dry-run
bash job.sh stage submit
# Wait for the stage job to reach COMPLETED and verify both full/index objects.
export RUN_NAME="flux-droid-smoke-$(date -u +%Y%m%dT%H%M%SZ)"
bash job.sh train dry-run
bash job.sh train submit
# After training completes, run `bash job.sh check dry-run` and `bash job.sh check submit`.
```

For the smoke, require terminal `COMPLETED`, `full/output/$RUN_NAME/step-4/COMPLETE`, `full/output/$RUN_NAME/COMPLETE` containing `4`, and a verified `export/manifest.json` as shown above. Unset `NEBIUS_STAGE_MODE` and `NEBIUS_TRAIN_MODE` before following the full recipe in a different bucket.

If the eight-GPU preset is unavailable, set `NEBIUS_GPU_COUNT=1` before the train dry-run and submission. This uses the same full-parameter model and staged data on one supported GPU, with one window per update in smoke mode. Use a fresh `RUN_NAME`; the single-GPU checkpoint cannot resume an eight-rank run. The default remains eight GPUs. The inference check always uses one GPU.

## Resume and capacity failures

If training stops after a published checkpoint, reuse the **same** `RUN_NAME` and submit a new job. The runner restores the latest `step-N/COMPLETE` checkpoint and refuses to overwrite a run with a final `COMPLETE` marker. Keep the same code, model revisions, dataset, rank count, and config when resuming.

If Nebius reports `NotEnoughResources`, the job may end in `ERROR` before training starts. Check the terminal job state and provider message; a new submission is needed once that GPU preset has capacity. Do not interpret a successful dry-run as available GPU inventory.

## Files

- `Dockerfile`: pinned FLUX Action source and locked Python environment.
- `stage_full.py`: pinned full DROID download and index build.
- `train.json`: 30,000-step eight-rank training configuration.
- `run_full.py`: rank checks, staging, resume, checkpoint publication, and export.
- `check_export.py`: fresh-process inference and artifact publication.
- `job.sh`: CPU stage, eight-GPU train, and one-GPU export-check commands.

FLUX Action source is fetched under its upstream Apache-2.0 license. Model weights and datasets are separate downloads with their own terms.
