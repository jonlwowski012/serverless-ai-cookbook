#!/usr/bin/env bash
# Usage: bash job.sh stage|train|check show|dry-run|submit
set -euo pipefail

task=${1:-}
mode=${2:-}
case "$task" in stage|train|check) ;; *) echo "task must be stage, train, or check" >&2; exit 2 ;; esac
case "$mode" in show|dry-run|submit) ;; *) echo "mode must be show, dry-run, or submit" >&2; exit 2 ;; esac

: "${NEBIUS_PROFILE:?set NEBIUS_PROFILE}"
: "${NEBIUS_PROJECT_ID:?set NEBIUS_PROJECT_ID}"
: "${NEBIUS_SUBNET_ID:?set NEBIUS_SUBNET_ID}"
: "${NEBIUS_BUCKET_ID:?set NEBIUS_BUCKET_ID}"
: "${NEBIUS_IMAGE:?set NEBIUS_IMAGE}"

stamp=$(date -u +%Y%m%dT%H%M%SZ)
command=(nebius ai job create --profile "$NEBIUS_PROFILE"
  --parent-id "$NEBIUS_PROJECT_ID" --subnet-id "$NEBIUS_SUBNET_ID"
  --image "$NEBIUS_IMAGE" --volume "$NEBIUS_BUCKET_ID:/workspace/data:rw"
  --disk-size 300Gi --env PYTHONUNBUFFERED=1)

if [[ $task == stage ]]; then
  stage_mode=${NEBIUS_STAGE_MODE:-full}
  case "$stage_mode" in full|sample) ;; *) echo "NEBIUS_STAGE_MODE must be full or sample" >&2; exit 2 ;; esac
  command+=(--name "flux-droid-stage-$stamp" --platform cpu-d3 --preset 32vcpu-128gb
    --timeout 48h --container-command python3 --args /app/cookbook/stage_full.py
    --env "STAGE_MODE=$stage_mode")
else
  gpu_count=${NEBIUS_GPU_COUNT:-8}
  case "$gpu_count" in 1|8) ;; *) echo "NEBIUS_GPU_COUNT must be 1 or 8" >&2; exit 2 ;; esac
  case "${NEBIUS_GPU_PLATFORM:-}" in
    gpu-b200-sxm-a)
      expected=B200
      if [[ $task == check || $gpu_count == 1 ]]; then preset=1gpu-20vcpu-224gb; else preset=8gpu-160vcpu-1792gb; fi ;;
    gpu-rtx6000-a)
      expected='RTX PRO 6000'
      if [[ $task == check || $gpu_count == 1 ]]; then preset=1gpu-24vcpu-218gb; else preset=8gpu-192vcpu-1744gb; fi ;;
    gpu-h200-sxm)
      expected=H200
      if [[ $task == check || $gpu_count == 1 ]]; then preset=1gpu-16vcpu-200gb; else preset=8gpu-128vcpu-1600gb; fi ;;
    gpu-h100-sxm)
      expected=H100
      if [[ $task == check || $gpu_count == 1 ]]; then preset=1gpu-16vcpu-200gb; else preset=8gpu-128vcpu-1600gb; fi ;;
    *) echo "unsupported NEBIUS_GPU_PLATFORM" >&2; exit 2 ;;
  esac
  run_name=${RUN_NAME:-flux-droid-full-$stamp}
  [[ $run_name =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || { echo "invalid RUN_NAME" >&2; exit 2; }
  if [[ $task == train ]]; then
    train_mode=${NEBIUS_TRAIN_MODE:-full}
    case "$train_mode" in full) config=train.json ;; smoke) config=train-smoke.json ;;
      *) echo "NEBIUS_TRAIN_MODE must be full or smoke" >&2; exit 2 ;; esac
    command+=(--name "flux-droid-train-$stamp" --platform "$NEBIUS_GPU_PLATFORM" --preset "$preset"
      --timeout 168h --container-command torchrun
      --args "--standalone --nnodes=1 --nproc-per-node=$gpu_count /app/cookbook/run_full.py"
      --env "RUN_NAME=$run_name" --env "FLUX_ACTION_CONFIG=/app/cookbook/$config"
      --env "EXPECTED_WORLD_SIZE=$gpu_count" --env "EXPECTED_GPU_NAME=$expected"
      --env FLUX_ACTION_PG_TIMEOUT_MINUTES=120)
  else
    check_name=${CHECK_NAME:-check}
    [[ $check_name =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || { echo "invalid CHECK_NAME" >&2; exit 2; }
    command+=(--name "flux-droid-check-$stamp" --platform "$NEBIUS_GPU_PLATFORM" --preset "$preset"
      --timeout 3h --container-command python3 --args /app/cookbook/check_export.py
      --env "RUN_NAME=$run_name" --env "CHECK_NAME=$check_name"
      --env "EXPECTED_GPU_NAME=$expected")
  fi
fi

case "$mode" in
  show) printf '%q ' "${command[@]}"; printf '\n' ;;
  dry-run) "${command[@]}" --dry-run ;;
  submit) "${command[@]}" --async ;;
esac
