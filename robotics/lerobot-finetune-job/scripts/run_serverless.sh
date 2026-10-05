#!/usr/bin/env bash
# Submit the image you built and pushed from this example.
set -euo pipefail

if [[ ${1:-} == --help ]]; then
  echo 'Usage: IMAGE=... SUBNET_ID=... ./scripts/run_serverless.sh [POLICY] [DATASET] [STEPS]'
  exit 0
fi
: "${IMAGE:?Set IMAGE to your pushed image}"
: "${SUBNET_ID:?Set SUBNET_ID}"
: "${S3_BUCKET:?Set S3_BUCKET so the checkpoint survives Job completion}"
: "${S3_ENDPOINT_URL:?Set S3_ENDPOINT_URL}"
: "${AWS_ACCESS_KEY_ID:?Export your Object Storage access key}"
: "${AWS_SECRET_ACCESS_KEY:?Export your Object Storage secret key}"

policy=${1:-act}
dataset=${2:-lerobot/pusht}
steps=${3:-5000}
run_name="lerobot-${policy}-$(date +%Y%m%d-%H%M%S)"
command=(nebius ai job create
  --name "$run_name" --image "$IMAGE" --subnet-id "$SUBNET_ID"
  --platform gpu-h100-sxm --preset 1gpu-16vcpu-200gb --timeout 6h --disk-size 450Gi
  --args "--policy $policy --dataset $dataset --steps $steps --output-dir outputs/train/$run_name"
)
for name in AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_DEFAULT_REGION S3_BUCKET S3_PREFIX S3_ENDPOINT_URL HF_TOKEN; do
  if [[ -n ${!name:-} ]]; then
    command+=(--env "$name=${!name}")
  fi
done
"${command[@]}"
job_id=$(nebius ai job get-by-name --name "$run_name" --format jsonpath='{.metadata.id}')
echo "Follow: nebius ai job logs $job_id --follow"
echo "Status: nebius ai job get $job_id"
echo "Output: s3://$S3_BUCKET/${S3_PREFIX:-lerobot}/$run_name/"
