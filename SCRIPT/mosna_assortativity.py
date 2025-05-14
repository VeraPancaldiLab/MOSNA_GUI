import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
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
warnings.simplefilter('ignore', RuntimeWarning)
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

def define_sample_name(type):
    sample_name_dict={'IMC':'ROI', 'IF':'layer'}
    return sample_name_dict[type]

def import_data(dir, type):
    if type == 'IMC':
        sample_cell = pd.read_parquet(Path(dir) / "IMC_sample_cell.parquet")
        markers = pd.read_parquet(Path(dir) / "IMC_markers.parquet")
        if (Path(dir) / "IMC_cell_pos_pheno.parquet").exists():
            cell_pos = pd.read_parquet(Path(dir) / "IMC_cell_pos_pheno.parquet")
        else:
            cell_pos = pd.read_parquet(Path(dir) / "IMC_cell_pos.parquet")
        cell_pos.drop(columns='patient', inplace=True)
        cell_pos.drop(columns=define_sample_name(type), inplace=True)

    if type == 'IF':
        sample_cell = pd.read_parquet(Path(dir) / f"IF_{config_file['IF_import']['panel']}_sample_cell.parquet")
        markers = pd.read_parquet(Path(dir) / f"IF_{config_file['IF_import']['panel']}_markers.parquet")
        if (Path(dir) / f"IF_{config_file['IF_import']['panel']}_cell_pos_pheno.parquet").exists():
            cell_pos = pd.read_parquet(Path(dir) / f"IF_{config_file['IF_import']['panel']}_cell_pos_pheno.parquet")
        else:
            cell_pos = pd.read_parquet(Path(dir) / f"IF_{config_file['IF_import']['panel']}_cell_pos.parquet")
        cell_pos.drop(columns='patient', inplace=True)
        cell_pos.drop(columns=define_sample_name(type), inplace=True)
        
    return cell_pos, markers, sample_cell
    
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

def mix_mat_assortativity(nodes_dir, pheno_col, n_shuffle = 50, type=None):

    sample_name = define_sample_name(type)

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

def plot_mix_mat(save_dir, net_stats, sample_id, type, panel):
    z_cols = [x for x in net_stats.columns if x.endswith('Z') and not x.startswith('assort')]

    mixmat_z = mosna.series_to_mixmat(net_stats.loc[sample_id, z_cols], discard=' Z').astype(float)
    assort_z = net_stats.loc[sample_id, "assort Z"]
    
    sns.set_context("notebook")
    figsize = (9, 8)
    title = "Z-scored assortativity for {} on panel{} for {} by cell types: {:.2f}".format(type,panel,sample_id,assort_z)
    f, ax = plt.subplots(figsize=figsize)
    sns.heatmap(mixmat_z, center=0, cmap="vlag", annot=False, linewidths=.5, ax=ax)
    ax.set_title(title)
    plt.xticks(rotation=45, ha='right')
    plt.savefig(save_dir / f"assortativity_z-scored_{sample_id}", bbox_inches='tight', facecolor='white')
    return z_cols

def clean_net_stat(z_net_stats):
    z_net_stats_cleaned, select_finite = mosna.clean_data(
        z_net_stats, 
        method='mixed',
        thresh=0.8,
        )
    return z_net_stats_cleaned

def group_assort(net_stat, z_cols, save_dir, type, panel):

    z_net_stats = net_stat[z_cols].astype(float)
    z_net_stats = clean_net_stat(z_net_stats)
    z_mean = z_net_stats.mean()
    z_std = z_net_stats.std()

    mixmat_z_mean = mosna.series_to_mixmat(z_mean.loc[z_cols], discard=' Z').astype(float)
    mixmat_z_std = mosna.series_to_mixmat(z_std.loc[z_cols], discard=' Z').astype(float)

    sns.set_context("notebook")
    figsize = (18, 10)
    fig, axes = plt.subplots(1, 2, figsize=figsize, gridspec_kw={'width_ratios': [5, 2]})

    if type == 'IF':
        title = f"mean Z-scored assortativity for {type} with {config_file['IF_import']['panel']} panel dataset by cell types"
    if type == 'IMC':
        title = f"mean Z-scored assortativity for {type} dataset by cell types"
    
    # --- Assortativity matrix ---

    sns.heatmap(mixmat_z_mean, center=0, cmap="vlag", annot=False, linewidths=.5, ax=axes[0])
    axes[0].set_title("Z_scored assortativity")
    axes[0].tick_params(axis='x', rotation=45)

    # --- BARPLOT of mean ± std ---

    data = []
    for i in mixmat_z_mean.index:
        for j in mixmat_z_mean.columns:
            data.append({
                'pair': f"{i}–{j}",
                'mean': mixmat_z_mean.loc[i, j],
                'std': mixmat_z_std.loc[i, j]
            })

    df_plot = pd.DataFrame(data)
    df_plot = df_plot.sort_values(by="mean")

    axes[1].barh(y=df_plot["pair"], width=df_plot["mean"], xerr=df_plot["std"],
             capsize=4, color='steelblue', edgecolor='black')

    axes[1].set_title("Mean ± Std per Cell-Type Pair")
    axes[1].set_ylabel("Z-scored Assortativity")
    axes[1].tick_params(axis='x', rotation=45)

    # --- Plot subplot ---

    fig.suptitle(title)
    plt.tight_layout()
    plt.savefig(save_dir / f"assortativity_z-scored_{type}{panel}", bbox_inches='tight', facecolor='white')
    plt.close()

########################################## Main #######################################

def main(IF, IMC, config_file):

    save_dir = Path("./output_data/assortativity")
    save_dir.mkdir(parents=True, exist_ok=True)

    def process(type, config_file):
        if type == 'IMC':
            panel = ''
        if type == 'IF':
            panel = config_file['IF_import']['panel']
            panel = '_' + panel

        markers_col = pd.read_csv(f'./output_data/description/{type}{panel}_markers.csv', header=None)[0].tolist()
        pheno = pd.read_csv(f'./output_data/description/{type}{panel}_phenotypes.csv', header=None)[0].tolist()

        sample_name={'IMC':'ROI', 'IF':'layer'}
        cell_pos, markers, sample_cell = import_data('./output_data',type)
        
        sample = sample_are_present_in_data(sample_cell, sample_name[type])
        nodes_transfo(f"./output_data/{type}{panel}_networks_sample", markers_col, sample_name[type], sample_present=sample)
    
        if not (save_dir / f"{type}{panel}_net_stat.parquet").exists():
            t = time()
            print(f"Processing Assortativity for {type} data --- ", end='')
            net_stat = mix_mat_assortativity(f"./output_data/{type}{panel}_networks_sample", 
                                                "Phenotypes", 
                                                type=type)
            net_stat.to_parquet(save_dir / f"{type}{panel}_net_stat.parquet")
            print(f"Done\nAssortativity for IMC took {time()-t} s")
            del net_stat, t
            gc.collect()
        
        net_stat = pd.read_parquet(save_dir / f'{type}{panel}_net_stat.parquet')
        list_id = net_stat.index.to_list()
        save_dir_type = save_dir / f"figures/{type}{panel}"
        save_dir_type.mkdir(parents=True, exist_ok=True)
        
        for id in tqdm(list_id, desc=f" └─ Processing assortativity for {type}"):
            z_cols = plot_mix_mat(save_dir_type, clean_net_stat(net_stat), id, type, panel)
        
        z_net_stat = group_assort(net_stat, z_cols, save_dir, type, panel)
    

    if IF:
        process('IF', config_file)
    if IMC: 
        process('IMC', config_file)
  
if __name__ == "__main__":
    config_path = get_arguments()
    config_file = get_config(config_path)
    main(config_file['IMC_import']['present_in'],
         config_file['IF_import']['present_in'],
         config_file)

