#!/bin/bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate mosna

add_pheno=$(yq eval '.add_pheno' CONFIG/configuration_pre_process.yaml)

mkdir -p temp/description

python -u SCRIPT/parser_csv_to_pandas.py --file CONFIG/configuration_pre_process.yaml

if [ "$add_pheno" == true ]; then
    printf '\t[TASK] Add phenotypes\t\t\t\t'
    python -u SCRIPT/add_phenotypes.py --file CONFIG/configuration_pre_process.yaml
    echo -e 'DONE\n'
fi
