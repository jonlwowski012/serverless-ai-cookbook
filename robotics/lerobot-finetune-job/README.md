---
title: Fine-tune a LeRobot Policy with Nebius AI Jobs
category: robotics
type: batch-job
runtime: nebius-ai-jobs
frameworks: [lerobot, pytorch, huggingface]
keywords: [robotics, fine-tuning, act-policy, diffusion-policy, serverless-jobs, s3]
difficulty: intermediate
---

# Fine-tune a LeRobot policy in a GPU Job

Train an ACT policy on the public PushT dataset, then upload its checkpoint to Object Storage. The Job finishes after training; uploading makes the result available after its container disk is removed. This demo shows the workflow, not a task-success benchmark.

## Before you start

Complete the [CLI prerequisites](../../README.md#prerequisites). You need Docker, the AWS CLI with [Object Storage credentials](https://docs.nebius.com/object-storage/interfaces/aws-cli), an existing bucket, a container registry you can push to, and quota for one H100 GPU VM. Run commands from `robotics/lerobot-finetune-job`.

## Run

### 1. Build the example image

Build from the current source so the image contains the simplified runner and pinned LeRobot 0.5.1 runtime. Use a fresh tag in your registry:

```bash
export IMAGE="your-registry/lerobot-demo:your-new-tag"
docker build --platform linux/amd64 -t "$IMAGE" .
docker push "$IMAGE"
```

The Dockerfile installs LeRobot and its system dependencies. `train/run.py` calls LeRobot's supported training entry point and uploads the completed run; it exposes only policy, dataset, steps, batch size, and output directory.

### 2. Configure storage and submit

Choose your subnet with `nebius vpc subnet list`. Set the region to match your bucket. AWS credentials come from your configured shell; do not put keys in this repository.

```bash
export SUBNET_ID="your-subnet-id"
export AWS_ACCESS_KEY_ID="your-object-storage-access-key"
export AWS_SECRET_ACCESS_KEY="your-object-storage-secret-key"
export AWS_DEFAULT_REGION="eu-north1"
export S3_ENDPOINT_URL="https://storage.$AWS_DEFAULT_REGION.nebius.cloud"
export S3_BUCKET="your-existing-bucket"
export S3_PREFIX="lerobot-demo"

aws --endpoint-url "$S3_ENDPOINT_URL" s3 ls "s3://$S3_BUCKET/"
bash scripts/run_serverless.sh act lerobot/pusht 100
```

The helper creates one H100 Job with a six-hour limit and passes storage settings to the container. The short 100-step run verifies the workflow. The helper prints the Job ID, status/log commands, and exact output prefix. For shared environments, use [secret references](https://docs.nebius.com/serverless/jobs/manage) in place of passing credentials through `--env`.

## Verify

Run the printed log and status commands. Wait for `COMPLETED`. Logs should contain `Checkpoint uploaded to s3://...` and `TRAINING COMPLETE`. Upload errors fail the Job.

Copy the output URI from the logs:

```bash
export OUTPUT_URI="s3://your-bucket/lerobot-demo/your-run-name/"
aws --endpoint-url "$S3_ENDPOINT_URL" s3 sync "$OUTPUT_URI" ./checkpoint/
```

A saved policy lives under `checkpoints/<step>/pretrained_model/` with `config.json` and `model.safetensors`. To check that an ACT checkpoint loads, replace `<step>` with a downloaded checkpoint directory:

```bash
docker run --rm --platform linux/amd64 --entrypoint python \
  -v "$PWD/checkpoint:/checkpoint:ro" "$IMAGE" \
  -m train.eval /checkpoint/checkpoints/<step>/pretrained_model
```

This checks loading, not rollout performance.

## Adapt and finish

Change the helper's dataset and step arguments for your own compatible data. To use Diffusion, pass `diffusion` as the first argument. Use the upstream [LeRobot configuration](https://huggingface.co/docs/lerobot) for evaluation, tracking, or advanced training rather than adding another configuration layer to this runner. The reference [ACT config](configs/act_pusht.yaml) shows upstream fields.

For a short local CPU run with files retained on your host:

```bash
bash scripts/run_docker.sh act lerobot/pusht 50
```

Delete the completed Job record using its printed ID. Remove only this run's artifacts when you no longer need them:

```bash
nebius ai job delete <job-id>
aws --endpoint-url "$S3_ENDPOINT_URL" s3 rm "$OUTPUT_URI" --recursive
```

If training fails, inspect Job logs and dataset compatibility. If upload fails, check bucket access and the S3 endpoint. If GPU quota is unavailable, select a platform and matching preset available in your project in `scripts/run_serverless.sh`.

## Validation

Checked locally: the image built, one ACT/PushT CPU training update saved a checkpoint, and the evaluation command loaded it. GPU training and real S3 upload were not rerun. See [validation notes](../../docs/validation.md).
