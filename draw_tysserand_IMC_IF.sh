#!/bin/bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate mosna

TEST=$(yq '.test' CONFIG/tysserand.yaml)
phenotypes_not_defined=$(yq '.phenograph' CONFIG/tysserand.yaml)
echo "$TEST"

mkdir -p output_data/description
mkdir -p output_data/test
mkdir -p output_data/IF_networks_sample
mkdir -p output_data/IMC_networks_sample

python SCRIPT/parser_csv_to_pandas.py --file CONFIG/tysserand.yaml

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
    python SCRIPT/test_parser.py --file CONFIG/tysserand.yaml
    printf "TEST --- DONE\n\n"
fi

if [ "$phenotypes_not_defined" == false ]; then
    printf 'Add phenotypes --- '
    python SCRIPT/add_phenotypes.py --file CONFIG/tysserand.yaml
    echo -e 'DONE\n'
fi

mkdir -p output_data/Tysserand_network
echo '########### Tysserand Plotting ###########'
python SCRIPT/draw_tysserand.py --file CONFIG/tysserand.yaml

conda deactivate