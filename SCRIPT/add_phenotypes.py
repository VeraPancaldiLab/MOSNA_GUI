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
        IF_cell_pos = pd.read_parquet(Path(dir) / "IF_cell_pos.parquet")

    if IF and not IMC:
        return IF_cell_pos
    if IMC and not IF:
        return IMC_cell_pos
    if IMC and IF:
        return IMC_cell_pos, IF_cell_pos

def import_phenotypes(dir, IMC, IF):
    if IMC:
        IMC_phenotypes = pd.read_csv(Path(dir) / "IMC_with_phenotypes_all.csv")
    if IF:
        IF_phenotypes = pd.read_csv(Path(dir) / "IF_with_phenotypes_all.csv")

    if IF and not IMC:
        return IF_phenotypes
    if IMC and not IF:
        return IMC_phenotypes
    if IMC and IF:
        return IMC_phenotypes, IF_phenotypes

def add_pheno(data, phenotypes):
    phenotypes_unique = phenotypes.drop_duplicates(subset=['X_position', 'Y_position'])
    data_merged = data.merge(
        phenotypes_unique[['X_position', 'Y_position', 'Cluster']],  # on ne garde que les colonnes nécessaires de df2
        on=['X_position', 'Y_position'],              # on fusionne sur ces deux colonnes
        how='left'                                    # 'left' garde toutes les lignes de df1
        )
    return data_merged

def main():
    config_path = get_arguments()
    config_file = get_config(config_path)

    if config_file['IMC_import']['present_in'] and config_file['IF_import']['present_in']:
        IMC_cell_pos, IF_cell_pos = import_data('./output_data',
                                                config_file['IMC_import']['present_in'],
                                                config_file['IF_import']['present_in'])
        IMC_phenotypes, IF_phenotypes = import_phenotypes(config_file['pheno_dir'],                           
                                                config_file['IMC_import']['present_in'],
                                                config_file['IF_import']['present_in'])
        
        IMC_cell_pos_pheno = add_pheno(IMC_cell_pos, IMC_phenotypes)
        IF_cell_pos_pheno = add_pheno(IF_cell_pos, IF_phenotypes)

        IMC_cell_pos_pheno = IMC_cell_pos_pheno.rename(columns={'Cluster':'Phenotypes'})
        IF_cell_pos_pheno = IF_cell_pos_pheno.rename(columns={'Cluster':'Phenotypes'})
        IMC_cell_pos_pheno.to_parquet('./output_data/IMC_cell_pos_pheno.parquet')
        IF_cell_pos_pheno.to_parquet('./output_data/IF_cell_pos_pheno.parquet')

        IMC_phenotypes_list = IMC_phenotypes['Cluster'].dropna().drop_duplicates()
        IF_phenotypes_list = IF_phenotypes['Cluster'].dropna().drop_duplicates()

        IMC_phenotypes_list.to_csv("./output_data/description/IMC_phenotypes.csv", index=False, header=False)
        IF_phenotypes_list.to_csv("./output_data/description/IF_phenotypes.csv", index=False, header=False)




        
if __name__ == "__main__":
    main()

