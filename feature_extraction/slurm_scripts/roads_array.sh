#!/bin/bash
#
#SBATCH --job-name=Kenya_A1
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --mail-user=bmuhwezi@umass.edu
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=12
#SBATCH --mem-per-cpu=10000
#SBATCH --partition=defq
#SBATCH --time=08:00:00
#SBATCH --output=array_%A_%a.out
#SBATCH --array=0-7
python roadLength.py $SLURM_ARRAY_TASK_ID 


