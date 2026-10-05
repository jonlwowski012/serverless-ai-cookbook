#!/usr/bin/env bash
# Build and run a short CPU simulation; output stays on the host.
set -euo pipefail
cd "$(dirname "$0")/.."
image=${IMAGE:-openmm-demo:local}
docker build --platform linux/amd64 -t "$image" .
mkdir -p results
docker run --rm --platform linux/amd64 -e OPENMM_PLATFORM=CPU \
  -v "$PWD/results:/openmm/results" \
  "$image" --protein-id "${1:-1UBQ}" --steps "${2:-200}"
