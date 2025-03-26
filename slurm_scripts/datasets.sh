#!/bin/bash

# Default overrides:
seed=42
device="cuda:0"
config_dir="./diffusion_policy/config"

# If no config names are passed, use a default; otherwise, use all provided arguments.
if [ "$#" -eq 0 ]; then
    config_names=("train_diffusion_unet_image_workspace.yaml")
else
    config_names=("$@")
fi

overrides="training.seed=${seed} training.device=${device}"

# Loop over each provided config name and submit a separate job
for config_name in "${config_names[@]}"; do
    # Create a unique run directory by incorporating the config name and timestamp
    run_dir="/users/ysong135/scratch/datasets/diffpo/checkpoints/$(date +%Y.%m.%d)/$(date +%H.%M.%S)_${config_name}"
    echo "Submitting job for config: ${config_name}"
    echo "Hydra run directory: ${run_dir}"
    
    sbatch --job-name="job_${config_name}" \
           --export=ALL,config_dir="${config_dir}",config_name="${config_name}",OVERRIDES="${overrides}",HYDRA_RUN_DIR="${run_dir}" \
           slurm_scripts/train.sbatch

    sleep 1  # slight pause to ensure different timestamps if needed
done