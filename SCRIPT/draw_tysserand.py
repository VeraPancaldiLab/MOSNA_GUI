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
import glob
import argparse
import matplotlib.pyplot as plt
from pathlib import Path
from tqdm import tqdm
import matplotlib as mpl
from phenograph.cluster import cluster

from tysserand import tysserand as ty
from mosna import mosna

import matplotlib._pylab_helpers as matpy
import matplotlib as mpl
from concurrent.futures import ProcessPoolExecutor, as_completed

mpl.use("Agg")
mpl.rcParams["figure.facecolor"] = 'white'
mpl.rcParams["axes.facecolor"] = 'white'
mpl.rcParams["savefig.facecolor"] = 'white'

########################################## Function ##########################################

def verif_file(type, panel=None):
    return len(glob.glob(f"./temp/{type}{panel}*.parquet")) > 0

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
    plt.close('all')
    matpy.Gcf.destroy_all()
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

def network_parallelization_process_patient_and_sample(patient_sample, sample_name, Cells, markers, 
                      there_is_duplicata, type, panel=None,
                      make_phenograph=False, k_neighbors = 30, primary_metrics_phenograh='minkowski', normalize = False, 
                      method='delaunay', min_neighbors=3):

        filtre = ((Cells['patient'] == patient_sample[0]) &
                    (Cells[f'{sample_name}'] == patient_sample[1]))

        if there_is_duplicata:
            cells_df = Cells.loc[filtre, ['CellID']]
            cell_ID_pos = cells_df.merge(Cells.drop_duplicates(subset='CellID'), on='CellID', how='left')
            coords = cells_df.merge(Cells.drop_duplicates(subset='CellID'), on='CellID', how='left') 
            coords = coords.drop(columns=['CellID','Phenotypes'])

            if markers is not None:
                markers_to_cluter = cells_df.merge(markers.drop_duplicates(subset='CellID'), on='CellID', how='left')
            
        else:
            cells = Cells.loc[filtre, 'CellID'].drop_duplicates()
            coords = Cells.loc[filtre, ['X_position','Y_position']]
            cell_ID_pos = Cells.loc[filtre, ['CellID','X_position','Y_position','Phenotypes']]

            if markers is not None:
                markers_to_cluter = cells_df.merge(markers.drop_duplicates(subset='CellID'))


        if make_phenograph:
            markers_to_cluter = markers_to_cluter.set_index('CellID')
            if normalize:
                markers_to_cluter = normalize_markers(markers_to_cluter)
                
            clustering, Q = phenograph_clustering(markers_to_cluter, k_neighbors, primary_metrics_phenograh)
            cell_ID_pos['Phenotypes'] = clustering

            del markers_to_cluter
        else:
            clustering = cell_ID_pos['Phenotypes']
                

        pairs = draw_tysserand_network(coords, clustering, patient_sample[0], type=type, panel=panel, 
                                       sample=patient_sample[1], method=method,
                                       min_neighbors=min_neighbors, sample_name=sample_name)
    
        del coords, clustering
        if 'cells' in locals():
            del cells
        if 'cells_df' in locals():
            del cells_df
        gc.collect()

        edges = pd.DataFrame(data=pairs, columns=['source', 'target'])
        sample_name_for_file = sample_name.replace('_', '-')
        if type == 'IMC':
            edges.to_parquet(Path(f"temp/{type}_networks_sample") / f'edges_patient-{patient_sample[0]}_{sample_name_for_file}-{patient_sample[1]}.parquet', index=False)
            cell_ID_pos.to_parquet(Path(f"temp/{type}_networks_sample") / f'nodes_patient-{patient_sample[0]}_{sample_name_for_file}-{patient_sample[1]}.parquet', index=False)
        if type == 'IF':
            edges.to_parquet(Path(f"temp/{type}_{panel}_networks_sample") / f'edges_patient-{patient_sample[0]}_{sample_name_for_file}-{patient_sample[1]}.parquet', index=False)
            cell_ID_pos.to_parquet(Path(f"temp/{type}_{panel}_networks_sample") / f'nodes_patient-{patient_sample[0]}_{sample_name_for_file}-{patient_sample[1]}.parquet', index=False)
        del edges, pairs, cell_ID_pos
        gc.collect()

def network_parallelization_process_patient(patient, Cells, markers, 
                      there_is_duplicata, type, panel=None,
                      make_phenograph=False, k_neighbors = 30, primary_metrics_phenograh='minkowski', normalize = False, 
                      method='delaunay', min_neighbors=3):

        filtre = Cells['patient'] == patient

        if there_is_duplicata:
            cells_df = Cells.loc[filtre, ['CellID']]
            cell_ID_pos = cells_df.merge(Cells.drop_duplicates(subset='CellID'), on='CellID', how='left')
            coords = cells_df.merge(Cells.drop_duplicates(subset='CellID'), on='CellID', how='left') 
            coords=coords.drop(columns=['CellID','Phenotypes'])
            
            if markers is not None:
                markers_to_cluter = cells_df.merge(markers.drop_duplicates(subset='CellID'), on='CellID', how='left')

        else:
            cells = Cells.loc[filtre, 'CellID'].drop_duplicates()
            coords = Cells.loc[filtre, ['X_position','Y_position']]
            cell_ID_pos = Cells.loc[filtre, ['CellID','X_position','Y_position','Phenotypes']]

            if markers is not None:
                markers_to_cluter = markers[markers['CellID'].isin(cells)].drop_duplicates(subset='CellID')

                        
        if make_phenograph:
            markers_to_cluter = markers_to_cluter.set_index('CellID')
            if normalize:
                markers_to_cluter = normalize_markers(markers_to_cluter)
            clustering, Q = phenograph_clustering(markers_to_cluter, k_neighbors, primary_metrics_phenograh)
            cell_ID_pos['Phenotypes'] = clustering
            del markers_to_cluter

        else:
            clustering = cell_ID_pos['Phenotypes']

        pairs = draw_tysserand_network(coords, clustering, patient, type=type, panel=panel, method=method, min_neighbors=min_neighbors)
        del coords, clustering
        if 'cells' in locals():
            del cells
        if 'cells_df' in locals():
            del cells_df
        gc.collect()

        edges = pd.DataFrame(data=pairs, columns=['source', 'target'])
        if type == 'IMC':
            edges.to_parquet(Path(f"OUTPUT_DATA/{type}_networks_sample") / f'edges_patient-{patient}.parquet', index=False)
            cell_ID_pos.to_parquet(Path(f"OUTPUT_DATA/nodes/{type}_networks_sample") / f'nodes_patient-{patient}.parquet', index=False)
        if type == 'IF':
            edges.to_parquet(Path(f"OUTPUT_DATA/{type}{panel}_networks_sample") / f'edges_patient-{patient}.parquet', index=False)
            cell_ID_pos.to_parquet(Path(f"OUTPUT_DATA/nodes/{type}_{panel}_networks_sample") / f'nodes_patient-{patient}.parquet', index=False)
        del edges, pairs, cell_ID_pos
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

def tysserand_network(Cells, there_is_duplicata, type, 
                      markers=None , panel=None,
                      make_phenograph=False, k_neighbors = 30, primary_metrics_phenograh='minkowski', normalize = False, 
                      method='delaunay', min_neighbors=3, cpu=4):
    
    if type == 'IMC':  
        sample_name = 'ROI'
    else:
        sample_name = 'layer'

    if 'Phenotypes' not in Cells:
        Cells['Phenotypes'] = ''

    if sample_name in Cells.columns:
        unique_patient_samples = Cells[['patient',sample_name]].drop_duplicates()
        unique_list = list(unique_patient_samples.itertuples(index=False, name=None))
        cpu = verif_cpu(cpu, unique_list)
        args_list = [(patient_sample, sample_name, Cells, markers, 
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
        unique_patient_samples = Cells['patient'].drop_duplicates()
        unique_list = unique_patient_samples.tolist()
        cpu = verif_cpu(cpu, unique_list)
        args_list = [(patient, sample_name, Cells, markers, 
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

        files = glob.glob(f"./temp/{type}{define_panel(type, panel)}*.parquet")
        for file in files:
            tqdm.write(f'[PROCESS] Processing on {file} file')
            Cells = pd.read_parquet(file)
            if config_file['phenograph']:
                markers = pd.read_parquet("./temp/IMC_markers.parquet")
            else:
                markers = None

            tysserand_network(Cells, config_file["tysserand"][f'{type}_duplicata'], type, markers, panel,
                            config_file['phenograph'],
                            config_file['k_neighbors_phenograph'],
                            config_file['primary_metric_phenograph'],
                            config_file[f'{type}_normalization'],
                            config_file['tysserand']['method_tysserand'],
                            config_file['tysserand']['min_neighbors'], cpu=config_file['tysserand']['cpu'])
            del Cells, markers
            gc.collect()
        
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
                    process('IF', config_file['tysserand']['panel'])
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

