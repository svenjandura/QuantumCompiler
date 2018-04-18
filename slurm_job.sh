#!/bin/bash/
#
#SBATCH --job-name=QiskitSimulator
#SBATCH --comment="Benchmarks a quantum compiler"
#SBATCH --workdir=/home/s/Sven.Jandura/Documents/Projekte/ibmq/challenge
#SBATCH --output=/home/s/Sven.Jandura/Documents/Projekte/ibmq/challenge/slurm.out

srun --ntasks=30 --multi-prog slurm.conf
