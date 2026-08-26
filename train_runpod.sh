#!/bin/bash
set -euo pipefail

# Volume mounted at /workspace: venv + HF cache persist here.
# --system-site-packages reuses the base image's torch/CUDA (no ~2.5GB reinstall).
# Plain pip (not uv) so already-present system torch is left alone.
VOL=/workspace
export HF_HOME="$VOL/hf"
VENV="$VOL/venv"

if [ ! -d "$VENV" ]; then
  python -m venv --system-site-packages "$VENV"
fi
source "$VENV/bin/activate"

pip install unsloth trl datasets

python train_runpod.py
