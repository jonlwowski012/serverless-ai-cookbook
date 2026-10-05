#!/usr/bin/env bash
set -euo pipefail

python3 -m pip install --no-cache-dir -r /mnt/data/requirements.txt
python3 /mnt/data/train.py \
  --config /mnt/data/config.yaml \
  --output-dir "/mnt/data/output/${RUN_NAME:?Set RUN_NAME}"
