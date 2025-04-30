import os
import sys
import warnings
import gc
from time import time
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

def mix_mat_assortativity(nodes_dir, pheno_col, n_shuffle = 50, sample_name='sample'):
    if sample_name is None:
        sample_name = 'sample'
    net_stats = mosna.groups_assort_mixmat(
        net_dir=nodes_dir, 
        attributes_col=pheno_col, 
        make_onehot=True,
        id_level_1='patient',
        id_level_2=replace_sample_name(sample_name), 
        extension='parquet',
        n_shuffle=n_shuffle,
        parallel_groups='max',  # or False
        memory_limit='max',
        save_intermediate_results=False)
    net_stats.index = net_stats['id']
    net_stats.drop(columns=['id'], inplace=True)
    return net_stats

def plot_mix_mat(save_dir, net_stats, sample_id):
    z_cols = [x for x in net_stats.columns if x.endswith('Z') and not x.startswith('assort')]

    mixmat_z = mosna.series_to_mixmat(net_stats.loc[sample_id, z_cols], discard=' Z').astype(float)
    assort_z = net_stats.loc[sample_id, "assort Z"]
    
    sns.set_context("notebook")
    figsize = (9, 8)
    title = "Z-scored assortativity for {} by cell types: {:.2f}".format(sample_id,assort_z)
    print(title)
    f, ax = plt.subplots(figsize=figsize)
    sns.heatmap(mixmat_z, center=0, cmap="vlag", annot=False, linewidths=.5, ax=ax)
    ax.set_title(title)
    plt.xticks(rotation=45, ha='right')
    plt.savefig(save_dir / f"assortativity_z-scored_{sample_id}", bbox_inches='tight', facecolor='white')

########################################## Main #######################################

def main_IF_IMC():
    config_path = get_arguments()
    config_file = get_config(config_path)
    IF_markers_col = pd.read_csv('./output_data/description/IF_markers.csv', header=None)[0].tolist()
    IMC_markers_col = pd.read_csv('./output_data/description/IMC_markers.csv', header=None)[0].tolist()
    IMC_pheno = pd.read_csv('./output_data/description/IMC_phenotypes.csv', header=None)[0].tolist()
    IF_pheno = pd.read_csv('./output_data/description/IF_phenotypes.csv', header=None)[0].tolist()



    IMC_cell_pos, IMC_markers, IMC_sample_cell, IF_cell_pos, IF_markers, IF_sample_cell = import_data('./output_data',
                                                            config_file['IMC_import']['present_in'],
                                                            config_file['IF_import']['present_in'])

    
    sample = sample_are_present_in_data(IMC_sample_cell, config_file["IMC_import"]["if_sample_take_an_other_name"])
    nodes_transfo("./output_data/IMC_networks_sample", IMC_markers_col, config_file["IMC_import"]["if_sample_take_an_other_name"], sample_present=sample)
    
    sample = sample_are_present_in_data(IF_sample_cell, config_file["IF_import"]["if_sample_take_an_other_name"])
    nodes_transfo("./output_data/IF_networks_sample", IF_markers_col, config_file["IF_import"]["if_sample_take_an_other_name"], sample_present=sample)
    
    gc.collect()
    
    save_dir = Path("./output_data/assortativity")
    save_dir.mkdir(parents=True, exist_ok=True)

    if not (save_dir / "IMC_net_stat.parquet").exists():
        t = time()
        net_stat_IMC = mix_mat_assortativity("./output_data/IMC_networks_sample", 
                                             "Phenotypes", 
                                             sample_name=config_file["IMC_import"]["if_sample_take_an_other_name"])
        net_stat_IMC.to_parquet(save_dir / 'IMC_net_stat.parquet')
        print(f"Assortativity for IMC took {time()-t} s")
        del net_stat_IMC, t
        gc.collect()
    
    net_stat_IMC = pd.read_parquet(save_dir / 'IMC_net_stat.parquet')
    list_id = net_stat_IMC.index.to_list()
    save_dir_IMC = save_dir / "figures/IMC"
    save_dir_IMC.mkdir(parents=True, exist_ok=True)
    for id in list_id:
        plot_mix_mat(save_dir_IMC, net_stat_IMC, id)

    if not (save_dir / "IF_net_stat.parquet").exists():
        t = time()
        net_stat_IF = mix_mat_assortativity("./output_data/IF_networks_sample", 
                                            "Phenotypes", 
                                            sample_name=config_file["IF_import"]["if_sample_take_an_other_name"])
        net_stat_IF.to_parquet(save_dir / 'IF_net_stat.parquet')
        print(f"Assortativity for IF took {time()-t} s")
        del net_stat_IF, t
        gc.collect()

    net_stat_IF = pd.read_parquet(save_dir / 'IF_net_stat.parquet')
    list_id = net_stat_IF.index.to_list()
    save_dir_IF = save_dir / "figures/IF"
    save_dir_IF.mkdir(parents=True, exist_ok=True)
    for id in list_id:
        plot_mix_mat(save_dir_IF, net_stat_IF, id)
    
def main_IF():
    config_path = get_arguments()
    config_file = get_config(config_path)
    IF_markers_col = pd.read_csv('./output_data/description/IF_markers.csv', header=None)[0].tolist()
    
    IF_cell_pos, IF_markers, IF_sample_cell = import_data('./output_data',
                                                            config_file['IMC_import']['present_in'],
                                                            config_file['IF_import']['present_in'])
    sample = sample_are_present_in_data(IF_sample_cell)
    nodes_transfo("./output_data/nodes/IF", IF_markers_col, config_file["IF_import"]["if_sample_take_an_other_name"], sample_present=sample)

def main_IMC():
    config_path = get_arguments()
    config_file = get_config(config_path)
    IMC_markers_col = pd.read_csv('./output_data/description/IMC_markers.csv', header=None)[0].tolist()

    IMC_cell_pos, IMC_markers, IMC_sample_cell = import_data('./output_data',
                                                            config_file['IMC_import']['present_in'],
                                                            config_file['IF_import']['present_in'])
    sample = sample_are_present_in_data(IMC_sample_cell)
    nodes_transfo("./output_data/nodes/IMC", IMC_markers_col, config_file["IMC_import"]["if_sample_take_an_other_name"], sample_present=sample)
    
if __name__ == "__main__":
    config_path = get_arguments()
    config_file = get_config(config_path)

    if config_file['IF_import']['present_in'] and config_file['IMC_import']['present_in']:
        main_IF_IMC()
    if config_file['IF_import']['present_in'] and not config_file['IMC_import']['present_in']:
        main_IF()
    if not config_file['IF_import']['present_in'] and config_file['IMC_import']['present_in']:
        main_IMC()
