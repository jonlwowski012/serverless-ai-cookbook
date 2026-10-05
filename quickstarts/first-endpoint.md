---
title: First Endpoint
category: quickstarts
type: endpoint
runtime: cpu
frameworks:
  - nebius-cli
  - nginx
keywords:
  - endpoint
  - auth
  - token
difficulty: quickstart
---

# Serve an authenticated nginx Endpoint

Deploy nginx and request its welcome page over HTTPS. An Endpoint keeps serving requests until you stop or delete it.

## Before you start

Complete the [CLI prerequisites](../README.md#prerequisites). Install `jq` and use `nebius vpc subnet list` to choose a subnet. You need project editor access and quota for one CPU VM.

## Run

```bash
export SUBNET_ID="your-subnet-id"
export ENDPOINT_NAME="nginx-$(date +%Y%m%d-%H%M%S)"
export AUTH_TOKEN=$(openssl rand -hex 32)

nebius ai endpoint create \
  --name "$ENDPOINT_NAME" --image nginx:alpine \
  --platform cpu-d3 --preset 4vcpu-16gb \
  --subnet-id "$SUBNET_ID" --container-port 80 \
  --auth token --token "$AUTH_TOKEN"

export ENDPOINT_ID=$(nebius ai endpoint get-by-name --name "$ENDPOINT_NAME" \
  --format jsonpath='{.metadata.id}')
nebius ai endpoint get "$ENDPOINT_ID"
nebius ai endpoint logs "$ENDPOINT_ID" --follow
```

Wait for the Endpoint to run, then press Ctrl-C to leave the log stream. `--container-port` exposes nginx through a managed HTTPS URL. `--auth token` requires the bearer token on requests. A separate public IP is unnecessary.

## Verify

```bash
export ENDPOINT_URL=$(nebius ai endpoint get "$ENDPOINT_ID" --format json \
  | jq -r '.status.public_endpoints[] | select(startswith("https://"))' | head -1)
curl --fail-with-body "$ENDPOINT_URL" -H "Authorization: Bearer $AUTH_TOKEN"
curl -i "$ENDPOINT_URL"
```

The authenticated request returns the nginx welcome page (HTTP 200). The request without a token returns HTTP 401 or 403.

## Adapt and finish

Replace the image with your serving application and change the container port to match its listening port. Keep the bearer token in your client; do not commit it.

Delete the Endpoint when finished to stop billing:

```bash
nebius ai endpoint delete "$ENDPOINT_ID"
```

If startup fails, check Endpoint logs. If the HTTPS URL is missing, wait for the Endpoint to run and get it again. See the [official Endpoint quickstart](https://docs.nebius.com/serverless/quickstart/endpoints).

## Validation

The commands were checked against the CLI and documentation; this nginx Endpoint was not deployed during this change. See [validation notes](../docs/validation.md).
