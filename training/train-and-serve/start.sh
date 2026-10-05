#!/usr/bin/env bash
set -euo pipefail

# Install the pinned runtime into the public PyTorch image.
python3 -m pip install --no-cache-dir \
  transformers==4.49.0 datasets==3.3.2 accelerate==1.4.0 \
  peft==0.14.0 trl==0.15.1 bitsandbytes==0.45.2 sentencepiece==0.2.0

python3 /mnt/data/fine_tune.py \
  --output-dir "/mnt/data/output/${RUN_NAME:?Set RUN_NAME}/tinyllama-lora"
