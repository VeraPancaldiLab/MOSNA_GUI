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
from phenograph.cluster import cluster
import contextlib
import sys
import warnings
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 

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
        IF_sample_cell = pd.read_parquet(Path(dir) / "IF_sample_cell.parquet")
        IF_cell_pos = pd.read_parquet(Path(dir) / "IF_cell_pos.parquet")
        IF_markers = pd.read_parquet(Path(dir) / "IF_markers.parquet")

    if IF and not IMC:
        return IF_cell_pos, IF_markers, IF_sample_cell
    if IMC and not IF:
        return IMC_cell_pos, IMC_markers, IMC_sample_cell
    if IMC and IF:
        return IMC_cell_pos, IMC_markers, IMC_sample_cell, IF_cell_pos, IF_markers, IF_sample_cell

def draw_tysserand_network(coords, clustering, Q, patient, type, method='delaunay', min_neighbors=3, sample=None):
    if clustering is not None:
        nb_clust = clustering.max()
        uniq = pd.Series(clustering).value_counts().index

        # choose colormap
        clusters_cmap = mosna.make_cluster_cmap(uniq)
        # make color mapper
        # series to sort by decreasing order
        n_colors = len(clusters_cmap)
        celltypes_color_mapper = {x: clusters_cmap[i % n_colors] for i, x in enumerate(uniq)}

    coords = np.array(coords.values.tolist())
    pairs = ty.build_delaunay(coords)
        # we want to avoid isolated cells, so we link them to their 3 closest neighbors
    pairs = ty.link_solitaries(coords, pairs, method=method, min_neighbors=min_neighbors)

    fig, ax = ty.plot_network(
        coords, pairs,labels=clustering,
        color_mapper=celltypes_color_mapper,
        legend_opt={'loc': 'center left', 'bbox_to_anchor': (1.05, 0.5), 'fontsize': 30, 'markerscale': 5},
        size_nodes=5,
        figsize=(30,30)
        )
    if sample == None:
        plt.title(f"Draw an {type} Tysserand network for patient {patient} with a clustering qualitie Q = {Q}", fontsize=30)
        plt.savefig(f"../Tysserand_network/{type}_Tysserand_network_{patient}.png")
    else:
        plt.title(f"Draw an {type} Tysserand network for patient {patient} and sample {sample} with a clustering qualitie Q = {Q}", fontsize=30)
        plt.savefig(f"../Tysserand_network/{type}_Tysserand_network_{patient}_{sample}.png")
    return 

def tysserand_network(IF_cell_pos, IF_markers, IF_sample_cell, there_is_duplicata, k_neighbors = 30, primary_metrics_phenograh='minkowski', method='delaunay', min_neighbors=3):
    if 'sample' in IF_sample_cell.columns:
        unique_patient_samples = IF_sample_cell[['patient','sample']].drop_duplicates()
        unique_list = list(unique_patient_samples.itertuples(index=False, name=None))

        for patient_sample in unique_list:
            print(f"Tysserand for patient {patient_sample[0]} and sample {patient_sample[1]}")
            filtre = ((IF_sample_cell['patient'] == patient_sample[0]) &
                        (IF_sample_cell['sample'] == patient_sample[1]))

            if there_is_duplicata:
                cells_df = IF_sample_cell.loc[filtre, ['CellID']]
                markers_to_cluter_IF = cells_df.merge(IF_markers.drop_duplicates(subset='CellID'), on='CellID', how='left')
                cell_ID_pos = cells_df.merge(IF_cell_pos.drop_duplicates(subset='CellID'), on='CellID', how='left')
                coords = cells_df.merge(IF_cell_pos.drop_duplicates(subset='CellID'), on='CellID', how='left') 
                print(f"\tTysserand networks with : {len(markers_to_cluter_IF)} cells")
            else:
                cells = IF_sample_cell.loc[filtre, 'CellID'].drop_duplicates()
                coords = IF_cell_pos.loc[filtre, ['X_position','Y_position']]
                markers_to_cluter_IF = IF_markers[IF_markers['CellID'].isin(cells)].drop_duplicates(subset='CellID')
                cell_ID_pos = IF_cell_pos.loc[filtre, ['CellID','X_position','Y_position']]
                        
            verif = len(markers_to_cluter_IF) 
            markers_to_cluter_IF = markers_to_cluter_IF.set_index('CellID')
            
            print("\tCLUSTERING BY PHENOGRAPH",end='\t\t\t')
            with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
                clustering_IF, graph_IF, Q_IF = cluster(
                    markers_to_cluter_IF,
                    k=k_neighbors,
                    primary_metric=primary_metrics_phenograh,
                    seed=10,
                    n_jobs=1
                )
            cell_ID_pos['cluster']=clustering_IF
            coords=coords.drop(columns='CellID')

            print("DONE\n\tDRAW TYSSERAND NETWORK",end='\t\t\t')
            draw_tysserand_network(coords, clustering_IF, Q_IF, patient_sample[0], 'IF',sample=patient_sample[1], method=method, min_neighbors=min_neighbors)
            print("DONE")

    else:
        unique_patient_samples = IF_sample_cell['patient'].drop_duplicates()
        unique_list = unique_patient_samples.tolist()


        for patient in unique_list:
            print(f"Tysserand for patient {patient}")
            filtre = IF_sample_cell['patient'] == patient

            if there_is_duplicata:
                cells_df = IF_sample_cell.loc[filtre, ['CellID']]
                markers_to_cluter_IF = cells_df.merge(IF_markers.drop_duplicates(subset='CellID'), on='CellID', how='left')
                cell_ID_pos = cells_df.merge(IF_cell_pos.drop_duplicates(subset='CellID'), on='CellID', how='left')
                coords = cells_df.merge(IF_cell_pos.drop_duplicates(subset='CellID'), on='CellID', how='left') 
                print(f"\tTysserand networks with : {len(markers_to_cluter_IF)} cells")
            else:
                cells = IF_sample_cell.loc[filtre, 'CellID'].drop_duplicates()
                coords = IF_cell_pos.loc[filtre, ['X_position','Y_position']]
                markers_to_cluter_IF = IF_markers[IF_markers['CellID'].isin(cells)].drop_duplicates(subset='CellID')
                cell_ID_pos = IF_cell_pos.loc[filtre, ['CellID','X_position','Y_position']]
                        
            verif = len(markers_to_cluter_IF) 
            markers_to_cluter_IF = markers_to_cluter_IF.set_index('CellID')
            
            print("\tCLUSTERING BY PHENOGRAPH",end='\t\t\t')
            with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
                clustering_IF, graph_IF, Q_IF = cluster(
                    markers_to_cluter_IF,
                    k=k_neighbors,
                    primary_metric=primary_metrics_phenograh,
                    seed=10,
                    n_jobs=1
                )
            cell_ID_pos['cluster']=clustering_IF
            coords=coords.drop(columns='CellID')

            print("DONE\n\tDRAW TYSSERAND NETWORK",end='\t\t\t')
            draw_tysserand_network(coords, clustering_IF, Q_IF, patient, 'IF', method=method, min_neighbors=min_neighbors)
            print("DONE")
    
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
        tysserand_network(IF_cell_pos, IF_markers, IF_sample_cell, True, config_file['tysserand']['k_neighbors_phenograph'],
                          config_file['tysserand']['primary_metric_phenograph'],
                          config_file['tysserand']['method_tysserand'],
                          config_file['tysserand']['min_neighbors'])
        tysserand_network(IMC_cell_pos, IMC_markers, IMC_sample_cell, True, config_file['tysserand']['k_neighbors_phenograph'],
                          config_file['tysserand']['primary_metric_phenograph'],
                          config_file['tysserand']['method_tysserand'],
                          config_file['tysserand']['min_neighbors'])
if __name__ == "__main__":
    main()