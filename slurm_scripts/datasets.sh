#!/bin/bash

# Default parameters:
seed=42
device="cuda:0"
config_dir="./diffusion_policy/config"
default_config_name="train_diffusion_unet_image_workspace.yaml"

# If no dataset paths are passed as arguments, use a default dataset path.
if [ "$#" -eq 0 ]; then
    dataset_paths=("/users/ysong135/scratch/datasets/diffpo/datasets/square_d0_obs_black_matte0.0_panda200_iiwa150.hdf5")
else
    dataset_paths=("$@")
fi

# Loop over each provided dataset path and submit a separate job.
for dataset_path in "${dataset_paths[@]}"; do
    # Compose the OVERRIDES variable including the dataset override.
    overrides="training.seed=${seed} training.device=${device} +extra.dataset_path=${dataset_path}"
    
    # Extract a base name from the dataset path for naming the run.
    dataset_name=$(basename "${dataset_path}" .hdf5)
    
    # Determine the config name based on the dataset path.
    config_name="${default_config_name}"
    if [[ "${dataset_path}" == *"square"* ]]; then
        config_name="square_unet.yaml"
    elif [[ "${dataset_path}" == *"coffee"* ]]; then
        config_name="coffee_unet.yaml"
    elif [[ "${dataset_path}" == *"stack"* ]]; then
        config_name="stack_unet.yaml"
    elif [[ "${dataset_path}" == *"three_piece_assembly"* ]]; then
        config_name="three_piece_assembly_unet.yaml"
    fi
    
    # Create a unique run directory incorporating the dataset name and timestamp.
    run_dir="/users/ysong135/scratch/datasets/diffpo/checkpoints/$(date +%Y.%m.%d)/$(date +%H.%M.%S)_${dataset_name}"
    
    echo "Submitting job for dataset: ${dataset_path}"
    echo "Hydra run directory: ${run_dir}"
    echo "Using config file: ${config_name}"
    
    sbatch --job-name="job_${dataset_name}" \
           --export=ALL,config_dir="${config_dir}",config_name="${config_name}",OVERRIDES="${overrides}",HYDRA_RUN_DIR="${run_dir}" \
           slurm_scripts/train.sbatch

done
