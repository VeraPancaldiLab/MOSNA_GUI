source ~/miniconda3/etc/profile.d/conda.sh
conda activate mosna

mkdir -p pandas_data
mkdir -p pandas_data/test

python SCRIPT/parser_csv_to_pandas.py --file CONFIG/cell_encounter.yaml

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
python SCRIPT/test_parser.py --file CONFIG/cell_encounter.yaml
printf "TEST --- DONE\n\n"


printf "########### Cell Encounter ###########\n\n"
mkdir -p cell_encounter_data
python SCRIPT/cell_encounter.py --file CONFIG/cell_encounter.yaml
printf "Cell Encounter --- DONE\n\n"

conda deactivate