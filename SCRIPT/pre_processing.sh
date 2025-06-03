#!/bin/bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate mosna

phenograph=$(yq '.phenograph' CONFIG/configuration.yaml)
add_pheno=$(yq '.add_pheno' CONFIG/configuration.yaml)

mkdir -p output_data/description

python -u SCRIPT/parser_csv_to_pandas.py --file CONFIG/configuration.yaml

if [ "$add_pheno" == true ]; then
    if [ "$phenograph" == false ]; then
        printf '\t[TASK] Add phenotypes\t\t\t\t'
        python -u SCRIPT/add_phenotypes.py --file CONFIG/configuration.yaml
        echo -e 'DONE\n'
    fi
fi
