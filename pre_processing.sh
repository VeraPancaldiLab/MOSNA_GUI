#!/bin/bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate mosna

TEST=$(yq '.test' CONFIG/configuration.yaml)
phenotypes_not_defined=$(yq '.phenograph' CONFIG/configuration.yaml)
add_pheno=$(yq '.add_pheno' CONFIG/configuration.yaml)
panel=$(yq -r '.IF_import.panel' CONFIG/configuration.yaml)

mkdir -p output_data/description
mkdir -p output_data/test
mkdir -p output_data/IF_${panel}_networks_sample
mkdir -p output_data/IMC_networks_sample

python -u SCRIPT/parser_csv_to_pandas.py --file CONFIG/configuration.yaml

if [ "$TEST" == "true" ]; then
    echo -n 'Concatenation For test --- '
    head -n 1 $(ls data/processed/Bram_data/acquired_csv_files/*.csv | head -n 1) > output_data/test/merged_IMC.csv
    for f in data/processed/Bram_data/acquired_csv_files/*.csv; do
        tail -n +2 "$f" >> output_data/test/merged_IMC.csv
    done

    head -n 1 $(ls data/processed/Bram_data/IF_merged_by_patient/*.csv | head -n 1) > output_data/test/merged_IF.csv
    for f in data/processed/Bram_data/IF_merged_by_patient/*.csv; do
        tail -n +2 "$f" >> output_data/test/merged_IF.csv
    done
    printf 'DONE\n\n'

    echo '########### TEST ###########'
    python -u SCRIPT/test_parser.py --file CONFIG/configuration.yaml
    printf "TEST --- DONE\n\n"
fi

if [ "$add_pheno" == true ]; then
    if [ "$phenotypes_not_defined" == false ]; then
        printf '[TASK] Add phenotypes\t\t\t\t'
        python -u SCRIPT/add_phenotypes.py --file CONFIG/configuration.yaml
        echo -e 'DONE\n'
    fi
fi
