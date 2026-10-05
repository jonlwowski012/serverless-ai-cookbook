---
title: First Job
category: quickstarts
type: job
runtime: gpu
frameworks:
  - nebius-cli
keywords:
  - jobs
  - gpu
  - nvidia-smi
difficulty: quickstart
---

# Run your first GPU Job

Run `nvidia-smi` in a Job to check GPU visibility. A Job runs its command once and releases compute when it finishes. Allow several minutes for startup.

## Before you start

Complete the [CLI prerequisites](../README.md#prerequisites). You need project editor access and quota for one L40S GPU VM. Run `nebius vpc subnet list` to choose a subnet in that project.

## Run

```bash
export SUBNET_ID="your-subnet-id"
export JOB_NAME="first-job-$(date +%Y%m%d-%H%M%S)"

nebius ai job create \
  --name "$JOB_NAME" \
  --image nvidia/cuda:13.1.1-runtime-ubuntu24.04 \
  --container-command bash --args "-c nvidia-smi" \
  --platform gpu-l40s-a --preset 1gpu-8vcpu-32gb \
  --subnet-id "$SUBNET_ID" --timeout 1h

export JOB_ID=$(nebius ai job get-by-name --name "$JOB_NAME" \
  --format jsonpath='{.metadata.id}')
nebius ai job get "$JOB_ID"
nebius ai job logs "$JOB_ID" --follow
```

The platform selects the GPU type; its matching preset selects the number of GPUs, CPUs, and memory. The timeout caps runtime; the Job stops earlier when `nvidia-smi` exits.

## Verify

After the command finishes, check `nebius ai job get "$JOB_ID"` for `COMPLETED`. Logs should contain the NVIDIA GPU table, including the GPU name and driver version. A running Job alone does not prove completion.

## Adapt and finish

Replace the image and command to run your own batch task. Files written to the container disk disappear when the Job finishes; mount Object Storage for durable results, as shown in [Train and Serve](../training/train-and-serve/README.md).

Optionally delete the completed Job record:

```bash
nebius ai job delete "$JOB_ID"
```

If the Job cannot start, check quota and subnet availability. If it exits with an error, inspect its logs. See the [official Job quickstart](https://docs.nebius.com/serverless/quickstart/jobs) for platform details.

## Validation

Checked on Nebius: the L40S Job completed and logged the GPU table. See [validation notes](../docs/validation.md).
