#!/bin/bash
set -euo pipefail

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install mlx-lm

python format.py

python -m mlx_lm lora \
    --model mlx-community/Qwen2.5-Coder-3B-Instruct-4bit \
    --data . \
    --train \
    --batch-size 1 \
    --max-seq-length 4096 \
    --iters 800 \
    --num-layers 12

