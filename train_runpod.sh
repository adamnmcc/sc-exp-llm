#!/bin/bash
set -euo pipefail

# Persistent network volume mounted at /workspace: venv + HF cache live here so
# a fresh pod reuses them. --system-site-packages reuses the base image's torch
# and CUDA libs (skips a ~2.5GB reinstall). uv makes the resolve+install fast.
VOL=/workspace
export HF_HOME="$VOL/hf"
VENV="$VOL/venv"

if [ ! -d "$VENV" ]; then
  python -m venv --system-site-packages "$VENV"
fi
source "$VENV/bin/activate"

python -m pip install -q uv
uv pip install unsloth trl datasets

python train_runpod.py
