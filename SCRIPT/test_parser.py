import pandas as pd
import glob
from pathlib import Path
import argparse
import yaml
import os

def get_arguments():

    parser = argparse.ArgumentParser(description = "Draw tysserand for IMC / IF")
    parser.add_argument('--file', type = str, required=True, help = "config file")
    args = parser.parse_args()

    return args.file

def get_config(config_path):
        
    base_path = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base_path, config_path)

    if not os.path.exists(full_path):
        raise FileNotFoundError(f"❌ Config file not found : {full_path}")
    
    with open(full_path, 'r') as f:
        config = yaml.safe_load(f)
    return config

def import_data(directory):
    object_data = glob.glob(directory)
    files = dict()

    for file in object_data:
        if Path(file).with_suffix('.csv').exists():
            obj = pd.read_csv(Path(file).with_suffix('.csv'))
            files.setdefault(Path(file).stem, obj)           
        else:
            obj = pd.read_parquet(Path(file).with_suffix('.parquet'))
            files.setdefault(Path(file).stem, obj)
    return files

def value_compt(df1, df2):
    colonnes_communes = df1.columns.intersection(df2.columns)

    df1_filtered = df1[colonnes_communes]
    df2_filtered = df2[colonnes_communes]

    df2_aligned_filtered = df2_filtered[df1_filtered.columns]
    if df2_aligned_filtered.columns.all() == df1_filtered.columns.all():
        inclusion = df1_filtered.merge(df2_aligned_filtered, how='left', indicator=True)['_merge'].eq('both').all()
        return len(df1),len(df2),inclusion
    else: 
        return 'columns have not same name or there are different'
def merge(df1, df2, df3, df_to_compare):
    df1['dup_index'] = df1.groupby('CellID').cumcount()
    df2['dup_index'] = df2.groupby('CellID').cumcount()
    df3['dup_index'] = df3.groupby('CellID').cumcount()
    df_merged = df1.merge(df2, on=['CellID', 'dup_index']).merge(df3, on=['CellID', 'dup_index'])
    df_merged = df_merged.drop(columns='dup_index')
    return value_compt(df_merged, df_to_compare)

def main():
    config_path = get_arguments()
    config_file = get_config(config_path)
    if not config_file['test']['partial']:
        directory_to_test = import_data(config_file['test']['directory_to_test'])
        test_directory = import_data(config_file['test']['test_directory'])
        if config_file['IF_import']['present_in']:
            print(f"IF data (pandas length, originals concatenated csv length, same row between them)\t-->\t{merge(directory_to_test['IF_markers'],directory_to_test['IF_cell_pos'],directory_to_test['IF_sample_cell'],test_directory['merged_IF'])}")
        if config_file['IMC_import']['present_in']:
            print(f"IMC data (pandas length, originals concatenated csv length, same row between them)\t-->\t{merge(directory_to_test['IMC_markers'],directory_to_test['IMC_cell_pos'],directory_to_test['IMC_sample_cell'],test_directory['merged_IMC'])}")
      
if __name__ == "__main__":
    main()