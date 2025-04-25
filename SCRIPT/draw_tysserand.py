import os
import sys
import warnings
import contextlib
import gc

warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
with open(os.devnull, 'w') as fnull:
    with contextlib.redirect_stderr(fnull):

        import numpy as np
        import pandas as pd
        import yaml
        import argparse
        import matplotlib.pyplot as plt
        import seaborn as sns
        from time import time
        from pathlib import Path
        from time import time
        from tqdm import tqdm
        import copy
        import matplotlib as mpl
        import colorcet as cc
        import composition_stats as cs
        from phenograph.cluster import cluster
    
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
        plt.savefig(f"output_data/Tysserand_network/{type}_Tysserand_network_{patient}.png", bbox_inches="tight")
        plt.close(fig)
    
    else:
        plt.title(f"Draw an {type} Tysserand network for patient {patient} and sample {sample} with a clustering qualitie Q = {Q}", fontsize=30)
        plt.savefig(f"output_data/Tysserand_network/{type}_Tysserand_network_{patient}_{sample}.png", bbox_inches="tight")
        plt.close(fig)
    del clusters_cmap, n_colors, celltypes_color_mapper, uniq, fig
    gc.collect()
    return pairs

def normalize_markers(markers_by_patient_sample):
    for markers in markers_by_patient_sample:
                        # Calculate 99.9th percentile value for column

        p99_9 = markers_by_patient_sample[markers].quantile(0.999)
                            
                        # Ensure values above the 99.9th percentile are not more than this value
        markers_by_patient_sample[markers] = markers_by_patient_sample[markers].clip(upper=p99_9)
                            
                        # Normalize based on 99.9th percentile value
        markers_by_patient_sample[markers] = (markers_by_patient_sample[markers] - markers_by_patient_sample[markers].min()) / (p99_9 - markers_by_patient_sample[markers].min())
    return markers_by_patient_sample

def tysserand_network(IF_cell_pos, IF_markers, IF_sample_cell, there_is_duplicata, type, k_neighbors = 30, primary_metrics_phenograh='minkowski', method='delaunay', min_neighbors=3, normalize = False, sample_take_an_other_name='sample'):
    if sample_take_an_other_name is None:  
        sample_name = 'sample'
    else:
        sample_name = sample_take_an_other_name
    if sample_name in IF_sample_cell.columns:
        unique_patient_samples = IF_sample_cell[['patient',sample_name]].drop_duplicates()
        unique_list = list(unique_patient_samples.itertuples(index=False, name=None))

        for patient_sample in tqdm(unique_list, desc=f" └─ Processing {type} file", position=1):
            tqdm.write(f"{type} Tysserand for patient {patient_sample[0]} and {sample_name} {patient_sample[1]}")
            filtre = ((IF_sample_cell['patient'] == patient_sample[0]) &
                        (IF_sample_cell['sample'] == patient_sample[1]))

            if there_is_duplicata:
                cells_df = IF_sample_cell.loc[filtre, ['CellID']]
                markers_to_cluter_IF = cells_df.merge(IF_markers.drop_duplicates(subset='CellID'), on='CellID', how='left')
                cell_ID_pos = cells_df.merge(IF_cell_pos.drop_duplicates(subset='CellID'), on='CellID', how='left')
                coords = cells_df.merge(IF_cell_pos.drop_duplicates(subset='CellID'), on='CellID', how='left') 
                coords = coords.drop(columns='CellID')
                nodes = markers_to_cluter_IF.merge(cell_ID_pos, on='CellID', how='left', suffixes=('_marker', '_pos'))
                nodes['patient'] = patient[0]
                nodes[f'{sample_name}'] = patient[1]
                tqdm.write(f"\tTysserand networks with : {len(markers_to_cluter_IF)} cells")

            else:
                cells = IF_sample_cell.loc[filtre, 'CellID'].drop_duplicates()
                coords = IF_cell_pos.loc[filtre, ['X_position','Y_position']]
                markers_to_cluter_IF = IF_markers[IF_markers['CellID'].isin(cells)].drop_duplicates(subset='CellID')
                cell_ID_pos = IF_cell_pos.loc[filtre, ['CellID','X_position','Y_position']]
                nodes = markers_to_cluter_IF.merge(cell_ID_pos, on='CellID', how='left', suffixes=('_marker', '_pos'))
                nodes['patient'] = patient_sample[0]
                nodes[f'{sample_name}'] = patient_sample[1]
                tqdm.write(f"\tTysserand networks with : {len(markers_to_cluter_IF)} cells")

            tqdm.write("\tCLUSTERING BY PHENOGRAPH",end='\t\t\t')       
            markers_to_cluter_IF = markers_to_cluter_IF.set_index('CellID')
            if normalize:
                markers_to_cluter_IF = normalize_markers(markers_to_cluter_IF)
            
            
            with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
                clustering_IF, graph_IF, Q_IF = cluster(
                    markers_to_cluter_IF,
                    k=k_neighbors,
                    primary_metric=primary_metrics_phenograh,
                    seed=10,
                    n_jobs=1
                )
            cell_ID_pos['cluster']=clustering_IF
            
            tqdm.write("DONE\n\tDRAW TYSSERAND NETWORK",end='\t\t\t')

            with open(os.devnull, 'w') as c, contextlib.redirect_stdout(c):
                pairs = draw_tysserand_network(coords, clustering_IF, Q_IF, patient_sample[0], type=type,sample=patient_sample[1], method=method, min_neighbors=min_neighbors)
    
            del coords, cell_ID_pos, graph_IF, clustering_IF, markers_to_cluter_IF
            if 'cells' in locals():
                del cells
            if 'cells_df' in locals():
                del cells_df
            gc.collect()
            tqdm.write("\t\t\t\tDONE\n")
            edges = pd.DataFrame(data=pairs, columns=['source', 'target'])
            edges.to_parquet(Path(f"output_data/edges/{type}") / f'edges_patient_{patient_sample[0]}_{sample_name}_{patient_sample[1]}.parquet', index=False)
            nodes.to_parquet(Path(f"output_data/nodes/{type}") / f'nodes_patient_{patient_sample[0]}_{sample_name}_{patient_sample[1]}.parquet', index=False)
        del unique_list, unique_patient_samples, edges, pairs, nodes
        gc.collect()

    else:
        unique_patient_samples = IF_sample_cell['patient'].drop_duplicates()
        unique_list = unique_patient_samples.tolist()


        for patient in tqdm(unique_list, desc=f" └─ Processing {type} file", position=1):
            tqdm.write(f"{type} Tysserand for patient {patient}")
            filtre = IF_sample_cell['patient'] == patient

            if there_is_duplicata:
                cells_df = IF_sample_cell.loc[filtre, ['CellID']]
                markers_to_cluter_IF = cells_df.merge(IF_markers.drop_duplicates(subset='CellID'), on='CellID', how='left')
                cell_ID_pos = cells_df.merge(IF_cell_pos.drop_duplicates(subset='CellID'), on='CellID', how='left')
                coords = cells_df.merge(IF_cell_pos.drop_duplicates(subset='CellID'), on='CellID', how='left') 
                coords=coords.drop(columns='CellID')
                nodes = markers_to_cluter_IF.merge(cell_ID_pos, on='CellID', how='left', suffixes=('_marker', '_pos'))
                nodes['patient'] = patient
                tqdm.write(f"\tTysserand networks with : {len(markers_to_cluter_IF)} cells")
            else:
                cells = IF_sample_cell.loc[filtre, 'CellID'].drop_duplicates()
                coords = IF_cell_pos.loc[filtre, ['X_position','Y_position']]
                markers_to_cluter_IF = IF_markers[IF_markers['CellID'].isin(cells)].drop_duplicates(subset='CellID')
                cell_ID_pos = IF_cell_pos.loc[filtre, ['CellID','X_position','Y_position']]
                nodes = markers_to_cluter_IF.merge(cell_ID_pos, on='CellID', how='left', suffixes=('_marker', '_pos'))
                nodes['patient'] = patient
                tqdm.write(f"\tTysserand networks with : {len(markers_to_cluter_IF)} cells")
                        
            markers_to_cluter_IF = markers_to_cluter_IF.set_index('CellID')
            tqdm.write("\tCLUSTERING BY PHENOGRAPH",end='\t\t\t')
            if normalize:
                markers_to_cluter_IF = normalize_markers(markers_to_cluter_IF)
            
            with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
                clustering_IF, graph_IF, Q_IF = cluster(
                    markers_to_cluter_IF,
                    k=k_neighbors,
                    primary_metric=primary_metrics_phenograh,
                    seed=10,
                    n_jobs=1
                )
            cell_ID_pos['cluster']=clustering_IF
            tqdm.write("DONE\n\tDRAW TYSSERAND NETWORK",end='\t\t\t')

            with open(os.devnull, 'w') as c, contextlib.redirect_stdout(c):
                pairs = draw_tysserand_network(coords, clustering_IF, Q_IF, patient, type=type, method=method, min_neighbors=min_neighbors)
            del coords, cell_ID_pos, graph_IF, clustering_IF, markers_to_cluter_IF
            if 'cells' in locals():
                del cells
            if 'cells_df' in locals():
                del cells_df
            gc.collect()
            tqdm.write("\t\t\t\tDONE\n")
            edges = pd.DataFrame(data=pairs, columns=['source', 'target'])
            edges.to_parquet(Path(f"output_data/edges/{type}") / f'edges_patient_{patient}.parquet', index=False)
            nodes.to_parquet(Path(f"output_data/nodes/{type}") / f'nodes_patient_{patient}.parquet', index=False)
        del unique_list, unique_patient_samples, edges, pairs, nodes
        gc.collect()

def main():
    print('\n')
    config_path = get_arguments()
    config_file = get_config(config_path)

    if config_file['IF_import']['present_in'] and not config_file['IMC_import']['present_in']:
        IF_cell_pos, IF_markers, IF_sample_cell = import_data(config_file['standard']['output_dir'],
                                                            config_file['IMC_import']['present_in'],
                                                            config_file['IF_import']['present_in'])
        if config_file['IF_import']['re_index']:
            IF_cell_pos['CellID'] = IF_cell_pos.index
            IF_markers['CellID'] = IF_markers.index
            IF_sample_cell['CellID'] = IF_sample_cell.index


    if config_file['IMC_import']['present_in'] and not config_file['IF_import']['present_in']:
        IMC_cell_pos, IMC_markers, IMC_sample_cell = import_data(config_file['standard']['output_dir'],
                                                            config_file['IMC_import']['present_in'],
                                                            config_file['IF_import']['present_in'])
        if config_file['IF_import']['re_index']:
            IF_cell_pos['CellID'] = IF_cell_pos.index
            IF_markers['CellID'] = IF_markers.index
            IF_sample_cell['CellID'] = IF_sample_cell.index



    if config_file['IMC_import']['present_in'] and config_file['IF_import']['present_in']:
        IMC_cell_pos, IMC_markers, IMC_sample_cell, IF_cell_pos, IF_markers, IF_sample_cell = import_data(config_file['standard']['output_dir'],
                                                            config_file['IMC_import']['present_in'],
                                                            config_file['IF_import']['present_in'])

        if config_file['IMC_import']['re_index']:
            IMC_cell_pos['CellID'] = IMC_cell_pos.index
            IMC_markers['CellID'] = IMC_markers.index
            IMC_sample_cell['CellID'] = IMC_sample_cell.index
        if config_file['IF_import']['re_index']:
            IF_cell_pos['CellID'] = IF_cell_pos.index
            IF_markers['CellID'] = IF_markers.index
            IF_sample_cell['CellID'] = IF_sample_cell.index

        tysserand_network(IF_cell_pos, IF_markers, IF_sample_cell, config_file['IF_import']['there_is_duplicata'], 'IF',
                          config_file['tysserand']['k_neighbors_phenograph'],
                          config_file['tysserand']['primary_metric_phenograph'],
                          config_file['tysserand']['method_tysserand'],
                          config_file['tysserand']['min_neighbors'],
                          config_file['IF_import']['normalize'],
                          config_file['IF_import']['if_sample_take_an_other_name'])
        
        tysserand_network(IMC_cell_pos, IMC_markers, IMC_sample_cell, config_file['IMC_import']['there_is_duplicata'], 'IMC',
                          config_file['tysserand']['k_neighbors_phenograph'],
                          config_file['tysserand']['primary_metric_phenograph'],
                          config_file['tysserand']['method_tysserand'],
                          config_file['tysserand']['min_neighbors'],
                          config_file['IMC_import']['normalize'],
                          config_file['IF_import']['if_sample_take_an_other_name'])
        
if __name__ == "__main__":
    main()