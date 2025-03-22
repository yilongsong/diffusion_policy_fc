#!/bin/bash
# submit_train_diffusion.sh
# Usage:
#   ./submit_train_diffusion.sh [dataset_path_override] [note_override]
#
# For example:
#   ./submit_train_diffusion.sh "/home/yilong/Documents/robo/robomimic_3d/datasets/square/ph/my_dataset.hdf5" "expA"

# Default overrides:
seed=42
device="cuda:0"
config_dir="diffusion_policy/config"
config_name="train_diffusion_unet_image_workspace.yaml"

# If a dataset_path override is provided, use it:
if [ -n "$1" ]; then
    dataset_path_override=$1
    dataset_override_arg="dataset.dataset_path=${dataset_path_override}"
else
    dataset_override_arg=""
fi

# If a note override is provided:
if [ -n "$2" ]; then
    note_override=$2
    note_override_arg="task.note=${note_override}"
else
    note_override_arg=""
fi

# If a checkpoint path is provided:
if [ -n "$3" ]; then
    checkpoint_path=$3
    checkpoint_override_arg="checkpoint.restore_path=${checkpoint_path} training.resume=True"
else
    checkpoint_override_arg=""
fi

# Compose additional Hydra override arguments (you can add more here)
overrides="training.seed=${seed} training.device=${device} ${dataset_override_arg} ${note_override_arg} ${checkpoint_override_arg}"

# Construct a run directory string (using date) for Hydra
run_dir="data/outputs/$(date +%Y.%m.%d)/$(date +%H.%M.%S)_train_diffusion_unet_image_${dataset_path_override:-default}"

echo "Submitting job with overrides: ${overrides}"
echo "Hydra run directory: ${run_dir}"

# Submit job via Slurm
sbatch --job-name="train_diffusion" slurm_scripts/train.sbatch \
       --export=ALL,OVERRIDES="${overrides}",HYDRA_RUN_DIR="${run_dir}"