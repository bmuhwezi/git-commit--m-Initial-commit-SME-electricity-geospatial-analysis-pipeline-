#!/bin/bash
#
#SBATCH --job-name=Kenya_A1
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=bmuhwezi@umass.edu
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=12
#SBATCH --mem-per-cpu=10000
#SBATCH --partition=longq
#SBATCH --output=array_%A_%a.out
#SBATCH --array=0-35
python SC_NL_buffer_plt_bill.py $SLURM_ARRAY_TASK_ID 


