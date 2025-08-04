import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import warnings
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
import argparse
import yaml
import warnings
from pathlib import Path
from tqdm import tqdm
import matplotlib as mpl

from tysserand import tysserand as ty
from mosna import mosna
import matplotlib as mpl
import shutil

mpl.rcParams["figure.facecolor"] = 'white'
mpl.rcParams["axes.facecolor"] = 'white'
mpl.rcParams["savefig.facecolor"] = 'white'

########################################## Function ##########################################

def verif_file(type, panel=None):
    if os.path.isfile(f"./temp/{type}{panel}.parquet"):
        return True
    return False

def define_panel(type, panel):
    if type == 'IMC':
        panel = ''
    if type == 'IF':
        panel = '_' + panel
    return panel

def get_arguments():

    parser = argparse.ArgumentParser(description = "Draw tysserand for IMC / IF")
    parser.add_argument('--file', type = str, required=True, help = "config file")
    args = parser.parse_args()

    return args.file

def get_config(config_path):
        
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config   

def import_params(type, pheno_col):
    panel = define_panel(type)

    cell_types = pd.read_parquet(f"./temp/{type}{panel}.parquet")[pheno_col]
    uniq_pheno = cell_types.unique().to_numpy()

    sample = pd.read_parquet(f"./temp/{type}{panel}.parquet")[["patient", panel]].drop_duplicates()
    markers = pd.read_csv(f"./temp/description/{type}{panel}_markers.csv").iloc[:, 0].to_list()

    return cell_types, uniq_pheno, sample, markers

def define_sample_name(type):
    sample_name_dict={'IMC':'ROI', 'IF':'layer'}
    return sample_name_dict[type]

def var_aggregate(network_dir, output_dir, method, pheno_col, uniq_phenotypes, stat_funcs, stat_names, sample_name, file_type, panel):
    if sample_name is None:
        sample_name = 'sample'

    if (output_dir / f'{file_type}_aggregation_stats.parquet').exists():
        print(f'\t[INFO] Load aggregation statistics from {file_type}')
        var_aggreg = pd.read_parquet(output_dir / f'{file_type}_aggregation_stats.parquet')
    else:
        print(f'\t[INFO] Compute aggregation statistics from {file_type}')
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
            id_level_2=sample_name, 
            parallel_groups=False,
            memory_limit='max',
            save_intermediate_results=False, 
            dir_save_interm=None,
            verbose=1,
            )
        var_aggreg.to_parquet(output_dir / f'{file_type}{panel}_aggregation_stats.parquet', index=False)
    var_aggreg.drop(columns=['patient', sample_name], inplace=True)
    return var_aggreg

def get_param_for_niches(nodes_df, edges_df, node_features_list, 
                        stat_funcs, stat_names, order):
    
    features_NAS = mosna.make_features_NAS(
        X=nodes_df[node_features_list].values,
        pairs=edges_df.values,
        order=order,
        var_names = node_features_list,
        stat_funcs=stat_funcs,
        stat_names=stat_names,
        var_sep='_'
    )

    return features_NAS

def clustering_NAS(features_NAS, reducer_type, clusterer_type, n_neighbors, 
                   metric, min_dist, dim_clust,
                   min_cluster_size,k_cluster, resolution, n_clusters,
                   save_dir, patient, sample):
    
    if patient == None and sample == None:
        dir=save_dir / f'clustering-aggregate'
    elif patient != None and sample != None:
        dir=save_dir / f'clustering-{patient}-{sample}'
    dir.mkdir(parents=True, exist_ok=True)

    cluster_labels, _, _, _ = mosna.get_clusterer(
        data=features_NAS.values,
        data_dir=dir,
        reducer_type=reducer_type,
        clusterer_type=clusterer_type,
        n_neighbors=n_neighbors,
        metric=metric,
        n_clusters=n_clusters,
        resolution=resolution,
        min_dist=min_dist,
        dim_clust=dim_clust,
        min_cluster_size=min_cluster_size,
        use_gpu=False,
        k_cluster=k_cluster,
        verbose=0,
    )
    shutil.rmtree(dir)
    return cluster_labels

def plot_niches(counts, cluster_labels, save_dir, patient, sample, image_type, panel, normalize='niche'):
    fig, axes = plt.subplots(1, 2, figsize=(20, 8), constrained_layout=True)

    axes[1] = mosna.plot_niches_composition(counts=counts, ax=axes[1])
    axes[1].set_title("Niches Composition")

    axes[0] = mosna.plot_niches_histogram(cluster_labels, ax=axes[0])
    axes[0].set_title('Niches histogram')

    if sample == None and patient == None:
        fig.suptitle(f"For an {image_type}{panel} image and panel niches composition for with {normalize}_normalization")
        fig.savefig(save_dir / f'{image_type}{panel}_niche_composition_{normalize}.png', dpi=300, bbox_inches='tight')
    if sample != None and patient != None:
        fig.suptitle(f"For an {image_type}{panel} image and panel niches composition for {patient}, sample {sample} with {normalize} normalization")
        fig.savefig(save_dir / f'{patient}-{sample}_niche_composition_{normalize}.png', dpi=300, bbox_inches='tight')
    plt.close(fig)

def tysserand(coords, pairs, clustering,
              type, patient, sample, sample_name,
              save_dir, normalize):
    
    fig, _ = ty.plot_network(
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
        uniq = pd.Series(clustering).value_counts().index

        clusters_cmap = mosna.make_cluster_cmap(uniq)
        n_colors = len(clusters_cmap)
        celltypes_color_mapper = {x: clusters_cmap[i % n_colors] for i, x in enumerate(uniq)}
    return celltypes_color_mapper

def register_params(config, save_directory):
    yaml_file = config.copy()
    yaml_file['stat_funcs'] = str(yaml_file['stat_funcs'])
    yaml_file['stat_names'] = str(yaml_file['stat_names'])
    with open(save_directory / f"NAS_{type}_parameters.json", "w") as f:
        json.dump(yaml_file, f, indent=2)
    return f'Parameters registered in {save_directory}'
        
def get_params(config_file, type, nodes_aggregation, method, FUNC_MAP):
    if nodes_aggregation:
        config = config_file[method]['nodes_aggregation'][type]
                
        stat_funcs = [FUNC_MAP[name] for name in config['stat_funcs'].split(',')]
        stat_names = config['stat_names']
        normalize = config['normalize']
        order = int(config['order'])
        clusterer_type = config['clusterer_type']
        reducer_type = config['reducer_type']
        metric = config['metric']
        n_neighbors = config['n_neighbors']
        min_dist = config['min_dist']
        dim_clust = config['dim_clust']
        min_cluster_size = config['min_cluster_size']
        k_cluster = config['k_cluster']
        resolution = config['resolution']
        n_clusters = config['n_clusters']

    else:
        config = config_file[method][type]

        stat_funcs = [FUNC_MAP[name] for name in config['stat_funcs'].split(',')]
        stat_names = config['stat_names']
        normalize = config['normalize']
        order = int(config['order'])
        clusterer_type = config['clusterer_type']
        reducer_type = config['reducer_type']
        metric = config['metric']
        n_neighbors = config['n_neighbors']
        min_dist = config['min_dist']
        dim_clust = config['dim_clust']
        min_cluster_size = config['min_cluster_size']
        k_cluster = config['k_cluster']
        resolution = config['resolution']
        n_clusters = config['n_clusters']

    return stat_funcs, stat_names, normalize, order, clusterer_type, \
            reducer_type, metric, n_neighbors, min_dist, dim_clust, \
            min_cluster_size, k_cluster,resolution, n_clusters

####################################################### Main #######################################################

def main(IF, IMC, config_file):

    FUNC_MAP = {
    'np.mean': np.mean,
    'np.std': np.std,
    }   

    method = config_file['NAS']['method']
    pheno_col = 'Phenotypes'
    output_dir = Path('./OUTPUT_DATA')
    nodes_aggregation = config_file['NAS']['node_aggregation']
    perform_NAS_all_sample = config_file['NAS']['perform_NAS_all_sample']

    if method == 'NAS':
        sof_dir = output_dir / f"NAS"    
    elif method == 'SCAN-IT':
        sof_dir = output_dir / f"SCAN-IT"
        raise Exception("SCAN-IT not available yet")

    def process(type, panel):

        ######################################## Define configuration ########################################
        sample_name = define_sample_name(type)
        
        tab_feature_to_compute_NAS = ['X_position', 'Y_position', 'Phenotypes']

        if config_file['NAS']['output_name_file'] is not None:
            save_dir = sof_dir / f"{str(config_file['NAS']['output_name_file'])}"
        else:
            save_dir_ = sof_dir / 'standard'
        
        panel = define_panel(type)
        network_dir = Path(f'./temp/{type}{panel}_networks_sample')
        save_dir.mkdir(parents=True, exist_ok=True)
        
        cell_type, uniq_pheno, tab_sample, tab_markers = import_params()
        ######################################## Node aggregation ########################################
        
        if nodes_aggregation:
            stat_funcs, stat_names, normalize, order, clusterer_type, \
            reducer_type, metric, n_neighbors, min_dist, dim_clust, \
            min_cluster_size, k_cluster, resolution, n_clusters = get_params(config_file, type, nodes_aggregation, method, FUNC_MAP)


            nodes_aggregate = var_aggregate(network_dir,save_dir,method,pheno_col, uniq_pheno,stat_funcs, 
                                                stat_names, sample_name, type, panel)
            
                
            cluster_labels = clustering_NAS(nodes_aggregate,reducer_type, 
                            clusterer_type, n_neighbors, metric, 
                            min_dist, dim_clust, min_cluster_size,k_cluster,resolution, n_clusters,
                            save_dir, patient=None, sample=None)

            tqdm.write(f"\n\t[PROCESS] niches for patient {type}")
            counts = mosna.make_niches_composition(
                    var=cell_type,
                    niches=cluster_labels,
                    var_label="Phenotypes",
                    normalize=normalize
            )

            plot_niches(counts, cluster_labels, save_dir, None, None, type, panel, normalize=normalize)
        ######################################## For each Patient/sample ########################################
        if perform_NAS_all_sample:
            stat_funcs, stat_names, normalize, order, clusterer_type, \
            reducer_type, metric, n_neighbors, min_dist, dim_clust, \
            min_cluster_size, k_cluster, resolution, n_clusters = get_params(config_file, type, False, method, FUNC_MAP)

            for patient, sample in tqdm(tab_sample, desc= f'\t[PROCESS] {type} Compositions niches'):
                if type == 'IMC':
                    tqdm.write(f"\n\t[INFO] niches for patient {patient} and ROI {sample}")
                else:
                    tqdm.write(f"\n\t[INFO] niches for patient {patient} and layer {sample}")
                save_dir_data = save_dir / f'{type}{panel}'
                save_directory = save_dir_data / f"normalization_{normalize}"
                save_directory.mkdir(parents=True, exist_ok=True)
                
                #################### Reading nodes and edges ####################

                nodes = pd.read_parquet(network_dir / f'nodes_patient-{patient}_{sample_name}-{sample}.parquet')
                edges = pd.read_parquet(network_dir / f'edges_patient-{patient}_{sample_name}-{sample}.parquet')

                #################### Define parameters for niches and run the clustering ####################

                features_NAS = get_param_for_niches(nodes, edges, tab_feature_to_compute_NAS,       # tab_markers
                                                    stat_funcs, stat_names, order, 
                                                    save_dir, patient, sample)
                
                cluster_labels = clustering_NAS(features_NAS,reducer_type, 
                                                    clusterer_type, n_neighbors, metric, 
                                                    min_dist, dim_clust, min_cluster_size,k_cluster,resolution, n_clusters,
                                                    save_dir, patient, sample)
                #################### Plot niches on niche composition and on spatial tysserand ####################
                counts = mosna.make_niches_composition(
                        var=nodes['Phenotypes'],       
                        niches=cluster_labels,        
                        var_label='Phenotypes',
                        normalize=normalize
                    )
                plot_niches(counts, cluster_labels, save_directory, patient, sample, type, panel, normalize=normalize)

                nodes[f'niches_{normalize}'] = cluster_labels
                pairs = edges[['source', 'target']].values
                tysserand(nodes[['X_position','Y_position']], pairs, cluster_labels, type, 
                        patient, sample, sample_name, save_directory, normalize=normalize)

    try:
        if IMC:
            if verif_file('IMC', define_panel('IMC')):
                process('IMC')
            else:
                raise ValueError("There is no IMC in your data or the Tysserand networks were not generated")
    except ValueError as e:
        print(f"\t[INFO] IMC error: {e}")

    try:
        if IF:
            if config_file['NAS']['panel'] == 'all':
                for panel in config_file['panel_list']:
                    if verif_file('IF', panel):
                        process('IF',panel)
                    else:
                        raise ValueError("There is no IF in your data or the Tysserand networks were not generated")
            else:
                if verif_file('IF', panel):
                    process('IF',panel)
                else:
                    raise ValueError("There is no IF in your data or the Tysserand networks were not generated")
                    
    except ValueError as e:
        print(f"\t[INFO] IF error: {e}")

if __name__ == "__main__":
    print('\n\n[NAS PROCESSING]')
    config_path = get_arguments()
    config_file = get_config(config_path)   
    main(config_file['NAS']['IF_perform'],
                config_file['NAS']['IMC_perform'],
                config_file)
