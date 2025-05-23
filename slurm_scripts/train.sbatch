#!/bin/bash

#SBATCH -N 1
#SBATCH -n 16
#SBATCH --time=800:00:00
#SBATCH -p 3090-gcondo --gres=gpu:1 --gres-flags=enforce-binding
#SBATCH --mem=128G
#SBATCH -o /oscar/home/ysong135/Documents/diffusion_policy/outputs/%j.out
#SBATCH -e /oscar/home/ysong135/Documents/diffusion_policy/outputs/%j.err
#SBATCH --mail-type=FAIL
#SBATCH --mail-user=yilong_song@brown.edu

# Load modules and activate conda environment
module purge

module load miniforge/23.11.0-0s
source /oscar/runtime/software/external/miniforge/23.11.0-0/etc/profile.d/conda.sh
module load cuda/11.8.0
module load cudnn/8.7.0.84
module load vscode

export MUJOCO_GL=osmesa
module load mesa/22.1.6-6dbg5gq
module load patchelf
unset LD_PRELOAD

export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/users/ysong135/.mujoco/mujoco210/bin
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/lib/nvidia
export CPATH=$CONDA_PREFIX/include
export PYTHONPATH="/oscar/home/ysong135/Documents/robosuite:$PYTHONPATH"
export PYTHONPATH="/oscar/home/ysong135/Documents/robomimic:$PYTHONPATH"

conda  deactivate || true

conda activate robodiff

cd /oscar/home/ysong135/Documents/diffusion_policy || { echo "Directory not found"; exit 1; }

export HYDRA_FULL_ERROR=1

python train.py \
  --config-dir=${config_dir} \
  --config-name=${config_name} \
  hydra.run.dir="${HYDRA_RUN_DIR}" \
  ${OVERRIDES}