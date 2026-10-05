#!/usr/bin/env bash
# Run a GPU simulation and upload its results to Object Storage.
set -euo pipefail

if [[ ${1:-} == --help ]]; then
  echo 'Usage: IMAGE=... SUBNET_ID=... ./scripts/run_serverless.sh [PROTEIN_ID] [STEPS]'
  exit 0
fi
: "${IMAGE:?Set IMAGE to your pushed image}"
: "${SUBNET_ID:?Set SUBNET_ID}"
: "${S3_BUCKET:?Set S3_BUCKET so the results survive Job completion}"
: "${S3_ENDPOINT_URL:?Set S3_ENDPOINT_URL}"
: "${AWS_ACCESS_KEY_ID:?Export your Object Storage access key}"
: "${AWS_SECRET_ACCESS_KEY:?Export your Object Storage secret key}"

protein=${1:-1UBQ}
steps=${2:-1000}
run_name="openmm-$(date +%Y%m%d-%H%M%S)"
command=(nebius ai job create
  --name "$run_name" --image "$IMAGE" --subnet-id "$SUBNET_ID"
  --platform gpu-l40s-a --preset 1gpu-8vcpu-32gb --timeout 1h --disk-size 100Gi
  --env OPENMM_PLATFORM=CUDA --args "--protein-id $protein --steps $steps"
)
for name in AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_DEFAULT_REGION S3_BUCKET S3_PREFIX S3_ENDPOINT_URL; do
  if [[ -n ${!name:-} ]]; then
    command+=(--env "$name=${!name}")
  fi
done
"${command[@]}"
job_id=$(nebius ai job get-by-name --name "$run_name" --format jsonpath='{.metadata.id}')
echo "Follow: nebius ai job logs $job_id --follow"
echo "Status: nebius ai job get $job_id"
