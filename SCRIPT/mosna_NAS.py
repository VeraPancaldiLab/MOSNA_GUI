import os
import sys
import warnings
import gc
from time import time
import copy
import json
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
import shutil

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

def import_params(output_dir, pheno_col):
    uniq_phenotypes_IMC = pd.read_csv(output_dir / "description/IMC_phenotypes.csv").iloc[:, 0].to_numpy()
    uniq_phenotypes_IF = pd.read_csv(output_dir / "description/IF_phenotypes.csv").iloc[:, 0].to_numpy()
    cell_types_IMC = pd.read_parquet(output_dir / "IMC_cell_pos_pheno.parquet")[pheno_col]
    cell_types_IF = pd.read_parquet(output_dir / "IF_cell_pos_pheno.parquet")[pheno_col]
    IF_markers = pd.read_csv(output_dir / "description/IF_markers.csv").iloc[:, 0].to_list()
    IMC_markers = pd.read_csv(output_dir / "description/IMC_markers.csv").iloc[:, 0].to_list()
    IF_sample = pd.read_csv(output_dir / "description/IF_file_description.csv", header=None).values.tolist()
    IMC_sample = pd.read_csv(output_dir / "description/IMC_file_description.csv", header=None).values.tolist()
    return uniq_phenotypes_IF, uniq_phenotypes_IMC, cell_types_IF, cell_types_IMC, IF_markers, IMC_markers, IF_sample, IMC_sample

def define_sample_name(config_file, type):
    if type == 'IMC':
        if config_file["IMC_import"]["if_sample_take_an_other_name"] is not None:
            sample_name = config_file["IMC_import"]["if_sample_take_an_other_name"]
        else:
            sample_name = 'sample'
    elif type == 'IF':
        if config_file["IF_import"]["if_sample_take_an_other_name"] is not None:
            sample_name = config_file["IF_import"]["if_sample_take_an_other_name"]
        else:
            sample_name = 'sample'
    return sample_name

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

def get_param_for_niches(nodes_df, edges_df, node_features_list, 
                        stat_funcs, stat_names, order, reducer_type, clusterer_type, n_neighbors, metric, min_dist, dim_clust, min_cluster_size,
                        save_dir, patient, sample,):
    features_nas = mosna.make_features_NAS(
        X=nodes_df[node_features_list].values,
        pairs=edges_df.values,
        order=order,
        var_names = node_features_list,
        stat_funcs=stat_funcs,
        stat_names=stat_names,
        var_sep='_'
    )

    dir=save_dir / f'clustering-{patient}-{sample}'
    dir.mkdir(parents=True, exist_ok=True)
    cluster_labels, cluster_dir, nb_clust, clusterer = mosna.get_clusterer(
        data=features_nas.values,
        data_dir=dir,     # dossier pour sauvegarder modèles + embeddings
        reducer_type=reducer_type,
        clusterer_type=clusterer_type,
        n_neighbors=n_neighbors,
        metric=metric,
        min_dist=min_dist,
        dim_clust=dim_clust,
        min_cluster_size=min_cluster_size,
        use_gpu=False,
        verbose=1,
    )
    shutil.rmtree(dir)
    return cluster_labels

def load_niches(nodes, cluster_labels, save_dir, patient, sample, image_type, normalize='niche'):
    counts = mosna.make_niches_composition(
        var=nodes['Phenotypes'],       # ou un autre label
        niches=cluster_labels,        # résultat du clustering
        var_label='Phenotypes',
        normalize=normalize
    )
    axes = mosna.plot_niches_composition(counts=counts)
    fig = axes.figure
    plt.title(f"{image_type}_niches composition for {patient}, sample {sample}_{normalize}_normalization")
    fig.savefig(save_dir / f'{patient}-{sample}_niche_composition_{normalize}.png', dpi=300, bbox_inches='tight')
    plt.close(fig)

def tysserand(coords, pairs, clustering,
              type, patient, sample, sample_name,
              save_dir, normalize):
    
    fig, ax = ty.plot_network(
        np.array(coords.values.tolist()), pairs,
        labels=clustering,
        color_mapper=color_map(clustering),
        legend_opt={'loc': 'center left', 'bbox_to_anchor': (1.05, 0.5), 'fontsize': 30, 'markerscale': 5},
        size_nodes=5,
        figsize=(30,30)
        )
    plt.title(f"Draw an {type} Tysserand network niches normalized by {normalize} for patient {patient} and {sample_name} {sample}", fontsize=30)
    plt.savefig(save_dir / f"{type}_Tysserand_network_niches_normalized_{normalize}_{patient}_{sample_name}_{sample}.png", bbox_inches="tight")
    plt.close(fig)

def color_map(clustering):
    if clustering is not None:
        nb_clust = clustering.max()
        uniq = pd.Series(clustering).value_counts().index

        # choose colormap
        clusters_cmap = mosna.make_cluster_cmap(uniq)
        # make color mapper
        # series to sort by decreasing order
        n_colors = len(clusters_cmap)
        celltypes_color_mapper = {x: clusters_cmap[i % n_colors] for i, x in enumerate(uniq)}
    return celltypes_color_mapper
 ##################################### Main #########################################

####################################################### Main #######################################################

def main(IMC, IF, config_file):


    FUNC_MAP = {
    'np.mean': np.mean,
    'np.std': np.std,
    }   

    stat_funcs = [FUNC_MAP[name] for name in config_file['NAS']['stat_funcs']]
    stat_names = config_file['NAS']['stat_funcs']
    method = config_file['NAS']['method']
    pheno_col = 'Phenotypes'
    output_dir = Path('./output_data')
    normalize = config_file['NAS']['normalize']

    uniq_phenotypes_IF, uniq_phenotypes_IMC, cell_types_IF, cell_types_IMC, IF_markers, IMC_markers, IF_sample, IMC_sample = import_params(output_dir, pheno_col)

    if method == 'NAS':
        sof_dir = output_dir / f"NAS"    
        sof_dir.mkdir(parents=True, exist_ok=True)
    elif method == 'SCAN-IT':
        sof_dir = output_dir / f"SCAN-IT"    
        sof_dir.mkdir(parents=True, exist_ok=True)

    save_dir = sof_dir / 'niches_figure'
    save_dir.mkdir(parents=True, exist_ok=True)
    
    network_dir_IF = Path('./output_data/IF_networks_sample')
    network_dir_IMC = Path('./output_data/IMC_networks_sample')
    def process(type):
        for patient, sample in tqdm(IMC_sample, desc= f'{type} niches'):
            sample_name = define_sample_name(config_file, type)
            save_dir_IMC = save_dir / f'{type}'
            if config_file['NAS']['output_id'] is not None:
                save_directory = save_dir_IMC / f"normalization_{normalize}_{str(config_file['NAS']['output_id'])}"
            else:
                save_directory = save_dir_IMC / f'normalization_{normalize}'

            save_directory.mkdir(parents=True, exist_ok=True)
            
            if type == 'IMC':
                nodes = pd.read_parquet(network_dir_IMC / f'nodes_patient-{patient}_{replace_sample_name(sample_name)}-{sample}.parquet')
                edges = pd.read_parquet(network_dir_IMC / f'edges_patient-{patient}_{replace_sample_name(sample_name)}-{sample}.parquet')

                cluster_labels = get_param_for_niches(nodes, edges, IMC_markers, 
                                                stat_funcs, stat_names, config_file['NAS']['order'], config_file['NAS']['reducer_type'], 
                                                config_file['NAS']['clusterer_type'], config_file['NAS']['n_neighbors'], config_file['NAS']['metric'], 
                                                config_file['NAS']['min_dist'], config_file['NAS']['dim_clust'], config_file['NAS']['min_cluster_size'],
                                                save_dir_IMC, patient, sample)
            
            elif type == 'IF':
                nodes = pd.read_parquet(network_dir_IF / f'nodes_patient-{patient}_{replace_sample_name(sample_name)}-{sample}.parquet')
                edges = pd.read_parquet(network_dir_IF / f'edges_patient-{patient}_{replace_sample_name(sample_name)}-{sample}.parquet')

                cluster_labels = get_param_for_niches(nodes, edges, IF_markers, 
                                                stat_funcs, stat_names, config_file['NAS']['order'], config_file['NAS']['reducer_type'], 
                                                config_file['NAS']['clusterer_type'], config_file['NAS']['n_neighbors'], config_file['NAS']['metric'], 
                                                config_file['NAS']['min_dist'], config_file['NAS']['dim_clust'], config_file['NAS']['min_cluster_size'],
                                                save_dir_IMC, patient, sample)

            load_niches(nodes, cluster_labels, save_directory, patient, sample, type, normalize=config_file['NAS']['normalize'])

            nodes[f'niches_{normalize}'] = cluster_labels
            pairs = edges[['source', 'target']].values
            tysserand(nodes[['X_position','Y_position']], pairs, cluster_labels, type, patient, sample, sample_name, save_directory, normalize=config_file['NAS']['normalize'])
        
        yaml_file = config_file['NAS'].copy()
        yaml_file['stat_funcs'] = str(yaml_file['stat_funcs'])
        yaml_file['stat_names'] = str(yaml_file['stat_names'])
        with open(save_directory / "NAS_parameters.json", "w") as f:
            json.dump(yaml_file, f, indent=2)

    if IMC:
        process('IMC')
    if IF:
        process('IF')

if __name__ == "__main__":
    config_path = get_arguments()
    config_file = get_config(config_path)
    main(config_file['IMC_import']['present_in'], config_file['IF_import']['present_in'])