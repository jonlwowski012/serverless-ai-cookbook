---
title: Serve Qwen with vLLM
category: inference
type: endpoint
runtime: gpu
frameworks:
  - vllm
  - transformers
keywords:
  - llm
  - inference
  - openai-compatible
  - serving
difficulty: quickstart
---

# Serve Qwen with vLLM

Run Qwen3-0.6B behind an authenticated chat API. This uses an Endpoint because the model must stay loaded between requests.

## Before you start

Complete the [CLI prerequisites](../../README.md#prerequisites). Install `jq`; choose your project's subnet with `nebius vpc subnet list`. You need quota for one L40S GPU VM. The model is public, so a Hugging Face token is unnecessary.

## Run

```bash
export SUBNET_ID="your-subnet-id"
export MODEL_ID="Qwen/Qwen3-0.6B"
export ENDPOINT_NAME="qwen-demo-$(date +%Y%m%d-%H%M%S)"
export AUTH_TOKEN=$(openssl rand -hex 32)

nebius ai endpoint create \
  --name "$ENDPOINT_NAME" --image vllm/vllm-openai:v0.18.0-cu130 \
  --container-command "python3 -m vllm.entrypoints.openai.api_server" \
  --args "--model $MODEL_ID --host 0.0.0.0 --port 8000" \
  --platform gpu-l40s-a --preset 1gpu-8vcpu-32gb \
  --subnet-id "$SUBNET_ID" --container-port 8000 \
  --auth token --token "$AUTH_TOKEN" \
  --shm-size 16Gi --disk-size 100Gi

export ENDPOINT_ID=$(nebius ai endpoint get-by-name --name "$ENDPOINT_NAME" \
  --format jsonpath='{.metadata.id}')
nebius ai endpoint get "$ENDPOINT_ID"
nebius ai endpoint logs "$ENDPOINT_ID" --follow
```

Wait for model loading to finish, then press Ctrl-C to leave the log stream. The pinned image contains vLLM; the command downloads the model. Shared memory supports its worker processes. The container port is exposed through managed HTTPS.

## Verify

```bash
export ENDPOINT_URL=$(nebius ai endpoint get "$ENDPOINT_ID" --format json \
  | jq -r '.status.public_endpoints[] | select(startswith("https://"))' | head -1)
curl --fail-with-body "$ENDPOINT_URL/v1/models" \
  -H "Authorization: Bearer $AUTH_TOKEN"

curl --fail-with-body "$ENDPOINT_URL/v1/chat/completions" \
  -H "Authorization: Bearer $AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"$MODEL_ID\",\"messages\":[{\"role\":\"user\",\"content\":\"Say hello\"}],\"max_tokens\":128}" \
  | jq -r '.choices[0].message.content'
```

You should see the model ID followed by an assistant response. If the request fails, check the model name and Endpoint logs; startup includes downloading the weights.

## Adapt and finish

Change `MODEL_ID` for another vLLM-supported model. Larger models may require a different GPU and preset. Change the prompt in the request to use your own task.

Delete the Endpoint when finished to stop billing:

```bash
nebius ai endpoint delete "$ENDPOINT_ID"
```

See [Nebius Endpoint documentation](https://docs.nebius.com/serverless/endpoints/manage) for authentication, ports, and lifecycle options.

## Validation

Checked on Nebius: model listing, chat completion over HTTPS, and rejection of an unauthenticated request. See [validation notes](../../docs/validation.md).
