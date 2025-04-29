#!/bin/bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate mosna

TEST=$(yq '.test' CONFIG/tysserand.yaml)
echo "$TEST"

mkdir -p output_data/description
mkdir -p output_data/test
mkdir -p output_data/edges/IF
mkdir -p output_data/edges/IMC
mkdir -p output_data/nodes/IF
mkdir -p output_data/nodes/IMC

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

printf 'Add phenotypes --- '
python SCRIPT/add_phenotypes.py --file CONFIG/tysserand.yaml
echo -e 'DONE\n'

mkdir -p output_data/Tysserand_network
echo '########### Tysserand Plotting ###########'
python SCRIPT/draw_tysserand.py --file CONFIG/tysserand.yaml

conda deactivate