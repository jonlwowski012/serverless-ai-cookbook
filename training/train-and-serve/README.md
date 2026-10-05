---
title: Train and Serve TinyLlama with Serverless
category: training
type: workflow
runtime: gpu
frameworks:
  - pytorch
  - transformers
  - vllm
keywords:
  - finetuning
  - lora
  - object-storage
  - endpoint
difficulty: intermediate
---

# Fine-tune TinyLlama, then serve the adapter

Use a GPU Job to fine-tune TinyLlama on 32 instruction examples, save the LoRA adapter to Object Storage, and load it in a vLLM Endpoint. The bucket is the handoff between the two resources. This small run demonstrates the workflow; it does not establish model quality.

## Before you start

Complete the [CLI prerequisites](../../README.md#prerequisites). You need `jq`, the AWS CLI configured with [Object Storage credentials](https://docs.nebius.com/object-storage/interfaces/aws-cli), and quota for one L40S GPU VM. Run commands from `training/train-and-serve`.

### 1. Set your inputs and create a bucket

Use your configured CLI project. Pick its subnet with `nebius vpc subnet list`, and set the storage region to match your project.

```bash
export SUBNET_ID="your-subnet-id"
export REGION="eu-north1"
export BUCKET_NAME="your-unique-demo-bucket"
export RUN_NAME="tinyllama-$(date +%Y%m%d-%H%M%S)"
export STORAGE_URL="https://storage.$REGION.nebius.cloud"

nebius storage bucket create --name "$BUCKET_NAME"
export BUCKET_ID=$(nebius storage bucket get-by-name --name "$BUCKET_NAME" \
  --format jsonpath='{.metadata.id}')

for file in fine_tune.py start.sh serve.sh; do
  aws --endpoint-url "$STORAGE_URL" s3 cp "$file" "s3://$BUCKET_NAME/$file"
done
```

### 2. Train in a Job

```bash
nebius ai job create \
  --name "$RUN_NAME" \
  --image pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel \
  --container-command bash --args "/mnt/data/start.sh" \
  --env "RUN_NAME=$RUN_NAME" --volume "$BUCKET_ID:/mnt/data:rw" \
  --platform gpu-l40s-a --preset 1gpu-8vcpu-32gb \
  --subnet-id "$SUBNET_ID" --disk-size 100Gi --timeout 1h

export JOB_ID=$(nebius ai job get-by-name --name "$RUN_NAME" \
  --format jsonpath='{.metadata.id}')
nebius ai job logs "$JOB_ID" --follow
nebius ai job get "$JOB_ID"
```

`start.sh` installs pinned dependencies in the public PyTorch image, then runs the trainer on one GPU. Model serialization uses local scratch space; the script copies finished files to the read/write bucket mount at `/mnt/data`. Each fresh `RUN_NAME` gets its own output directory.

Wait for the Job to reach `COMPLETED`. Logs end with `TRAINING COMPLETE`. Check the saved adapter before serving it:

```bash
aws --endpoint-url "$STORAGE_URL" s3 ls \
  "s3://$BUCKET_NAME/output/$RUN_NAME/tinyllama-lora/"
```

The output includes `adapter_config.json`, `adapter_model.safetensors`, tokenizer files, and `eval_results.json`. A `COMPLETE` marker is written after copying all files; serving checks it before loading. These are adapter weights; serving also needs the TinyLlama base model.

### 3. Load the adapter in an Endpoint

```bash
export ENDPOINT_NAME="$RUN_NAME-serve"
export AUTH_TOKEN=$(openssl rand -hex 32)

nebius ai endpoint create \
  --name "$ENDPOINT_NAME" --image vllm/vllm-openai:v0.7.3 \
  --container-command bash --args "/mnt/data/serve.sh" \
  --env "RUN_NAME=$RUN_NAME" --volume "$BUCKET_ID:/mnt/data:ro" \
  --platform gpu-l40s-a --preset 1gpu-8vcpu-32gb \
  --subnet-id "$SUBNET_ID" --container-port 8000 --disk-size 100Gi \
  --auth token --token "$AUTH_TOKEN"

export ENDPOINT_ID=$(nebius ai endpoint get-by-name --name "$ENDPOINT_NAME" \
  --format jsonpath='{.metadata.id}')
nebius ai endpoint get "$ENDPOINT_ID"
nebius ai endpoint logs "$ENDPOINT_ID" --follow
```

Wait for the model to finish loading, then press Ctrl-C to leave the logs. Serving mounts the same bucket read-only and exposes port 8000 through managed HTTPS.

### 4. Verify inference with the trained adapter

```bash
export ENDPOINT_URL=$(nebius ai endpoint get "$ENDPOINT_ID" --format json \
  | jq -r '.status.public_endpoints[] | select(startswith("https://"))' | head -1)

curl --fail-with-body "$ENDPOINT_URL/v1/models" \
  -H "Authorization: Bearer $AUTH_TOKEN"

curl --fail-with-body "$ENDPOINT_URL/v1/completions" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"tinyllama_adapter","prompt":"### Instruction:\nExplain object storage in one sentence.\n\n### Response:\n","max_tokens":64}' \
  | jq -r '.choices[0].text'
```

`/v1/models` should list `tinyllama_adapter`, and the completion request should return text. The adapter name selects the trained weights rather than the base model alone.

## Adapt and finish

Edit `start.sh` to pass `--max-samples` or `--num-epochs` for a longer run. Use a new `RUN_NAME` each time. Changing the base model requires updating both the training input and `serve.sh`; the adapter must match its base model.

Delete the Endpoint to stop billing. Remove the demo bucket only after downloading any outputs you want to keep:

```bash
nebius ai endpoint delete "$ENDPOINT_ID"
nebius ai job delete "$JOB_ID"
aws --endpoint-url "$STORAGE_URL" s3 sync "s3://$BUCKET_NAME/output/$RUN_NAME/" "./output/$RUN_NAME/"
aws --endpoint-url "$STORAGE_URL" s3 rm "s3://$BUCKET_NAME/" --recursive
nebius storage bucket delete "$BUCKET_ID"
```

If training fails, read Job logs. If vLLM cannot load the adapter, check that training completed and `RUN_NAME` matches the saved directory. See the [Job guide](https://docs.nebius.com/serverless/jobs/manage) and [Endpoint guide](https://docs.nebius.com/serverless/endpoints/manage) for resource settings.

## Validation

Checked on Nebius: the 32-example training Job, durable adapter readback, and authenticated inference using `tinyllama_adapter`. Host-side AWS CLI uploads were not checked. See [validation notes](../../docs/validation.md).
