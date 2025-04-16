#!/bin/bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate mosna

python parser_csv_to_pandas.py --file config.yaml

conda deactivate