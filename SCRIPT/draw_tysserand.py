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

def import_data(dir, IMC, IF):
    if IMC:
        IMC_sample_cell = pd.read_parquet(Path(dir) / "IMC_sample_cell.parquet")
        IMC_cell_pos = pd.read_parquet(Path(dir) / "IMC_cell_pos.parquet")
        IMC_markers = pd.read_parquet(Path(dir) / "IMC_markers.parquet")
    if IF:
        IF_sample_cell = pd.read_parquet(Path(dir) / "IMC_sample_cell.parquet")
        IF_cell_pos = pd.read_parquet(Path(dir) / "IMC_cell_pos.parquet")
        IF_markers = pd.read_parquet(Path(dir) / "IMC_markers.parquet")

    if IF and not IMC:
        return IF_cell_pos, IF_markers, IF_sample_cell
    if IMC and not IF:
        return IMC_cell_pos, IMC_markers, IMC_sample_cell
    if IMC and IF:
        return IMC_cell_pos, IMC_markers, IMC_sample_cell, IF_cell_pos, IF_markers, IF_sample_cell

def main():
    config_path = get_arguments()
    config_file = get_config(config_path)

    if config_file['IF_import']['present_in'] and not config_file['IMC_import']['present_in']:
        IF_cell_pos, IF_markers, IF_sample_cell = import_data(config_file['standard']['output_dir'],
                                                            config_file['IMC_import']['present_in'],
                                                            config_file['IF_import']['present_in'])
        


    if config_file['IMC_import']['present_in'] and not config_file['IF_import']['present_in']:
        IMC_cell_pos, IMC_markers, IMC_sample_cell = import_data(config_file['standard']['output_dir'],
                                                            config_file['IMC_import']['present_in'],
                                                            config_file['IF_import']['present_in'])
        



    if config_file['IMC_import']['present_in'] and config_file['IF_import']['present_in']:
        IMC_cell_pos, IMC_markers, IMC_sample_cell, IF_cell_pos, IF_markers, IF_sample_cell = import_data(config_file['standard']['output_dir'],
                                                            config_file['IMC_import']['present_in'],
                                                            config_file['IF_import']['present_in'])


if __name__ == "__main__":
    main()