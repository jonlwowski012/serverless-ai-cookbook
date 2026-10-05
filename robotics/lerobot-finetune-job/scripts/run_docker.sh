#!/usr/bin/env bash
# Build and run a short local training check; output stays on the host.
set -euo pipefail
cd "$(dirname "$0")/.."
image=${IMAGE:-lerobot-demo:local}
docker build --platform linux/amd64 -t "$image" .
mkdir -p lerobot-outputs
docker run --rm --platform linux/amd64 --shm-size 2g \
  -v "$PWD/lerobot-outputs:/lerobot/outputs" \
  "$image" --policy "${1:-act}" --dataset "${2:-lerobot/pusht}" --steps "${3:-50}" --batch-size 2
