#!/bin/bash

# Default overrides:
seed=42
device="cuda:0"
config_dir="./diffusion_policy/config"
config_name="train_diffusion_unet_image_workspace.yaml"

# Compose additional Hydra override arguments (you can add more here)
overrides="training.seed=${seed} training.device=${device}"

# Construct a run directory string (using date) for Hydra
run_dir="/users/ysong135/scratch/datasets/diffpo/checkpoints/$(date +%Y.%m.%d)/$(date +%H.%M.%S)_train_diffusion_unet_image"

echo "Submitting job with overrides: ${overrides}"
echo "Hydra run directory: ${run_dir}"

# Submit job via Slurm
sbatch --job-name="200+150" \
       --export=ALL,config_dir="${config_dir}",config_name="${config_name}",OVERRIDES="${overrides}",HYDRA_RUN_DIR="${run_dir}" \
       slurm_scripts/train.sbatch
