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

def replace_sample_name(sample_name):
    return sample_name.replace('_', '-')

def var_aggregate(network_dir, output_dir, method, pheno_col, uniq_phenotypes, stat_funcs, stat_names, sample_name, file_type):
    if sample_name is None:
        sample_name = 'sample'

    if (output_dir / f'{file_type}_aggregation_stats.parquet').exists():
        print(f'Load aggregation statistics from {file_type}')
        var_aggreg = pd.read_parquet(output_dir / f'{file_type}_aggregation_stats.parquet')
    else:
        print(f'Compute aggregation statistics from {file_type}')
        var_aggreg = mosna.compute_spatial_omic_features_all_networks(
            method=method,
            nodes_dir=network_dir,
            edges_dir=network_dir, 
            attributes_col=pheno_col,
            use_attributes=uniq_phenotypes, 
            make_onehot=True,
            stat_funcs=stat_funcs,
            stat_names=stat_names,
            id_level_1='patient',
            id_level_2=replace_sample_name(sample_name), 
            parallel_groups=False,
            memory_limit='max',
            save_intermediate_results=False, 
            dir_save_interm=None,
            verbose=1,
            )
        var_aggreg.to_parquet(output_dir / f'{file_type}_aggregation_stats.parquet', index=False)
    return var_aggreg.drop(columns=['patient', replace_sample_name(sample_name)], inplace=True)

def get_param_for_niches():
    hyperparams = {
    'n_neighbors': 15,
    'metric': 'euclidean',
    'clusterer_type': 'hdbscan',
    'dim_clust': 10,
    'clust_size_param': 5,
    }

    clust_size_param_name = 'min_cluster_size'  # par ex. pour HDBSCAN

    cluster_params = {
        'reducer_type': 'none', 
        'n_neighbors': hyperparams['n_neighbors'], 
        'k_cluster': hyperparams['n_neighbors'],
        'metric': hyperparams['metric'],
        'min_dist': 0.0,
        'clusterer_type': hyperparams['clusterer_type'], 
        'dim_clust': hyperparams['dim_clust'], 
        'force_recompute': True,
        clust_size_param_name: int(hyperparams['clust_size_param']),
    }
    return cluster_params

def load_niches(var_aggreg, sof_dir, cluster_params=None):
    if cluster_params == None:
        cluster_labels, cluster_dir, nb_clust, _ = mosna.get_clusterer(var_aggreg, sof_dir)
    else:
        cluster_labels, cluster_dir, nb_clust, _ = mosna.get_clusterer(var_aggreg, sof_dir, **cluster_params)
    niches = cluster_labels
    str_params = '_'.join([str(key) + '-' + str(val) for key, val in cluster_params.items()])
    #str_params = str_params + f'_normalize-{normalize}'
    return niches, str_params

def plot_niches(niches, cell_types, str_params, save_dir, save_fig=True):
    # Niches total counts
    ax = mosna.plot_niches_histogram(niches)
    plt.title('Niches histogram')
    if save_fig:
        figname = f"{str_params}_niches_total_count.jpg"
        plt.savefig(save_dir / figname, bbox_inches='tight', facecolor='white', dpi=150)
    plt.show()


    # Niches composition

    mosna.plot_niches_composition(var=cell_types, niches=niches, var_label='cell-types')
    title = "niche cell-types composition, normalized by total # cells"
    plt.title(title)
    if save_fig:
        figname = f"{str_params}_{title}.jpg"
        plt.savefig(save_dir / figname, bbox_inches='tight', facecolor='white', dpi=150)
    plt.show()

    mosna.plot_niches_composition(var=cell_types, niches=niches, var_label='cell-types', normalize='niche')
    title = "niche cell-types composition, normalized by niche"
    plt.title(title)
    if save_fig:
        figname = f"{str_params}_{title}.jpg"
        plt.savefig(save_dir / figname, bbox_inches='tight', facecolor='white', dpi=150)
    plt.show()

    mosna.plot_niches_composition(var=cell_types, niches=niches, var_label='cell-types', normalize='obs')
    title = "niche cell-types composition, normalized by cell-type"
    plt.title(title)
    if save_fig:
        figname = f"{str_params}_{title}.jpg"
        plt.savefig(save_dir / figname, bbox_inches='tight', facecolor='white', dpi=150)
    plt.show()

    mosna.plot_niches_composition(var=cell_types, niches=niches, var_label='cell-types', normalize='niche&obs')
    title = "niche cell-types composition, normalized by niche & cell-type"
    plt.title(title)
    if save_fig:
        figname = f"{str_params}_{title}.jpg"
        plt.savefig(save_dir / figname, bbox_inches='tight', facecolor='white', dpi=150)
    plt.show()

##################################### Main #########################################

def main_IF():
    return 0

def main_IMC():
    return 0

def main_IMC_IF():
    config_path = get_arguments()
    config_file = get_config(config_path)


    method = config_file['NAS']['method']

    pheno_col = 'Phenotypes'
    output_dir = Path('./output_data')
    uniq_phenotypes_IMC = pd.read_csv(output_dir / "description/IMC_phenotypes.csv").iloc[:, 0].to_numpy()
    uniq_phenotypes_IF = pd.read_csv(output_dir / "description/IF_phenotypes.csv").iloc[:, 0].to_numpy()
    
    cell_types_IMC = pd.read_parquet(output_dir / "IMC_cell_pos_pheno.parquet")[pheno_col]
    cell_types_IF = pd.read_parquet(output_dir / "IF_cell_pos_pheno.parquet")[pheno_col]

    stat_funcs = np.mean
    stat_names = 'mean'

    if method == 'NAS':
        sof_dir = output_dir / f"NAS"    
        sof_dir.mkdir(parents=True, exist_ok=True)
    elif method == 'SCAN-IT':
        sof_dir = output_dir / f"SCAN-IT"    
        sof_dir.mkdir(parents=True, exist_ok=True)

    save_dir=Path('./output_data/niches')
    save_dir.mkdir(parents=True, exist_ok=True)
    
    network_dir_IF = Path('./output_data/IF_networks_sample')
    network_dir_IMC = Path('./output_data/IMC_networks_sample')

    var_agg_IMC = var_aggregate(network_dir_IMC, sof_dir, 
                                method, pheno_col, uniq_phenotypes_IMC, stat_funcs, stat_names,
                                config_file['IMC_import']['if_sample_take_an_other_name'], 'IMC')
    
    var_agg_IF = var_aggregate(network_dir_IF, sof_dir, 
                               method, pheno_col, uniq_phenotypes_IF, stat_funcs, stat_names,
                               config_file['IF_import']['if_sample_take_an_other_name'], 'IF')
    
    cluster_param = get_param_for_niches()
    print(cluster_param)
    niches, str_param = load_niches(var_agg_IMC, sof_dir, cluster_param)
    plot_niches(niches, cell_types_IMC, str_param, save_dir)

if __name__ == "__main__":
    config_path = get_arguments()
    config_file = get_config(config_path)

    if config_file['IF_import']['present_in'] and config_file['IMC_import']['present_in']:
        main_IMC_IF()
    if config_file['IF_import']['present_in'] and not config_file['IMC_import']['present_in']:
        main_IF()
    if not config_file['IF_import']['present_in'] and config_file['IMC_import']['present_in']:
        main_IMC()
