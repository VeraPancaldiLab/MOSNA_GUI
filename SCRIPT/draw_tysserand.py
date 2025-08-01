import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import warnings
import gc
import multiprocessing
import contextlib
from sklearn.exceptions import ConvergenceWarning, FitFailedWarning
warnings.simplefilter('ignore', FitFailedWarning)
warnings.simplefilter('ignore', ConvergenceWarning)
warnings.simplefilter('ignore', FutureWarning)
warnings.simplefilter('ignore', DeprecationWarning)
warnings.simplefilter('ignore', UserWarning)
import numpy as np
import pandas as pd
import yaml
import argparse
import matplotlib.pyplot as plt
from pathlib import Path
from tqdm import tqdm
import matplotlib as mpl
from phenograph.cluster import cluster

from tysserand import tysserand as ty
from mosna import mosna

import matplotlib as mpl
from concurrent.futures import ProcessPoolExecutor, as_completed

mpl.rcParams["figure.facecolor"] = 'white'
mpl.rcParams["axes.facecolor"] = 'white'
mpl.rcParams["savefig.facecolor"] = 'white'

########################################## Function ##########################################

def verif_file(type, panel=None):
    if os.path.isfile(f"./temp/{type}{panel}_cell_pos.parquet") and \
        os.path.isfile(f"./temp/{type}{panel}_cell_pos_pheno.parquet") and \
        os.path.isfile(f"./temp/{type}{panel}_markers.parquet") and \
        os.path.isfile(f"./temp/{type}{panel}_sample_cell.parquet"):
        return True
    return False

def define_panel(type, panel=None):
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

def define_sample_name(type):
    sample_name_dict={'IMC':'ROI', 'IF':'layer'}
    return sample_name_dict[type]

def import_data(dir, type, panel=None):
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
        sample_cell = pd.read_parquet(Path(dir) / f"IF_{panel}_sample_cell.parquet")
        markers = pd.read_parquet(Path(dir) / f"IF_{panel}_markers.parquet")
        if (Path(dir) / f"IF_{panel}_cell_pos_pheno.parquet").exists():
            cell_pos = pd.read_parquet(Path(dir) / f"IF_{panel}_cell_pos_pheno.parquet")
        else:
            cell_pos = pd.read_parquet(Path(dir) / f"IF_{panel}_cell_pos.parquet")
        cell_pos.drop(columns='patient', inplace=True)
        cell_pos.drop(columns=define_sample_name(type), inplace=True)

    return cell_pos, markers, sample_cell

def draw_tysserand_network(coords, clustering, patient, type, panel=None, method='delaunay', min_neighbors=3, sample=None, sample_name=None):
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
    pairs = ty.link_solitaries(coords, pairs, method=method, min_neighbors=min_neighbors, verbose=0)

    fig, ax = ty.plot_network(
        coords, pairs,labels=clustering,
        color_mapper=celltypes_color_mapper,
        legend_opt={'loc': 'center left', 'bbox_to_anchor': (1.05, 0.5), 'fontsize': 30, 'markerscale': 5},
        size_nodes=5,
        figsize=(30,30)
        )
    
    if sample == None:
        if type == 'IMC':
            plt.title(f"Draw an {type} Tysserand network for patient {patient}", fontsize=30)
            plt.savefig(f"OUTPUT_DATA/Tysserand_network/{type}_Tysserand_network_{patient}.png", bbox_inches="tight")
            plt.close(fig)
        if type == 'IF':
            plt.title(f"Draw an {type} Tysserand network for panel {panel} and patient {patient}", fontsize=30)
            plt.savefig(f"OUTPUT_DATA/Tysserand_network/{type}_{panel}_Tysserand_network_{patient}.png", bbox_inches="tight")
            plt.close(fig)
    else:
        if type == 'IMC':
            plt.title(f"Draw an {type} Tysserand network for patient {patient} and {sample_name} {sample}", fontsize=30)
            plt.savefig(f"OUTPUT_DATA/Tysserand_network/{type}_Tysserand_network_{patient}_{sample_name}_{sample}.png", bbox_inches="tight")
            plt.close(fig)
        if type == 'IF':
            plt.title(f"Draw an {type} Tysserand network for panel {panel} and patient {patient} and {sample_name} {sample}", fontsize=30)
            plt.savefig(f"OUTPUT_DATA/Tysserand_network/{type}_{panel}_Tysserand_network_{patient}_{sample_name}_{sample}.png",
                         bbox_inches="tight")
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

def phenograph_clustering(markers_to_cluster, k_neighbors, primary_metrics_phenograh):
    with open(os.devnull, 'w') as f, contextlib.redirect_stdout(f):
        clustering, graph_IF, Q = cluster(
            markers_to_cluster,
            k=k_neighbors,
            primary_metric=primary_metrics_phenograh,
            seed=10,
            n_jobs=1
            )
    del graph_IF
    gc.collect()
    return clustering, Q

def network_parallelization_process_patient_and_sample(patient_sample, sample_name, IF_cell_pos, IF_markers, IF_sample_cell, 
                      there_is_duplicata, type, panel=None,
                      make_phenograph=False, k_neighbors = 30, primary_metrics_phenograh='minkowski', normalize = False, 
                      method='delaunay', min_neighbors=3):

        filtre = ((IF_sample_cell['patient'] == patient_sample[0]) &
                    (IF_sample_cell[f'{sample_name}'] == patient_sample[1]))

        if there_is_duplicata:
            cells_df = IF_sample_cell.loc[filtre, ['CellID']]
            markers_to_cluter_IF = cells_df.merge(IF_markers.drop_duplicates(subset='CellID'), on='CellID', how='left')
            cell_ID_pos = cells_df.merge(IF_cell_pos.drop_duplicates(subset='CellID'), on='CellID', how='left')
            coords = cells_df.merge(IF_cell_pos.drop_duplicates(subset='CellID'), on='CellID', how='left') 
            coords = coords.drop(columns=['CellID','Phenotypes'])
            nodes = markers_to_cluter_IF.merge(cell_ID_pos, on='CellID', how='left', suffixes=('_marker', '_pos'))
            nodes['patient'] = patient_sample[0]
            nodes[f'{sample_name}'] = patient_sample[1]


        else:
            cells = IF_sample_cell.loc[filtre, 'CellID'].drop_duplicates()
            coords = IF_cell_pos.loc[filtre, ['X_position','Y_position']]
            markers_to_cluter_IF = IF_markers[IF_markers['CellID'].isin(cells)].drop_duplicates(subset='CellID')
            cell_ID_pos = IF_cell_pos.loc[filtre, ['CellID','X_position','Y_position','Phenotypes']]
            nodes = markers_to_cluter_IF.merge(cell_ID_pos, on='CellID', how='left', suffixes=('_marker', '_pos'))
            nodes['patient'] = patient_sample[0]
            nodes[f'{sample_name}'] = patient_sample[1]

            

        if make_phenograph:
     
            markers_to_cluter_IF = markers_to_cluter_IF.set_index('CellID')
            if normalize:
                markers_to_cluter_IF = normalize_markers(markers_to_cluter_IF)
                
            clustering_IF, Q_IF = phenograph_clustering(markers_to_cluter_IF, k_neighbors, primary_metrics_phenograh)
            cell_ID_pos['Phenotypes']=clustering_IF
 
                
        else:
            clustering_IF=cell_ID_pos['Phenotypes']
                

        pairs = draw_tysserand_network(coords, clustering_IF, patient_sample[0], type=type, panel=panel, sample=patient_sample[1], method=method, min_neighbors=min_neighbors, sample_name=sample_name)
    
        del coords, cell_ID_pos, clustering_IF, markers_to_cluter_IF
        if 'cells' in locals():
            del cells
        if 'cells_df' in locals():
            del cells_df
        gc.collect()

        edges = pd.DataFrame(data=pairs, columns=['source', 'target'])
        sample_name_for_file = sample_name.replace('_', '-')
        if type == 'IMC':
            edges.to_parquet(Path(f"temp/{type}_networks_sample") / f'edges_patient-{patient_sample[0]}_{sample_name_for_file}-{patient_sample[1]}.parquet', index=False)
            nodes.to_parquet(Path(f"temp/{type}_networks_sample") / f'nodes_patient-{patient_sample[0]}_{sample_name_for_file}-{patient_sample[1]}.parquet', index=False)
        if type == 'IF':
            edges.to_parquet(Path(f"temp/{type}_{panel}_networks_sample") / f'edges_patient-{patient_sample[0]}_{sample_name_for_file}-{patient_sample[1]}.parquet', index=False)
            nodes.to_parquet(Path(f"temp/{type}_{panel}_networks_sample") / f'nodes_patient-{patient_sample[0]}_{sample_name_for_file}-{patient_sample[1]}.parquet', index=False)
        del edges, pairs, nodes
        gc.collect()

def network_parallelization_process_patient(patient, sample_name, IF_cell_pos, IF_markers, IF_sample_cell, 
                      there_is_duplicata, type, panel=None,
                      make_phenograph=False, k_neighbors = 30, primary_metrics_phenograh='minkowski', normalize = False, 
                      method='delaunay', min_neighbors=3):

        filtre = IF_sample_cell['patient'] == patient

        if there_is_duplicata:
            cells_df = IF_sample_cell.loc[filtre, ['CellID']]
            markers_to_cluter_IF = cells_df.merge(IF_markers.drop_duplicates(subset='CellID'), on='CellID', how='left')
            cell_ID_pos = cells_df.merge(IF_cell_pos.drop_duplicates(subset='CellID'), on='CellID', how='left')
            coords = cells_df.merge(IF_cell_pos.drop_duplicates(subset='CellID'), on='CellID', how='left') 
            coords=coords.drop(columns=['CellID','Phenotypes'])
            nodes = markers_to_cluter_IF.merge(cell_ID_pos, on='CellID', how='left', suffixes=('_marker', '_pos'))
            nodes['patient'] = patient

        else:
            cells = IF_sample_cell.loc[filtre, 'CellID'].drop_duplicates()
            coords = IF_cell_pos.loc[filtre, ['X_position','Y_position']]
            markers_to_cluter_IF = IF_markers[IF_markers['CellID'].isin(cells)].drop_duplicates(subset='CellID')
            cell_ID_pos = IF_cell_pos.loc[filtre, ['CellID','X_position','Y_position','Phenotypes']]
            nodes = markers_to_cluter_IF.merge(cell_ID_pos, on='CellID', how='left', suffixes=('_marker', '_pos'))
            nodes['patient'] = patient

                        
        if make_phenograph:
            markers_to_cluter_IF = markers_to_cluter_IF.set_index('CellID')
                

            if normalize:
                markers_to_cluter_IF = normalize_markers(markers_to_cluter_IF)
                
            clustering_IF, Q_IF = phenograph_clustering(markers_to_cluter_IF, k_neighbors, primary_metrics_phenograh)
            cell_ID_pos['Phenotypes']=clustering_IF

                
        else:
            clustering_IF=cell_ID_pos['Phenotypes']

        pairs = draw_tysserand_network(coords, clustering_IF, patient, type=type, panel=panel, method=method, min_neighbors=min_neighbors)
        del coords, cell_ID_pos, clustering_IF, markers_to_cluter_IF
        if 'cells' in locals():
            del cells
        if 'cells_df' in locals():
            del cells_df
        gc.collect()

        edges = pd.DataFrame(data=pairs, columns=['source', 'target'])
        if type == 'IMC':
            edges.to_parquet(Path(f"OUTPUT_DATA/{type}_networks_sample") / f'edges_patient-{patient}.parquet', index=False)
            nodes.to_parquet(Path(f"OUTPUT_DATA/nodes/{type}_networks_sample") / f'nodes_patient-{patient}.parquet', index=False)
        if type == 'IF':
            edges.to_parquet(Path(f"OUTPUT_DATA/{type}_{panel}_networks_sample") / f'edges_patient-{patient}.parquet', index=False)
            nodes.to_parquet(Path(f"OUTPUT_DATA/nodes/{type}_{panel}_networks_sample") / f'nodes_patient-{patient}.parquet', index=False)
        del edges, pairs, nodes
        gc.collect()

def verif_cpu(cpu, unique_list):
    if cpu > multiprocessing.cpu_count():
        cpu = min(multiprocessing.cpu_count(), len(unique_list))
        tqdm.write(f"\t[INFO] You've selected a higher number of cpu than your current available cpu : {multiprocessing.cpu_count()}")
    if cpu > len(unique_list):
        cpu = min(cpu, len(unique_list))
        tqdm.write(f"\t[INFO] You've selected a higher number of cpu than the number needed : {multiprocessing.cpu_count()}")
    tqdm.write(f"\t[INFO] you are currently using {cpu} cpu")
    return cpu

def tysserand_network(IF_cell_pos, IF_markers, IF_sample_cell, 
                      there_is_duplicata, type, panel=None,
                      make_phenograph=False, k_neighbors = 30, primary_metrics_phenograh='minkowski', normalize = False, 
                      method='delaunay', min_neighbors=3, cpu=4):
    
    if type == 'IMC':  
        sample_name = 'ROI'
    else:
        sample_name = 'layer'

    if 'Phenotypes' not in IF_cell_pos:
        IF_cell_pos['Phenotypes'] = ''

    if sample_name in IF_sample_cell.columns:
        unique_patient_samples = IF_sample_cell[['patient',sample_name]].drop_duplicates()
        unique_list = list(unique_patient_samples.itertuples(index=False, name=None))
        cpu = verif_cpu(cpu, unique_list)
        args_list = [(patient_sample, sample_name, IF_cell_pos, IF_markers, IF_sample_cell, 
                    there_is_duplicata, type, panel, make_phenograph, k_neighbors, 
                    primary_metrics_phenograh, normalize, method, min_neighbors)
                    for patient_sample in unique_list]
        
        with ProcessPoolExecutor(max_workers=cpu) as executor:
            futures = {
                executor.submit(network_parallelization_process_patient_and_sample, *args): args[0]
                for args in args_list
            }
            for future in tqdm(as_completed(futures), total=len(futures), desc=f"\t[MULTI PROCESS] └─ Processing {type} file"):
                patient = futures[future]
                try:
                    future.result()
                except Exception as e:
                    tqdm.write(f"[Erreur] patient={patient} : {e}")      
        del unique_list, unique_patient_samples
        gc.collect()

    else:
        unique_patient_samples = IF_sample_cell['patient'].drop_duplicates()
        unique_list = unique_patient_samples.tolist()
        cpu = verif_cpu(cpu, unique_list)
        args_list = [(patient, sample_name, IF_cell_pos, IF_markers, IF_sample_cell, 
                    there_is_duplicata, type, make_phenograph, k_neighbors, 
                    primary_metrics_phenograh, normalize, method, min_neighbors)
                    for patient in unique_list]

        with ProcessPoolExecutor(max_workers=cpu) as executor:
            futures = {
                executor.submit(network_parallelization_process_patient, *args): args[0]
                for args in args_list
            }
            for future in tqdm(as_completed(futures), total=len(futures), desc=f"\t[PROCESS] └─ Processing {type} file"):
                patient = futures[future]
                try:
                    future.result()
                except Exception as e:
                    tqdm.write(f"[Erreur] patient={patient} : {e}")
        del unique_list, unique_patient_samples
        gc.collect()

########################################## Main ##########################################

def main(IF, IMC, config_file):
    Path('OUTPUT_DATA/Tysserand_network').mkdir(parents=True, exist_ok=True)
    def process(type, panel=None):
        Path(f'temp/{type}{define_panel(type, panel)}_networks_sample').mkdir(parents=True, exist_ok=True)

        cell_pos, markers, sample_cell = import_data('./temp', type, panel)
        
        tysserand_network(cell_pos, markers, sample_cell, config_file["tysserand"][f'{type}_duplicata'], type, panel,
                          config_file['phenograph'],
                          config_file['k_neighbors_phenograph'],
                          config_file['primary_metric_phenograph'],
                          config_file[f'{type}_normalization'],
                          config_file['tysserand']['method_tysserand'],
                          config_file['tysserand']['min_neighbors'], cpu=config_file['tysserand']['cpu'])
        

    try:
        if IMC:
            if verif_file('IMC', define_panel('IMC')):
                tqdm.write(f"\n\n\t[INFO] process on IMC")
                process('IMC')
            else:
                raise ValueError("There is no IMC in your data")
    except ValueError as e:
        tqdm.write(f"IMC error: {e}")

    try:
        if IF:
            if config_file['tysserand']['panel'] == 'all':
                for panel in config_file['panel_list']:
                        if verif_file('IF', define_panel('IF', panel)):
                            tqdm.write(f"\n\n\t[INFO] process on {panel} panel")
                            process('IF', panel)
                        else:
                            raise ValueError("There is no IF in your data")

            else:
                if verif_file('IF', define_panel('IF', config_file['tysserand']['panel'])):
                    tqdm.write(f"\n\n\t[INFO] process on {config_file['tysserand']['panel']} panel")
                    process('IF')
                else:
                    raise ValueError("There is no IF in your data")

    except ValueError as e:
        tqdm.write(f"IF error: {e}")

if __name__ == "__main__":
    tqdm.write('\n[TYSSERAND NETWORK GENERATION]')
    config_path = get_arguments()
    config_file = get_config(config_path)

    main(config_file['tysserand']['IF_perform'],
                config_file['tysserand']['IMC_perform'],
                config_file)

