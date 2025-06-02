#!/bin/bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate mosna

phenograph=$(yq '.phenograph' CONFIG/configuration.yaml)
add_pheno=$(yq '.add_pheno' CONFIG/configuration.yaml)
panel=$(yq -r '.IF_import.panel' CONFIG/configuration.yaml)

mkdir -p output_data/description
mkdir -p output_data/test
mkdir -p output_data/IF_${panel}_networks_sample
mkdir -p output_data/IMC_networks_sample

python -u SCRIPT/parser_csv_to_pandas.py --file CONFIG/configuration.yaml

if [ "$add_pheno" == true ]; then
    if [ "$phenograph" == false ]; then
        printf '\t[TASK] Add phenotypes\t\t\t\t'
        python -u SCRIPT/add_phenotypes.py --file CONFIG/configuration.yaml
        echo -e 'DONE\n'
    fi
fi
