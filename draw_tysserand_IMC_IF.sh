#!/bin/bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate mosna

mkdir -p pandas_data
mkdir -p pandas_data/test

python SCRIPT/parser_csv_to_pandas.py --file CONFIG/tysserand.yaml

echo -n 'Concatenation For test --- '
head -n 1 $(ls data/processed/Bram_data/acquired_csv_files/*.csv | head -n 1) > pandas_data/test/merged_IMC.csv
for f in data/processed/Bram_data/acquired_csv_files/*.csv; do
    tail -n +2 "$f" >> pandas_data/test/merged_IMC.csv
done

head -n 1 $(ls data/processed/Bram_data/IF_merged_by_patient/*.csv | head -n 1) > pandas_data/test/merged_IF.csv
for f in data/processed/Bram_data/IF_merged_by_patient/*.csv; do
    tail -n +2 "$f" >> pandas_data/test/merged_IF.csv
done
printf 'DONE\n\n'

echo '########### TEST ###########'
python SCRIPT/test_parser.py --file CONFIG/tysserand.yaml
printf "TEST --- DONE\n\n"


mkdir -p ../Tysserand_network
echo '########### Tysserand Plotting ###########'
python SCRIPT/draw_tysserand.py --file CONFIG/tysserand.yaml

conda deactivate