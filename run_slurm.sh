#!/bin/bash

srun --job-name=QiskitSimulator --exclude=cip-ws-105,cip-ws-107  --ntasks=10 --mem-per-cpu=4096 --multi-prog slurm.conf

python3 file_evaluator.py
