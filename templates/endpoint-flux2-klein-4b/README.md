# FLUX.2 Klein 4B

<!-- factory:deploy -->

<a href="https://console.nebius.com/serverless/endpoint/create?image=vllm%2Fvllm-omni%3Av0.24.0%40sha256%3A566d89d7eaba08dd313dab2464e67fe984825d281c77437582e3008a917bbf7c&amp;command=vllm+serve+black-forest-labs%2FFLUX.2-klein-4B+--omni+--host+0.0.0.0+--port+8000+--revision+e7b7dc27f91deacad38e78976d1f2b499d76a294&amp;targetPort=8000&amp;platform=gpu-l40s-a&amp;preset=1gpu-16vcpu-64gb&amp;diskSize=500GiB&amp;preemptible=false&amp;auth=true"><img src="../assets/create-endpoint.svg" alt="Create Endpoint" width="138" height="20"></a>

<!-- /factory:deploy -->

<!-- factory:intro -->

Black Forest Labs' **FLUX.2 Klein distilled 4B** generates images from text and edits reference images with the same model. This template serves both through vLLM-Omni's OpenAI-style Images API on one NVIDIA L40S.

**License:** [Apache-2.0](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B/blob/main/LICENSE.md) · **Source:** [Model card](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B) · [Black Forest Labs](https://github.com/black-forest-labs/flux2)

<!-- /factory:intro -->

## What you get

| Workflow | Route | Input and output |
| --- | --- | --- |
| Text-to-image | `POST /v1/images/generations` | JSON prompt → base64 PNG |
| Image editing | `POST /v1/images/edits` | Multipart reference image + instruction → base64 PNG |
| Model readiness | `GET /v1/models` | Loaded model information |

The default uses four sampling steps and guidance 1.0, matching the distilled model's [sampling example](https://huggingface.co/black-forest-labs/FLUX.2-klein-4B#using-with-diffusers-). It is not the base model or a LoRA deployment; see the [adapter-specific example](../../inference/flux2-klein-lora/README.md) for that workflow.

The deploy link selects **one L40S, 16 vCPUs, 64 GiB RAM, a 500 GiB disk, token authentication, and on-demand compute**. Before creating it, set shared memory to **16 GiB** in the console's advanced settings. Select a project and subnet with L40S capacity. The public weights are ungated; an HF token is optional for authenticated Hub downloads. Keep any token in the console's secret configuration, never in committed commands.

## Test request

Run these commands from a fresh local working directory. Copy the managed HTTPS URL from the endpoint's **Public endpoints** and use the token generated in the create form. Endpoint authentication is separate from a Hugging Face token.

```bash
export BASE_URL='https://YOUR_ENDPOINT_HOST'
export TOKEN='YOUR_ENDPOINT_AUTH_TOKEN'
AUTH=(-H "Authorization: Bearer $TOKEN")
```

### Wait for the model

Nebius can show RUNNING while weights are downloading or the pipeline is initializing. The loop below makes at most 80 attempts, with a ten-second timeout per attempt. Stop and inspect logs if it times out; do not create a duplicate endpoint.

```bash
ready=false
for attempt in {1..80}; do
  if curl --fail --silent --show-error --max-time 10 "${AUTH[@]}" \
    "$BASE_URL/v1/models" -o models.json; then
    ready=true
    break
  fi
  sleep 15
done
[ "$ready" = true ] || { echo 'Model readiness timed out; inspect endpoint logs.' >&2; exit 1; }
python3 -m json.tool models.json
```

### Text-to-image

```bash
set -euo pipefail
curl --fail-with-body --silent --show-error --max-time 55 \
  "$BASE_URL/v1/images/generations" "${AUTH[@]}" \
  -H 'Content-Type: application/json' -o generation.json -d '{
    "model": "black-forest-labs/FLUX.2-klein-4B",
    "prompt": "A studio photograph of a red ceramic teapot on a light wooden table, plain cream background, soft daylight, no text.",
    "size": "1024x1024", "n": 1, "response_format": "b64_json",
    "num_inference_steps": 4, "guidance_scale": 1.0, "seed": 42
  }'
python3 -c 'import base64,json; p=json.load(open("generation.json")); b=base64.b64decode(p["data"][0]["b64_json"],validate=True); assert b.startswith(b"\x89PNG\r\n\x1a\n"); open("klein-generated.png","wb").write(b)'
```

Open `klein-generated.png` before using it as the editing reference.

### Image editing

This uses the generated image as its reference, so no external sample download is required. Replace the path with your own PNG or JPEG to edit another image. The image is a multipart upload, not a JSON URL.

```bash
set -euo pipefail
curl --fail-with-body --silent --show-error --max-time 55 \
  "$BASE_URL/v1/images/edits" "${AUTH[@]}" -o editing.json \
  --form-string 'model=black-forest-labs/FLUX.2-klein-4B' \
  --form-string 'prompt=Change the red teapot to blue. Keep its shape, the wooden table, the background, lighting and camera angle unchanged.' \
  -F 'image=@klein-generated.png;type=image/png' \
  --form-string 'size=1024x1024' --form-string 'n=1' \
  --form-string 'response_format=b64_json' --form-string 'num_inference_steps=4' \
  --form-string 'guidance_scale=1.0' --form-string 'seed=42'
python3 -c 'import base64,json; p=json.load(open("editing.json")); b=base64.b64decode(p["data"][0]["b64_json"],validate=True); assert b.startswith(b"\x89PNG\r\n\x1a\n"); open("klein-edited.png","wb").write(b)'
```

Compare the two files. A valid PNG establishes an API response; inspect the images to assess prompt following and preservation of the reference scene.

### Python

Install `requests` in your local Python environment, then run the equivalent requests after readiness:

```python
import base64
import os
from pathlib import Path
import requests

base = os.environ["BASE_URL"].rstrip("/")
headers = {"Authorization": f"Bearer {os.environ['TOKEN']}"}
params = {"model": "black-forest-labs/FLUX.2-klein-4B", "size": "1024x1024",
          "n": 1, "response_format": "b64_json", "num_inference_steps": 4,
          "guidance_scale": 1.0, "seed": 42}
response = requests.post(f"{base}/v1/images/generations", headers=headers,
    json={**params, "prompt": "A red ceramic teapot on a wooden table, studio photograph."}, timeout=55)
response.raise_for_status()
Path("python-generated.png").write_bytes(base64.b64decode(response.json()["data"][0]["b64_json"], validate=True))
with open("python-generated.png", "rb") as image:
    response = requests.post(f"{base}/v1/images/edits", headers=headers,
        data={**params, "prompt": "Change only the red teapot to blue."},
        files={"image": ("reference.png", image, "image/png")}, timeout=55)
response.raise_for_status()
Path("python-edited.png").write_bytes(base64.b64decode(response.json()["data"][0]["b64_json"], validate=True))
```

## Observed results

Tested on **2026-10-28** on one on-demand L40S with the exact image and CLI command below. Both README clients passed generation and editing; all four responses fully decoded as 1024×1024 PNGs. Missing and invalid bearer tokens returned HTTP 401. No Hugging Face token was used.

| Request | Observed client wall time | Output |
| --- | --- | --- |
| curl generation, four steps | 3.0 s | 1024² PNG, 3.15 MB |
| curl edit, four steps | 5.7 s | 1024² PNG, 3.15 MB |
| Python generation, different prompt | 2.8 s | 1024² PNG |
| Python edit | 12.2 s | 1024² PNG |

These are individual example requests, not a latency or throughput benchmark. curl times include JSON/base64 decoding; Python times cover the HTTP call and response transfer. Cold startup took **16.8 minutes**, including allocation retries, image pulling and model initialization. The runtime reported **14.87 GiB** for model loading and **15.36 GiB** of process GPU memory after loading; these are not inference peaks. Cost and peak host RAM were not measured.

| Generated reference | Instruction: change the red teapot to blue |
| --- | --- |
| ![Red teapot generated by the cloud endpoint](samples/klein-generated.png) | ![Edited blue teapot preserving the reference scene](samples/klein-edited.png) |

Both pairs were visually checked. The test endpoint and its GPU VM were deleted, with NotFound confirmed for each. [Sanitized validation record and output hashes](validation.json).

<!-- factory:cli -->

## CLI alternative

Use an authenticated CLI profile whose default project has L40S quota. Add `--subnet-id YOUR_SUBNET_ID` if that project has multiple subnets. The public image needs no private registry credentials.

```bash
nebius ai endpoint create \
  --name flux2-klein-4b \
  --image vllm/vllm-omni:v0.24.0@sha256:566d89d7eaba08dd313dab2464e67fe984825d281c77437582e3008a917bbf7c \
  --public --platform gpu-l40s-a --preset 1gpu-16vcpu-64gb \
  --container-port 8000 --shm-size 16Gi --disk-size 500Gi \
  --auth token --container-command vllm \
  --args "serve black-forest-labs/FLUX.2-klein-4B --omni --host 0.0.0.0 --port 8000 --revision e7b7dc27f91deacad38e78976d1f2b499d76a294"
```

The CLI generates and prints the endpoint bearer token once. Save it privately; never commit CLI output containing tokens or resource identifiers. The image is pinned to vLLM-Omni **v0.24.0** by digest. No custom Docker build is required. The command requests a model revision, but this release's Klein loader does not apply it to every component. Treat the observed Hub revision as provenance, rather than a guarantee of fully pinned model weights.

<!-- /factory:cli -->

Run local contract checks without a GPU:

```bash
python3 -m unittest discover -s templates/endpoint-flux2-klein-4b/tests -v
```

Run that command from the repository root. The tests exercise README requests against a stub API; they do not prove model execution.

## Cost and cleanup

This template uses on-demand compute. GPU, disk and public-IP charges continue while it is running; deleting the test endpoint is part of the workflow. Copy its exact ID from the create result, then delete only that endpoint:

```bash
nebius ai endpoint delete YOUR_ENDPOINT_ID
nebius ai endpoint get YOUR_ENDPOINT_ID
```

The second command should return NotFound after deletion completes. Download any outputs you need before deleting; the container disk is disposable. If you choose preemptible compute in the console, configure its pricing policy there and expect interruptions and lost in-flight requests.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| RUNNING but `502` or connection failure | Wait for `/v1/models`; inspect endpoint logs for downloads, initialization or OOM. |
| `401` or `403` | Send the endpoint bearer token; an HF token does not authenticate this endpoint. |
| Model download throttled | Configure an HF token through a secret and check outbound Hub access. |
| Out of memory | Keep the one-L40S configuration, one image per request and 1024² dimensions; inspect logs before increasing workload or changing compute. |
| Timeout or `504` | The public gateway has a finite response window. The request may still be running; inspect logs before retrying. The examples cap client requests at 55 seconds. |
| Edit fails validation | Use multipart `image=@path`, a valid PNG/JPEG and the exact model ID. |
| Unchanged or distorted edit | Review the prompt and reference. A passing HTTP request does not guarantee the requested visual change. |
