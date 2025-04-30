#!/bin/bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate mosna

python SCRIPT/mosna_assortativity.py --file CONFIG/tysserand.yaml