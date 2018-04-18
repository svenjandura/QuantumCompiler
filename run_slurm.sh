#!/bin/bash

srun --job-name=QiskitSimulator --ntasks=30 --mem-per-cpu=2048 --multi-prog slurm.conf

python3 file_evaluator.py
