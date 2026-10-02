#!/usr/bin/env bash
# Usage: bash job.sh smoke|full|check show|dry-run|submit
set -euo pipefail

train_mode=${1:-}
operation=${2:-}
case "$train_mode" in smoke|full|check) ;; *) echo "mode must be smoke, full, or check" >&2; exit 2 ;; esac
case "$operation" in show|dry-run|submit) ;; *) echo "operation must be show, dry-run, or submit" >&2; exit 2 ;; esac

: "${NEBIUS_PROFILE:?set NEBIUS_PROFILE}"
: "${NEBIUS_PROJECT_ID:?set NEBIUS_PROJECT_ID}"
: "${NEBIUS_SUBNET_ID:?set NEBIUS_SUBNET_ID}"
: "${NEBIUS_BUCKET_ID:?set NEBIUS_BUCKET_ID}"
: "${NEBIUS_IMAGE:?set NEBIUS_IMAGE}"
: "${RUN_NAME:?set RUN_NAME}"
[[ $RUN_NAME =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]] || { echo "invalid RUN_NAME" >&2; exit 2; }

platform=${NEBIUS_GPU_PLATFORM:-gpu-h200-sxm}
gpu_count=${NEBIUS_GPU_COUNT:-8}
case "$gpu_count" in 1|8) ;; *) echo "NEBIUS_GPU_COUNT must be 1 or 8" >&2; exit 2 ;; esac
case "$platform" in
  gpu-h200-sxm|gpu-h100-sxm)
    if [[ $train_mode == check || $gpu_count == 1 ]]; then preset=1gpu-16vcpu-200gb; else preset=8gpu-128vcpu-1600gb; fi ;;
  gpu-b200-sxm)
    if [[ $train_mode == check || $gpu_count == 1 ]]; then preset=1gpu-20vcpu-224gb; else preset=8gpu-160vcpu-1792gb; fi ;;
  gpu-rtx6000)
    if [[ $train_mode == check || $gpu_count == 1 ]]; then preset=1gpu-24vcpu-218gb; else preset=8gpu-192vcpu-1744gb; fi ;;
  cpu-d3)
    [[ $train_mode == check ]] || { echo "cpu-d3 is only supported for check" >&2; exit 2; }
    preset=32vcpu-128gb ;;
  *) echo "unsupported 8-GPU platform: $platform" >&2; exit 2 ;;
esac

if [[ $train_mode == check ]]; then
  : "${CHECK_NAME:?set CHECK_NAME for the check job}"
  [[ $CHECK_NAME =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]] || { echo "invalid CHECK_NAME" >&2; exit 2; }
  entrypoint=/app/cookbook/check_export.py
else
  entrypoint="/app/cookbook/train_job.py $train_mode"
fi

command=(nebius ai job create --profile "$NEBIUS_PROFILE"
  --parent-id "$NEBIUS_PROJECT_ID" --subnet-id "$NEBIUS_SUBNET_ID"
  --name "flux-full-$train_mode-$(date -u +%Y%m%dT%H%M%SZ)"
  --image "$NEBIUS_IMAGE" --platform "$platform" --preset "$preset"
  --volume "$NEBIUS_BUCKET_ID:/workspace/data:rw" --disk-size 300Gi
  --timeout 168h --container-command python3
  --args "$entrypoint"
  --env "RUN_NAME=$RUN_NAME" --env "IMAGE_REF=$NEBIUS_IMAGE"
  --env PYTHONUNBUFFERED=1 --env FLUX_ACTION_PG_TIMEOUT_MINUTES=120
  --env "NEBIUS_GPU_COUNT=$gpu_count")
if [[ $train_mode == check ]]; then
  command+=(--env "CHECK_NAME=$CHECK_NAME")
  if [[ $platform == cpu-d3 ]]; then
    command+=(--env CHECK_DEVICE=cpu --env CHECK_MAX_WINDOWS=1 --env OMP_NUM_THREADS=16)
  fi
fi
if [[ -n ${NEBIUS_HF_TOKEN_SECRET:-} ]]; then
  command+=(--env-secret "HF_TOKEN=$NEBIUS_HF_TOKEN_SECRET")
fi

case "$operation" in
  show) printf '%q ' "${command[@]}"; printf '\n' ;;
  dry-run) "${command[@]}" --dry-run ;;
  submit) "${command[@]}" --async ;;
esac
