#!/bin/bash

srun --job-name=QiskitSimulator --exclude=cip-ws-105,cip-ws-107  --ntasks=30 --mem-per-cpu=2048 --multi-prog slurm.conf

python3 file_evaluator.py
