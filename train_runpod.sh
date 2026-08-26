#!/bin/bash
set -euo pipefail

# Persistent network volume is mounted at /workspace.
# venv + HuggingFace cache live ON the volume, so a fresh pod reuses them
# instead of reinstalling torch/unsloth and re-downloading the model.
VOL=/workspace
export HF_HOME="$VOL/hf"
VENV="$VOL/venv"

if [ ! -d "$VENV" ]; then
  python -m venv "$VENV"
fi
source "$VENV/bin/activate"

python -m pip install --upgrade pip
python -m pip install unsloth trl datasets

python train_runpod.py
