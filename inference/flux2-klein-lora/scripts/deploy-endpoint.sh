#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  echo "usage: configure the documented environment variables, then run $0 [--dry-run]" >&2
}

dry_run=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) dry_run=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage; exit 2 ;;
  esac
done

: "${NEBIUS_CLI:=/usr/local/bin/nebius}"
: "${NEBIUS_PROFILE:?NEBIUS_PROFILE is required}"
: "${PROJECT_ID:?PROJECT_ID is required}"
: "${IMAGE:?IMAGE is required}"
: "${HF_TOKEN_SECRET_SELECTOR:?HF_TOKEN_SECRET_SELECTOR is required}"
: "${AUTH_TOKEN_SECRET_SELECTOR:?AUTH_TOKEN_SECRET_SELECTOR is required}"
: "${ENDPOINT_NAME_PREFIX:=flux2-klein-lora}"
: "${PLATFORM:=gpu-b200-sxm}"
: "${PRESET:=1gpu-20vcpu-224gb}"
: "${PREEMPTIBLE:=true}"
: "${SPOT_PRICING_POLICY_ID:=}"
: "${DISK_SIZE:=300Gi}"
: "${SHM_SIZE:=16Gi}"
: "${PUBLIC:=true}"
: "${SUBNET_ID:=}"
: "${REGISTRY_SECRET_SELECTOR:=}"
: "${MODEL_ID:=black-forest-labs/FLUX.2-klein-base-4B}"
: "${MODEL_SLUG:=flux2-klein-base-4b-lora}"
: "${LORA_ADAPTER_NAME:=adapter}"
: "${LORA_SCALE:=1.0}"
: "${DEFAULT_STEPS:=20}"
: "${DEFAULT_GUIDANCE_SCALE:=3.5}"
: "${DEFAULT_MAX_SEQUENCE_LENGTH:=256}"
: "${WAIT_TIMEOUT_SECONDS:=3600}"
: "${STATE_DIR:=${XDG_STATE_HOME:-$HOME/.local/state}/flux2-klein-lora}"

[[ "$IMAGE" =~ @sha256:[0-9a-f]{64}$ ]] || {
  echo "IMAGE must use an immutable sha256 digest" >&2
  exit 2
}
[[ "$MODEL_ID" == "black-forest-labs/FLUX.2-klein-base-4B" ]] || {
  echo "MODEL_ID must remain the undistilled FLUX.2 Klein base model" >&2
  exit 2
}
[[ "$PREEMPTIBLE" == "true" || "$PREEMPTIBLE" == "false" ]] || {
  echo "PREEMPTIBLE must be true or false" >&2
  exit 2
}
[[ "$PUBLIC" == "true" || "$PUBLIC" == "false" ]] || {
  echo "PUBLIC must be true or false" >&2
  exit 2
}

# Preemptible endpoints must pick a pricing model: cap the hourly price with a
# pricing policy, or follow the current spot price (no cap).
if [[ "$PREEMPTIBLE" != "true" ]]; then
  pricing="on-demand"
elif [[ -n "$SPOT_PRICING_POLICY_ID" ]]; then
  pricing="spot-pricing-policy"
else
  pricing="follows-spot-price"
fi

redact_endpoint_json() {
  jq 'walk(if type == "object" then with_entries(select(.key | test("token|secret|password|credential|private_key"; "i") | not)) else . end)'
}

suffix="$(date -u +%Y%m%d%H%M%S)-$(openssl rand -hex 2)"
endpoint_name="${ENDPOINT_NAME_PREFIX}-${suffix}"
endpoint_name=${endpoint_name:0:63}

if $dry_run; then
  jq -n \
    --arg profile "$NEBIUS_PROFILE" \
    --arg project_id "$PROJECT_ID" \
    --arg name "$endpoint_name" \
    --arg image "$IMAGE" \
    --arg platform "$PLATFORM" \
    --arg preset "$PRESET" \
    --argjson preemptible "$PREEMPTIBLE" \
    --arg pricing "$pricing" \
    --argjson public "$PUBLIC" \
    '{dry_run:true,profile:$profile,project_id:$project_id,name:$name,image:$image,platform:$platform,preset:$preset,preemptible:$preemptible,pricing:$pricing,public:$public,auth:"token",secrets:"configured; values and selectors redacted"}'
  exit 0
fi

command -v "$NEBIUS_CLI" >/dev/null || { echo "Nebius CLI not found" >&2; exit 1; }
for command in jq openssl; do
  command -v "$command" >/dev/null || { echo "missing command: $command" >&2; exit 1; }
done

umask 077
mkdir -p -- "$STATE_DIR"
chmod 0700 "$STATE_DIR"
if [[ -e "$STATE_DIR/endpoint-id" ]]; then
  echo "STATE_DIR already owns an endpoint; use a new directory for replacements" >&2
  exit 1
fi

temp_dir=$(mktemp -d "${TMPDIR:-/tmp}/flux2-klein-lora-endpoint.XXXXXX")
cleanup() {
  # shellcheck disable=SC2317
  rm -rf -- "$temp_dir"
}
trap cleanup EXIT

args=(
  ai endpoint create
  --profile "$NEBIUS_PROFILE"
  --parent-id "$PROJECT_ID"
  --name "$endpoint_name"
  --image "$IMAGE"
  --platform "$PLATFORM"
  --preset "$PRESET"
  --disk-size "$DISK_SIZE"
  --shm-size "$SHM_SIZE"
  --container-port 8000
  --auth token
  --token-secret "$AUTH_TOKEN_SECRET_SELECTOR"
  --env "MEDIA_MODEL_ID=$MODEL_ID"
  --env "MEDIA_MODEL_SLUG=$MODEL_SLUG"
  --env "MEDIA_LORA_ADAPTER_NAME=$LORA_ADAPTER_NAME"
  --env "MEDIA_LORA_SCALE=$LORA_SCALE"
  --env "MEDIA_FUSE_LORA=1"
  --env "MEDIA_DEFAULT_STEPS=$DEFAULT_STEPS"
  --env "MEDIA_DEFAULT_GUIDANCE_SCALE=$DEFAULT_GUIDANCE_SCALE"
  --env "MEDIA_DEFAULT_MAX_SEQUENCE_LENGTH=$DEFAULT_MAX_SEQUENCE_LENGTH"
  --env-secret "HF_TOKEN=$HF_TOKEN_SECRET_SELECTOR"
  --format json
)
case "$pricing" in
  spot-pricing-policy) args+=(--preemptible --spot-pricing-policy-id "$SPOT_PRICING_POLICY_ID") ;;
  follows-spot-price) args+=(--preemptible --follows-spot-price) ;;
esac
[[ "$PUBLIC" == "true" ]] && args+=(--public)
[[ -n "$SUBNET_ID" ]] && args+=(--subnet-id "$SUBNET_ID")
[[ -n "$REGISTRY_SECRET_SELECTOR" ]] && args+=(--registry-secret "$REGISTRY_SECRET_SELECTOR")

create_json="$temp_dir/create.json"
"$NEBIUS_CLI" "${args[@]}" >"$create_json"
chmod 0600 "$create_json"
endpoint_id=$(jq -r '.metadata.id // empty' "$create_json")
[[ -n "$endpoint_id" ]] || {
  echo "create response did not contain an endpoint ID" >&2
  exit 1
}
printf '%s\n' "$endpoint_id" >"$STATE_DIR/endpoint-id"
chmod 0600 "$STATE_DIR/endpoint-id"
redact_endpoint_json <"$create_json"

deadline=$((SECONDS + WAIT_TIMEOUT_SECONDS))
status_json="$temp_dir/status.json"
while (( SECONDS < deadline )); do
  "$NEBIUS_CLI" ai endpoint get \
    --profile "$NEBIUS_PROFILE" \
    --id "$endpoint_id" \
    --format json >"$status_json"
  chmod 0600 "$status_json"
  state=$(jq -r '.status.state // "UNKNOWN"' "$status_json")
  case "$state" in
    RUNNING)
      redact_endpoint_json <"$status_json" >"$STATE_DIR/endpoint-public.json"
      chmod 0600 "$STATE_DIR/endpoint-public.json"
      echo "endpoint reached RUNNING: $endpoint_id"
      exit 0
      ;;
    ERROR)
      redact_endpoint_json <"$status_json" >&2
      echo "endpoint entered ERROR; endpoint ID remains in STATE_DIR for cleanup" >&2
      exit 1
      ;;
  esac
  sleep 15
done
echo "timed out waiting for RUNNING; endpoint ID remains in STATE_DIR for cleanup" >&2
exit 1
