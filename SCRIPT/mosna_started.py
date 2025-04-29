import os
import sys
import warnings
import contextlib
import gc

warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
with open(os.devnull, 'w') as fnull:
    with contextlib.redirect_stderr(fnull):

        from sklearn.exceptions import ConvergenceWarning, FitFailedWarning
        warnings.simplefilter('ignore', FitFailedWarning)
        warnings.simplefilter('ignore', ConvergenceWarning)
        warnings.simplefilter('ignore', FutureWarning)
        warnings.simplefilter('ignore', DeprecationWarning)
        warnings.simplefilter('ignore', UserWarning)
        import numpy as np
        import pandas as pd
        import matplotlib.pyplot as plt
        import seaborn as sns
        import argparse
        import yaml
        from time import time
        import warnings
        import joblib
        from pathlib import Path
        from time import time
        from tqdm import tqdm
        import copy
        import matplotlib as mpl
        import napari
        import colorcet as cc
        import composition_stats as cs
        from sklearn.impute import KNNImputer
        from lifelines import KaplanMeierFitter, CoxPHFitter

        from tysserand import tysserand as ty
        from mosna import mosna
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
        
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config   

def import_data(dir, IMC, IF):
    if IMC:
        IMC_sample_cell = pd.read_parquet(Path(dir) / "IMC_sample_cell.parquet")
        IMC_markers = pd.read_parquet(Path(dir) / "IMC_markers.parquet")
        if (Path(dir) / "IMC_cell_pos_pheno.parquet").exists():
            IMC_cell_pos = pd.read_parquet(Path(dir) / "IMC_cell_pos_pheno.parquet")
        else:
            IMC_cell_pos = pd.read_parquet(Path(dir) / "IMC_cell_pos.parquet")
    if IF:
        IF_sample_cell = pd.read_parquet(Path(dir) / "IF_sample_cell.parquet")
        IF_markers = pd.read_parquet(Path(dir) / "IF_markers.parquet")
        if (Path(dir) / "IF_cell_pos_pheno.parquet").exists():
            IF_cell_pos = pd.read_parquet(Path(dir) / "IF_cell_pos_pheno.parquet")
        else:
            IF_cell_pos = pd.read_parquet(Path(dir) / "IF_cell_pos.parquet")

    if IF and not IMC:
        return IF_cell_pos, IF_markers, IF_sample_cell
    if IMC and not IF:
        return IMC_cell_pos, IMC_markers, IMC_sample_cell
    if IMC and IF:
        return IMC_cell_pos, IMC_markers, IMC_sample_cell, IF_cell_pos, IF_markers, IF_sample_cell
    
def sample_are_present_in_data(data, name):
    if name is None:
        name = 'sample'
    if name in data.columns:
        return True
    else:
        return False

def open_markers(file):
    with open(file, 'r') as f:
        markers = [line.strip() for line in f if line.strip()]
    print(markers)
    return markers

def replace_sample_name(sample_name):
    return sample_name.replace('_', '-')

def nodes_transfo(nodes_dir, marker_cols, sample_name=None, sample_present=True):
    if sample_name is not None:
        sample_name = replace_sample_name(sample_name)
        nodes_dir = mosna.transform_nodes(
            nodes_dir=nodes_dir,
            id_level_1='patient',
            id_level_2=sample_name, 
            use_cols=marker_cols,
            method='clr',
            save_dir='auto',
        )
    elif sample_present:
        nodes_dir = mosna.transform_nodes(
            nodes_dir=nodes_dir,
            id_level_1='patient',
            id_level_2='sample', 
            use_cols=marker_cols,
            method='clr',
            save_dir='auto',
        )
    else:
        nodes_dir = mosna.transform_nodes(
            nodes_dir=nodes_dir,
            id_level_1='patient',
            use_cols=marker_cols,
            method='clr',
            save_dir='auto',
        )

def mix_mat_assortativity(nodes_dir, pheno_col, n_shuffle = 500):
    net_stats = mosna.groups_assort_mixmat(
        net_dir=nodes_dir, 
        attributes_col=pheno_col, 
        make_onehot=True,
        id_level_1='patient',
        id_level_2='sample', 
        extension='parquet',
        n_shuffle=n_shuffle,
        parallel_groups='max',  # or False
        save_intermediate_results=True)
    net_stats.index = net_stats['id']
    net_stats.drop(columns=['id'], inplace=True)
    return net_stats

########################################## Main #######################################

def main_IF_IMC():
    config_path = get_arguments()
    config_file = get_config(config_path)
    IF_markers_col = pd.read_csv('../output_data/description/IF_markers.csv', header=None)[0].tolist()
    IMC_markers_col = pd.read_csv('../output_data/description/IMC_markers.csv', header=None)[0].tolist()
    IMC_pheno = pd.read_csv('../output_data/description/IMC_phenotypes.csv', header=None)[0].tolist()
    IF_pheno = pd.read_csv('../output_data/description/IF_phenotypes.csv', header=None)[0].tolist()



    IMC_cell_pos, IMC_markers, IMC_sample_cell, IF_cell_pos, IF_markers, IF_sample_cell = import_data('../output_data',
                                                            config_file['IMC_import']['present_in'],
                                                            config_file['IF_import']['present_in'])

    
    sample = sample_are_present_in_data(IMC_sample_cell, config_file["IMC_import"]["if_sample_take_an_other_name"])
    nodes_transfo("../output_data/IMC_networks_sample/nodes", IMC_markers_col, config_file["IMC_import"]["if_sample_take_an_other_name"], sample_present=sample)
    
    sample = sample_are_present_in_data(IF_sample_cell, config_file["IF_import"]["if_sample_take_an_other_name"])
    nodes_transfo("../output_data/IF_networks_sample/nodes", IF_markers_col, config_file["IF_import"]["if_sample_take_an_other_name"], sample_present=sample)

    net_stat = mix_mat_assortativity("../output_data/IMC_networks_sample", "Phenotypes")
    print(net_stat)

def main_IF():
    config_path = get_arguments()
    config_file = get_config(config_path)
    IF_markers_col = pd.read_csv('../output_data/description/IF_markers.csv', header=None)[0].tolist()
    
    IF_cell_pos, IF_markers, IF_sample_cell = import_data('./output_data',
                                                            config_file['IMC_import']['present_in'],
                                                            config_file['IF_import']['present_in'])
    sample = sample_are_present_in_data(IF_sample_cell)
    nodes_transfo("../output_data/nodes/IF", IF_markers_col, config_file["IF_import"]["if_sample_take_an_other_name"], sample_present=sample)

def main_IMC():
    config_path = get_arguments()
    config_file = get_config(config_path)
    IMC_markers_col = pd.read_csv('../output_data/description/IMC_markers.csv', header=None)[0].tolist()

    IMC_cell_pos, IMC_markers, IMC_sample_cell = import_data('./output_data',
                                                            config_file['IMC_import']['present_in'],
                                                            config_file['IF_import']['present_in'])
    sample = sample_are_present_in_data(IMC_sample_cell)
    nodes_transfo("../output_data/nodes/IMC", IMC_markers_col, config_file["IMC_import"]["if_sample_take_an_other_name"], sample_present=sample)
    
if __name__ == "__main__":
    config_path = get_arguments()
    config_file = get_config(config_path)

    if config_file['IF_import']['present_in'] and config_file['IMC_import']['present_in']:
        main_IF_IMC()
    if config_file['IF_import']['present_in'] and not config_file['IMC_import']['present_in']:
        main_IF()
    if not config_file['IF_import']['present_in'] and config_file['IMC_import']['present_in']:
        main_IMC()
