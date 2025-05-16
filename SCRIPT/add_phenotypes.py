import os
import sys
import warnings
import contextlib
import gc
import numpy as np
import pandas as pd
import yaml
import argparse
from pathlib import Path
from tqdm import tqdm

def get_arguments():

    parser = argparse.ArgumentParser(description = "Draw tysserand for IMC / IF")
    parser.add_argument('--file', type = str, required=True, help = "config file")
    args = parser.parse_args()

    return args.file

def get_config(config_path):
        
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config

def import_data(dir, IMC, IF):
    if IMC:
        IMC_cell_pos = pd.read_parquet(Path(dir) / "IMC_cell_pos.parquet")
    if IF:
        IF_cell_pos = pd.read_parquet(Path(dir) / f"IF_{config_file['IF_import']['panel']}_cell_pos.parquet")

    if IF and not IMC:
        return IF_cell_pos
    if IMC and not IF:
        return IMC_cell_pos
    if IMC and IF:
        return IMC_cell_pos, IF_cell_pos

def import_phenotypes(dir, IMC, IF, panel):
    if IMC:
        IMC_phenotypes = pd.read_csv(Path(dir) / "IMC_with_phenotypes.csv", dtype={tab_sample_name_type('IMC'): str})
    if IF:
        IF_phenotypes = pd.read_csv(Path(dir) / f"IF_{panel}_with_phenotypes.csv", dtype={tab_sample_name_type('IF'): str})

    if IF and not IMC:
        return IF_phenotypes
    if IMC and not IF:
        return IMC_phenotypes
    if IMC and IF:
        return IMC_phenotypes, IF_phenotypes

def tab_sample_name_type(type):
    sample_name={'IMC':'ROI', 'IF':'layer'}
    return sample_name[type]

def add_pheno(data, phenotypes, type):

    data['patient'] = data['patient'].astype(str)
    phenotypes['patient'] = phenotypes['patient'].astype(str)

    data[tab_sample_name_type(type)] = data[tab_sample_name_type(type)].astype(str)
    phenotypes[tab_sample_name_type(type)] = phenotypes[tab_sample_name_type(type)].astype(str)
    
    if not config_file[f'{type}_import']['re_index']:
        #phenotypes = phenotypes.drop_duplicates(subset=['CellID','X_position', 'Y_position','patient',tab_sample_name_type(type)])
        data_merged = data.merge(
            phenotypes[['CellID','X_position', 'Y_position', 'Cluster', 'patient',tab_sample_name_type(type)]],  # on ne garde que les colonnes nécessaires de df2
            on=['CellID','X_position', 'Y_position','patient',tab_sample_name_type(type)],              # on fusionne sur ces deux colonnes
            how='left'                                    # 'left' garde toutes les lignes de df1
            )
    elif config_file[f'{type}_import']['re_index']:
        #phenotypes = phenotypes.drop_duplicates(subset=['X_position', 'Y_position','patient',tab_sample_name_type(type)])
        data_merged = data.merge(
            phenotypes[['X_position', 'Y_position', 'Cluster', 'patient',tab_sample_name_type(type)]],  # on ne garde que les colonnes nécessaires de df2
            on=['X_position', 'Y_position','patient',tab_sample_name_type(type)],              # on fusionne sur ces deux colonnes
            how='left'                                    # 'left' garde toutes les lignes de df1
            )

    return data_merged

def main(config_file):

    if config_file['IMC_import']['present_in'] and config_file['IF_import']['present_in']:
        IMC_cell_pos, IF_cell_pos = import_data('./output_data',
                                                config_file['IMC_import']['present_in'],
                                                config_file['IF_import']['present_in'])
        IMC_phenotypes, IF_phenotypes = import_phenotypes(config_file['pheno_dir'],                           
                                                config_file['IMC_import']['present_in'],
                                                config_file['IF_import']['present_in'], config_file['IF_import']['panel'])

        IMC_cell_pos_pheno = add_pheno(IMC_cell_pos, IMC_phenotypes, 'IMC')
        IF_cell_pos_pheno = add_pheno(IF_cell_pos, IF_phenotypes, 'IF')

        IMC_cell_pos_pheno = IMC_cell_pos_pheno.rename(columns={'Cluster':'Phenotypes'})
        IF_cell_pos_pheno = IF_cell_pos_pheno.rename(columns={'Cluster':'Phenotypes'})
        IMC_cell_pos_pheno.to_parquet('./output_data/IMC_cell_pos_pheno.parquet')
        IF_cell_pos_pheno.to_parquet(f"./output_data/IF_{config_file['IF_import']['panel']}_cell_pos_pheno.parquet")

        IMC_phenotypes_list = IMC_phenotypes['Cluster'].dropna().drop_duplicates()
        IF_phenotypes_list = IF_phenotypes['Cluster'].dropna().drop_duplicates()

        IMC_phenotypes_list.to_csv("./output_data/description/IMC_phenotypes.csv", index=False, header=False)
        IF_phenotypes_list.to_csv(f"./output_data/description/IF_{config_file['IF_import']['panel']}_phenotypes.csv", index=False, header=False)

if __name__ == "__main__":
    config_path = get_arguments()
    config_file = get_config(config_path)
    main(config_file)

