#!/bin/bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate mosna
silent=$(yq -r '.silent' CONFIG/configuration.yaml)

if [[ "$silent" == "true" ]]; then
    export TF_CPP_MIN_LOG_LEVEL=3
    export TF_ENABLE_ONEDNN_OPTS=0
    mkdir -p output_data/Tysserand_network
    python SCRIPT/draw_tysserand.py --file CONFIG/configuration.yaml 2>/dev/null

else
    mkdir -p output_data/Tysserand_network
    python SCRIPT/draw_tysserand.py --file CONFIG/configuration.yaml
fi

conda deactivate