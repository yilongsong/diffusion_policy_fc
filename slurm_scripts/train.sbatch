#!/bin/bash

#SBATCH -N 1
#SBATCH --time=100:00:00
#SBATCH -p 3090-gcondo
#SBATCH --gres=gpu:1       # Adjust the number of GPUs as needed
#SBATCH --mem=128G
#SBATCH -o outputs/%j.out
#SBATCH -e outputs/%j.err
#SBATCH --mail-type=FAIL
#SBATCH --mail-user=yilong_song@brown.edu

# Load modules and activate conda environment
module load cuda/11.8.0
module load cudnn/9.1.1.17
conda activate robodiff

export HYDRA_FULL_ERROR=1

# Launch training using Hydra: we pass our overrides via the command line.
python train.py \
  --config-dir=${config_dir} \
  --config-name=${config_name} \
  hydra.run.dir="${HYDRA_RUN_DIR}" \
  ${OVERRIDES}
