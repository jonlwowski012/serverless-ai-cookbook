---
title: RFD4-Proteina NVIDIA NIM
category: life-sciences
type: endpoint
runtime: gpu-h100-sxm
frameworks: [nvidia-nim]
keywords: [protein-design, rfd4]
difficulty: intermediate
---

# RFD4-Proteina NVIDIA NIM

<!-- factory:deploy -->

<a href="https://console.nebius.com/serverless/endpoint/create?image=nvcr.io%2Fnim%2Fipd%2Frfd4-proteina%40sha256%3Af4106e6b659aa53979d37c450c0c0cef620dcfce63934ef7e8e1268c5439b49a&amp;platform=gpu-h100-sxm&amp;preset=1gpu-16vcpu-200gb&amp;preemptible=false&amp;diskSize=200GiB&amp;targetPort=8000&amp;auth=true"><img src="../assets/create-endpoint.svg" alt="Create Endpoint" width="138" height="20"></a>

<!-- /factory:deploy -->

<!-- factory:intro -->

Serve NVIDIA's RFD4-Proteina NIM directly from NVCR and submit protein-design requests
from an Object Storage bucket. Follow the
[recipe](../../life-science/rfd4-proteina/nim/README.md) for secrets, bucket setup,
commands and expected outputs. The image is pulled directly from NVIDIA; no mirror or
rebuild is used.

**License:** the template code is Apache-2.0. The NIM image has its own
[governing terms](https://catalog.ngc.nvidia.com/orgs/nim/ipd/containers/rfd4-proteina/-/governing-terms)
and needs an NGC API key as a registry credential. Its checkpoint differs from the
public Hugging Face release.

<!-- /factory:intro -->

[Validation status](../../life-science/rfd4-proteina/validation.md).

<!-- factory:cli -->

## CLI alternative

Create the two MysteryBox secrets described in the
[recipe](../../life-science/rfd4-proteina/nim/README.md) first: one holding the NGC key
as `NGC_API_KEY`, `REGISTRY_PASSWORD` and `REGISTRY_USERNAME` (literal `$oauthtoken`),
and one holding your chosen `AUTH_TOKEN`.

```bash
export NEBIUS_PROJECT_ID='project-...'
export NEBIUS_SUBNET_ID='vpcsubnet-...'
export NGC_SECRET='<secret selector with the NGC key>'
export AUTH_TOKEN_SECRET='<secret selector with AUTH_TOKEN>'

nebius ai endpoint create \
  --parent-id "$NEBIUS_PROJECT_ID" \
  --name rfd4-proteina-nim \
  --image nvcr.io/nim/ipd/rfd4-proteina@sha256:f4106e6b659aa53979d37c450c0c0cef620dcfce63934ef7e8e1268c5439b49a \
  --public \
  --platform gpu-h100-sxm \
  --preset 1gpu-16vcpu-200gb \
  --container-port 8000 \
  --disk-size 200Gi \
  --subnet-id "$NEBIUS_SUBNET_ID" \
  --auth token \
  --token-secret "$AUTH_TOKEN_SECRET" \
  --registry-secret "$NGC_SECRET" \
  --env-secret "NGC_API_KEY=$NGC_SECRET" \
  --env NIM_ENABLE_QUEUE_METRICS=true \
  --env NIM_MAX_CONCURRENT_REQUESTS=1 \
  --env NIM_MAX_QUEUE_DEPTH=8 \
  --env NIM_QUEUE_TIMEOUT_SECONDS=60
```

The queue settings are admission limits, not a measured capacity. The image is large,
so first startup also downloads the NIM checkpoints before the endpoint reports ready.

> This contribution has not had live end-to-end acceptance yet; see the
> [validation status](../../life-science/rfd4-proteina/validation.md).

<!-- /factory:cli -->
