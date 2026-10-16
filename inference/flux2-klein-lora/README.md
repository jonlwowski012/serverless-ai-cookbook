---
title: Serve a FLUX.2 Klein LoRA on a Serverless Endpoint
category: inference
type: endpoint
runtime: gpu
frameworks:
  - diffusers
  - fastapi
  - pytorch
keywords:
  - flux
  - lora
  - image-generation
  - serverless-endpoint
  - b200
difficulty: advanced
---

# Serve a FLUX.2 Klein LoRA on a Serverless Endpoint

Build a standalone image containing your Diffusers-format LoRA adapter and
serve it with `black-forest-labs/FLUX.2-klein-base-4B` on a token-protected
Nebius Serverless AI Endpoint.

The adapter is not part of this repository. The build accepts it only through a
temporary BuildKit context, verifies the expected SHA-256 before and inside the
image, and leaves the file ignored by Git.

## What this example does

1. Builds a pinned PyTorch/Diffusers/FastAPI image with a verified LoRA.
2. Pushes a unique registry tag and records its immutable digest.
3. Creates a new endpoint without updating or deleting existing endpoints.
4. Waits for readiness and runs one deterministic 1024×1024 inference.
5. Deletes only the exact endpoint ID recorded in this example's state folder.

The API exposes:

- `GET /v1/health/ready`
- `POST /v1/inference/flux2-klein-base-4b-lora`

Inference returns an OpenAI-style `data[0].b64_json` PNG and
`metrics.model_time_ms`.

## Requirements and cost

- Docker with Buildx, `jq`, `openssl`, `crane`, and Python 3
- Nebius CLI authenticated with an explicit profile
- Container Registry repository and optional registry MysteryBox secret
- Hugging Face access to the gated base model and a MysteryBox secret whose
  payload contains `HF_TOKEN`
- A second MysteryBox secret whose payload contains `AUTH_TOKEN`
- A Diffusers-compatible FLUX.2 Klein base 4B LoRA and its trusted SHA-256

The default is one preemptible B200 (`gpu-b200-sxm`,
`1gpu-20vcpu-224gb`) with a 300 GiB disk. It incurs GPU, disk, and public
address charges until deleted. Preemptible instances are cheaper but can be
interrupted; set `PREEMPTIBLE=false` for production-like availability.
A preemptible endpoint follows the current spot price by default, with no cap:
the price can change every 15 minutes while it runs. To cap it, create a
[pricing policy](https://docs.nebius.com/signup-billing/manage-pricing-policy)
for the platform and set `SPOT_PRICING_POLICY_ID` to its ID.

The endpoint has one worker and serializes inference on its GPU. A reference
1024×1024, 20-step workload measured about 3.3 seconds serial latency on one
B200 and about 4.6 seconds on one H200, but adapter, image, prompt, and platform
changes require a new benchmark. Serverless endpoint replicas do not
automatically scale in this recipe.

## 1. Validate locally

Create an isolated environment and run the static/unit checks:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
./scripts/validate.sh
```

The unit tests use a fake model runtime and do not download model weights.

To build and import-test the public runtime stage without an adapter:

```bash
docker buildx build \
  --target runtime \
  --platform linux/amd64 \
  --provenance=false \
  --load \
  --tag flux2-klein-lora-runtime:test \
  .

docker run --rm \
  --entrypoint python \
  --env MEDIA_VERIFY_ADAPTER=0 \
  flux2-klein-lora-runtime:test \
  -c 'from diffusers import Flux2KleinPipeline; print(Flux2KleinPipeline.__name__)'
```

Expected output:

```text
Flux2KleinPipeline
```

## 2. Build and push the LoRA image

Authenticate Docker and `crane` to your registry first. Choose a unique tag;
the build script refuses `latest` and refuses to overwrite an existing tag.

```bash
export IMAGE_TAG="cr.<region>.nebius.cloud/<registry-id>/flux2-klein-lora:$(date -u +%Y%m%d%H%M%S)"
export ADAPTER_FILE="/secure/path/adapter.safetensors"
export ADAPTER_SHA256="<trusted-sha256-from-the-training-output-owner>"

./scripts/build-image.sh \
  --image "$IMAGE_TAG" \
  --adapter-file "$ADAPTER_FILE" \
  --adapter-sha256 "$ADAPTER_SHA256" \
  --push
```

`build-metadata.json` contains the pushed image digest and adapter digest, but
not the adapter or credentials. Configure deployment with the immutable image:

```bash
export IMAGE="$(jq -r '.image + "@" + .digest' build-metadata.json)"
```

## 3. Configure the endpoint

Use secret selectors, never literal Hugging Face or endpoint tokens:

```bash
export NEBIUS_PROFILE="<profile>"
export PROJECT_ID="<project-id>"
export IMAGE="<registry/repository@sha256:digest>"
export HF_TOKEN_SECRET_SELECTOR="<secret-id>@<version-id>"
export AUTH_TOKEN_SECRET_SELECTOR="<secret-id>@<version-id>"

# Optional when the profile/project has no suitable default subnet:
export SUBNET_ID="<subnet-id>"

# Optional for private registries. The secret payload must contain
# REGISTRY_USERNAME and REGISTRY_PASSWORD.
export REGISTRY_SECRET_SELECTOR="<secret-id>@<version-id>"

# Keep state outside the checkout and use a fresh directory per endpoint.
export STATE_DIR="/secure/flux2-klein-lora-state"
```

The endpoint auth secret must contain the token value you will also place in a
mode-0600 file for the smoke test. The script never reads or prints that value.

Adapter-specific settings are configurable:

```bash
export LORA_ADAPTER_NAME="<adapter-name>"
export LORA_SCALE="1.0"
export MODEL_SLUG="flux2-klein-base-4b-lora"
```

Keep `MODEL_ID=black-forest-labs/FLUX.2-klein-base-4B`. The similarly named
`black-forest-labs/FLUX.2-klein-4B` is distilled; using it for a LoRA trained
against the base model can materially change output.

Review the non-mutating deployment intent:

```bash
./scripts/deploy-endpoint.sh --dry-run | jq
```

## 4. Deploy

```bash
./scripts/deploy-endpoint.sh
```

The script generates a unique name, creates a new endpoint, recursively redacts
token/secret fields from displayed JSON, records the endpoint ID under
`STATE_DIR`, and waits for `RUNNING`. It never stops, updates, or replaces an
existing endpoint.

## 5. Smoke-test

Create a token file without exposing the token in command arguments:

```bash
umask 077
read -rsp 'Endpoint token: ' ENDPOINT_TOKEN
printf '%s' "$ENDPOINT_TOKEN" > /secure/flux2-endpoint-token
unset ENDPOINT_TOKEN
```

In the endpoint details, copy the public HTTPS tunnel URL and keep the exact
FQDN. Do not use the IP address in `status.public_endpoints`: HTTP access over
public IPs is being retired. The URL has this form (copy it rather than
constructing it):

```bash
export ENDPOINT_URL="https://port8000-<endpoint-tunnel-id>.tunnel.applications.<region>.nebius.cloud"
```

Run readiness plus one image generation. Use a prompt appropriate for your
adapter, including its trigger token when applicable. The smoke-test rejects
non-HTTPS and IP-address base URLs before reading the token file:

```bash
python3 scripts/smoke-test.py \
  --base-url "$ENDPOINT_URL" \
  --token-file /secure/flux2-endpoint-token \
  --model-slug "$MODEL_SLUG" \
  --adapter-name "$LORA_ADAPTER_NAME" \
  --prompt "<your adapter trigger>, a subject suitable for this LoRA" \
  --output-dir /secure/flux2-smoke-output
```

Expected readiness fields:

```json
{
  "ready": true,
  "slug": "flux2-klein-base-4b-lora",
  "kind": "image_diffusers",
  "model_id": "black-forest-labs/FLUX.2-klein-base-4B",
  "device": "cuda",
  "lora_adapter_name": "adapter",
  "lora_fused": true,
  "lora_scale": 1.0
}
```

The output directory contains `health.json`, `payload.json`,
`inference-summary.json`, and `output.png`. Inspect the PNG; successful HTTP and
PNG checks prove serving health, while visual inspection proves that the chosen
adapter has the intended effect.

## 6. Cleanup

Read the exact ID, then pass it back as confirmation:

```bash
export ENDPOINT_ID="$(cat "$STATE_DIR/endpoint-id")"
./scripts/delete-endpoint.sh --confirm "$ENDPOINT_ID"
rm -f /secure/flux2-endpoint-token
```

The delete script removes local endpoint state only after the service reports
`NotFound`. Authentication or permission errors are failures, not successful
cleanup.

## Adaptation

- H200: set `PLATFORM=gpu-h200-sxm` and
  `PRESET=1gpu-16vcpu-200gb`.
- Non-preemptible: set `PREEMPTIBLE=false`.
- Capped spot price: set `SPOT_PRICING_POLICY_ID=<pricing policy ID>`; without
  it, preemptible endpoints follow the spot price.
- Private endpoint: set `PUBLIC=false` and run the smoke test from a network
  path that can reach it.
- Different trigger/scale: change `LORA_ADAPTER_NAME`, `LORA_SCALE`, and the
  smoke prompt, then validate the output again.
- Replacement: deploy to a new `STATE_DIR`, validate the new endpoint, switch
  clients, and delete the old exact ID only after approval.

## Troubleshooting

- `401`/`403`: confirm that the token file contains the same `AUTH_TOKEN` value
  as the endpoint auth secret. Do not bypass authentication.
- Endpoint `ERROR` before container logs: verify registry access, the immutable
  digest, subnet egress, disk size, and MysteryBox selectors.
- Model download failure: confirm gated-model access and the `HF_TOKEN` secret.
- Adapter load failure: confirm Diffusers key format, base-model compatibility,
  and the trusted adapter digest.
- Photorealistic or otherwise unexpected output: first confirm the undistilled
  `FLUX.2-klein-base-4B` model, then compare LoRA and no-LoRA outputs using the
  same seed and payload.
- Slow startup: the base model is large; keep the 300 GiB disk and allow up to
  one hour for the first pull/load.

The adapter, auth token, Hugging Face token, registry credentials, raw endpoint
JSON, and smoke output are intentionally excluded from Git.
