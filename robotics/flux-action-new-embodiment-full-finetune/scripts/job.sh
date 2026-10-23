#!/usr/bin/env bash
# Usage: bash scripts/job.sh smoke|full|check [dry-run]
set -euo pipefail

mode=${1:-}
case "$mode" in smoke|full|check) ;; *) echo "usage: bash scripts/job.sh smoke|full|check [dry-run]" >&2; exit 2 ;; esac
case ${2:-} in ''|dry-run) ;; *) echo "only dry-run is supported as a second argument" >&2; exit 2 ;; esac

: "${NEBIUS_PROFILE:?set NEBIUS_PROFILE}"
: "${NEBIUS_PROJECT_ID:?set NEBIUS_PROJECT_ID}"
: "${NEBIUS_SUBNET_ID:?set NEBIUS_SUBNET_ID}"
: "${NEBIUS_BUCKET_ID:?set NEBIUS_BUCKET_ID}"
: "${NEBIUS_IMAGE:?set NEBIUS_IMAGE}"
: "${RUN_NAME:?set RUN_NAME}"
[[ $RUN_NAME =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]] || { echo "invalid RUN_NAME" >&2; exit 2; }

if [[ $mode == check ]]; then
  : "${CHECK_NAME:?set CHECK_NAME}"
  [[ $CHECK_NAME =~ ^[A-Za-z0-9][A-Za-z0-9_-]*$ ]] || { echo "invalid CHECK_NAME" >&2; exit 2; }
  platform=cpu-d3
  preset=32vcpu-128gb
  entrypoint=/app/cookbook/src/check_export.py
else
  platform=gpu-h200-sxm
  preset=1gpu-16vcpu-200gb
  entrypoint="/app/cookbook/src/train_job.py $mode"
fi

job_name="flux-full-$mode-$(date -u +%Y%m%dT%H%M%SZ)"

command=(nebius ai job create --profile "$NEBIUS_PROFILE"
  --parent-id "$NEBIUS_PROJECT_ID" --subnet-id "$NEBIUS_SUBNET_ID"
  --name "$job_name"
  --image "$NEBIUS_IMAGE" --platform "$platform" --preset "$preset"
  --volume "$NEBIUS_BUCKET_ID:/workspace/data:rw" --disk-size 300Gi
  --timeout 168h --container-command python3 --args "$entrypoint"
  --env "RUN_NAME=$RUN_NAME" --env "IMAGE_REF=$NEBIUS_IMAGE"
  --env PYTHONUNBUFFERED=1 --env FLUX_ACTION_PG_TIMEOUT_MINUTES=120)
if [[ $mode == check ]]; then
  command+=(--env "CHECK_NAME=$CHECK_NAME" --env OMP_NUM_THREADS=16)
fi
if [[ -n ${NEBIUS_HF_TOKEN_SECRET:-} ]]; then
  command+=(--env-secret "HF_TOKEN=$NEBIUS_HF_TOKEN_SECRET")
fi

if [[ ${2:-} == dry-run ]]; then
  "${command[@]}" --dry-run
else
  "${command[@]}" --async
  cat <<EOF

Submitted: $job_name
Run: $RUN_NAME
Artifacts: runs/$RUN_NAME/ (bucket ID: $NEBIUS_BUCKET_ID)
EOF
  if [[ $mode == check ]]; then
    echo "Completion receipt: runs/$RUN_NAME/checks/$CHECK_NAME/COMPLETE.json"
  else
    echo "Completion receipt: runs/$RUN_NAME/TRAIN_COMPLETE.json"
  fi
  cat <<EOF

Find the job ID:
  nebius ai job get-by-name --name "$job_name" --parent-id "$NEBIUS_PROJECT_ID" --profile "$NEBIUS_PROFILE"
Monitor (replace JOB_ID with the returned ID):
  nebius ai job get JOB_ID --profile "$NEBIUS_PROFILE"
  nebius ai job logs JOB_ID --profile "$NEBIUS_PROFILE" --tail 80
EOF
fi
