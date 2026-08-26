#!/bin/bash
set -euo pipefail

# No venv: building one on the mfs network volume is unreliable (broken symlinks
# and exec bits). Install unsloth into the image's system Python instead — torch
# and CUDA are already present there, so this is fast (~1-2 min) and reliable.
# Persist only the model cache on the volume (that's the big, slow download).
export HF_HOME=/workspace/hf

pip install unsloth trl datasets

python train_runpod.py
