#!/bin/bash
set -euo pipefail

# RunPod: start from a PyTorch CUDA base image (e.g. runpod/pytorch:2.4.0-py3.11-cuda12.4).
# Then: git clone this repo, cd into it, bash train_runpod.sh

python -m pip install --upgrade pip
python -m pip install unsloth trl datasets

python train_runpod.py
