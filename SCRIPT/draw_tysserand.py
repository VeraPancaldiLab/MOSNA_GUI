import numpy as np
import pandas as pd
import yaml
import argparse
import matplotlib.pyplot as plt
import seaborn as sns
import os
from time import time
from pathlib import Path
from time import time
from tqdm import tqdm
import copy
import matplotlib as mpl
import colorcet as cc
import composition_stats as cs

from tysserand import tysserand as ty

import matplotlib as mpl
mpl.rcParams["figure.facecolor"] = 'white'
mpl.rcParams["axes.facecolor"] = 'white'
mpl.rcParams["savefig.facecolor"] = 'white'

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

def tysserand_network_IF(IF_cell_pos, IF_markers, IF_sample_cell, there_is_duplicata):


    filtre = IF_sample_cell['patient'] == patient
    nb_cells = filtre.sum()
    print(f"cell number in dataset (patient = {patient}) : {nb_cells}")

    if there_is_duplicata:
        cells_df = IF_sample_cell.loc[filtre, ['CellID']]
        markers_to_cluter_IF = cells_df.merge(IF_markers.drop_duplicates(subset='CellID'), on='CellID', how='left') 
    else:
        cells = IF_sample_cell.loc[filtre, 'CellID'].drop_duplicates()
        markers_to_cluter_IF = IF_markers[IF_markers['CellID'].isin(cells)].drop_duplicates(subset='CellID')
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
        print(IF_sample_cell.head())


if __name__ == "__main__":
    main()