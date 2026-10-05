#!/usr/bin/env bash
set -euo pipefail

adapter="/mnt/data/output/${RUN_NAME:?Set RUN_NAME}/tinyllama-lora"
# Only load an adapter after all its files have reached Object Storage.
if [[ ! -f "$adapter/COMPLETE" ]]; then
  echo "Adapter publication is incomplete: $adapter" >&2
  exit 1
fi

python3 -m vllm.entrypoints.openai.api_server \
  --host 0.0.0.0 --port 8000 \
  --model TinyLlama/TinyLlama-1.1B-Chat-v1.0 \
  --dtype float16 \
  --enable-lora --max-loras 1 \
  --lora-modules "tinyllama_adapter=$adapter"
