---
title: Fine-tune an image classifier
category: training
type: job
runtime: gpu
frameworks: [transformers, datasets, torchvision]
keywords: [fine-tuning, image-classification, vit, object-storage]
difficulty: beginner
---

# Fine-tune an image classifier

Train a ViT classifier on a small public art-style dataset in a GPU Job. Save the model and one test-accuracy report to Object Storage so they survive Job completion. One epoch demonstrates the workflow; accuracy depends on your training recipe.

## Before you start

Complete the [CLI prerequisites](../../README.md#prerequisites). Configure the AWS CLI with [Object Storage credentials](https://docs.nebius.com/object-storage/interfaces/aws-cli). You need quota for one L40S GPU VM. Run commands from `training/image-classifier-finetuning`.

## Run

### 1. Set inputs and upload the scripts

Choose your subnet with `nebius vpc subnet list`. Set the region to match your project and use a fresh bucket name.

```bash
export SUBNET_ID="your-subnet-id"
export REGION="eu-north1"
export BUCKET_NAME="your-unique-classifier-bucket"
export RUN_NAME="classifier-$(date +%Y%m%d-%H%M%S)"
export STORAGE_URL="https://storage.$REGION.nebius.cloud"

nebius storage bucket create --name "$BUCKET_NAME"
export BUCKET_ID=$(nebius storage bucket get-by-name --name "$BUCKET_NAME" \
  --format jsonpath='{.metadata.id}')
aws --endpoint-url "$STORAGE_URL" s3 sync src/ "s3://$BUCKET_NAME/"
```

`src/config.yaml` selects a pinned [art-style dataset](https://huggingface.co/datasets/aleksandr-dzhumurat/art-genre-classification-slim), the pretrained model, batch size, and epoch count.

### 2. Start the training Job

```bash
nebius ai job create \
  --name "$RUN_NAME" --image pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel \
  --container-command bash --args "/mnt/data/start.sh" \
  --env "RUN_NAME=$RUN_NAME" --volume "$BUCKET_ID:/mnt/data:rw" \
  --platform gpu-l40s-a --preset 1gpu-8vcpu-32gb \
  --subnet-id "$SUBNET_ID" --disk-size 100Gi --timeout 1h

export JOB_ID=$(nebius ai job get-by-name --name "$RUN_NAME" \
  --format jsonpath='{.metadata.id}')
nebius ai job logs "$JOB_ID" --follow
nebius ai job get "$JOB_ID"
```

The public PyTorch image supplies torch and torchvision. `start.sh` installs the remaining pinned dependencies and runs `train.py`. The trainer saves to local scratch space, then copies finished files to the bucket mount; model serialization requires a local filesystem.

## Verify

Wait for the Job to reach `COMPLETED`. Logs print `Test accuracy` and the saved output directory. Download the result:

```bash
aws --endpoint-url "$STORAGE_URL" s3 sync \
  "s3://$BUCKET_NAME/output/$RUN_NAME/" "./output/$RUN_NAME/"
cat "output/$RUN_NAME/test_results.json"
```

`test_results.json` includes `test_accuracy`; `model/` contains weights, label mappings, and the image processor. Epoch checkpoints also remain in the run directory. The `COMPLETE` marker is written after all files have been copied. A completed Job plus these files confirms the workflow.

## Adapt and finish

Change the dataset, model, epochs, or batch size in `src/config.yaml`, upload it again, and use a new `RUN_NAME`. The demo expects `image`/`label` columns and `train`/`validation`/`test` splits. Adapt those accesses in `train.py` for a different dataset schema.

Delete the completed Job record. After keeping any outputs you need, remove the demo bucket:

```bash
nebius ai job delete "$JOB_ID"
aws --endpoint-url "$STORAGE_URL" s3 rm "s3://$BUCKET_NAME/" --recursive
nebius storage bucket delete "$BUCKET_ID"
```

If training runs out of memory, reduce the batch size. For startup or upload failures, inspect Job logs and check bucket access. The example writes one test report rather than reconstructing learning curves or exporting duplicate report formats.

## Validation

Checked on Nebius: one epoch completed, and a separate Job read back the saved weights, completion marker, and test report. Host-side AWS CLI uploads were not checked. See [validation notes](../../docs/validation.md).
