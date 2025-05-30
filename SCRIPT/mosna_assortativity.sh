#!/bin/bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate mosna

if [[ "$1" == "--silent" ]]; then
    export TF_CPP_MIN_LOG_LEVEL=3
    export TF_ENABLE_ONEDNN_OPTS=0

    python SCRIPT/mosna_assortativity.py --file CONFIG/configuration.yaml 2>/dev/null

else

    python SCRIPT/mosna_assortativity.py --file CONFIG/configuration.yaml

fi