import pandas as pd
import yaml, os, argparse
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from tqdm import tqdm
import gc

def get_arguments():

    parser = argparse.ArgumentParser(description = "Draw tysserand for IMC / IF")
    parser.add_argument('--file', type = str, required=True, help = "config file")
    args = parser.parse_args()

    return args.file

def get_config(config_path):
        
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config

def import_data(dir):
    IMC_pos = pd.read_parquet(Path(dir) / "IMC_cell_pos.parquet")
    IF_pos = pd.read_parquet(Path(dir) / "IMC_cell_pos.parquet")
    IMC_sample_cell = pd.read_parquet(Path(dir) / "IMC_sample_cell.parquet")
    IF_sample_cell = pd.read_parquet(Path(dir) / "IF_sample_cell.parquet")
    return IMC_pos, IF_pos, IMC_sample_cell, IF_sample_cell

def filter_by_patient(filtre, data_pos, data_sample_cell, there_is_duplicata):
    if there_is_duplicata:
        cells_df = data_sample_cell.loc[filtre, ['CellID']]
        cell_ID_pos = cells_df.merge(data_pos.drop_duplicates(subset='CellID'), on='CellID', how='left')
    else:
        cells = data_sample_cell.loc[filtre, 'CellID'].drop_duplicates()
        cell_ID_pos = data_pos.loc[filtre, ['CellID','X_position','Y_position']]
    return cell_ID_pos

def cell_encounter(IMC_pos, IF_pos, r_max=10, nb_cell_max=7, sigma_x=10, sigma_y=15, amplitude=1, patient='Unknown'):
    result = []

    for idx_imc, imc_row in tqdm(IMC_pos.iterrows(), total=len(IMC_pos), desc=f" └─ Processing IMC cells for patient {patient}", position=1):
        x0, y0 = imc_row['X_position'], imc_row['Y_position']

        # Calculate all disntance between x0,x0 et les IF_pos
        dx = IF_pos['X_position'] - x0
        dy = IF_pos['Y_position'] - y0
        distances = np.sqrt(dx**2 + dy**2)

        # Keep only distances which are in the rad
        mask = distances <= r_max
        IF_near = IF_pos[mask]

        # ajust rad
        distances_series = pd.Series(distances, index=IF_pos.index)
        sorted_distances = distances_series[mask].sort_values(ascending=True)
        smallest_7_indices = sorted_distances.head(nb_cell_max).index
        IF_near = IF_pos.loc[smallest_7_indices]

        for idx_if, if_row in IF_near.iterrows():
            xi, yi = if_row['X_position'], if_row['Y_position']
            # Poids selon la gaussienne 2D (version point à point)
            weight = amplitude * np.exp(-(((xi - x0) ** 2) / (2 * sigma_x ** 2) + ((yi - y0) ** 2) / (2 * sigma_y ** 2)))
            result.append({'IMC_cell_ID': imc_row['CellID'],
                            'IF_cell_ID': if_row['CellID'],
                            'weight': weight,
                            'IF_X': xi,
                            'IF_Y': yi,
                            'IMC_X': x0,
                            'IMC_Y': y0})
            
    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection='3d')

    step = 1
    x = np.arange(x0 - r_max, x0 + r_max + step, step)
    y = np.arange(y0 - r_max, y0 + r_max + step, step)
    X, Y = np.meshgrid(x, y)

    Z = amplitude * np.exp(-(((X - x0) ** 2) / (2 * sigma_x ** 2) + ((Y - y0) ** 2) / (2 * sigma_y ** 2)))
    distance = np.sqrt((X - x0)**2 + (Y - y0)**2)
    Z[distance > r_max] = 0

    ax.plot_surface(X, Y, Z, cmap='viridis', alpha=0.7, edgecolor='none')

    zi = amplitude * np.exp(-(((IF_near['X_position'] - x0) ** 2) / (2 * sigma_x ** 2) +
                                  ((IF_near['Y_position'] - y0) ** 2) / (2 * sigma_y ** 2)))
    ax.scatter(IF_near['X_position'], IF_near['Y_position'], zi, color='red', label='Points IF', s=50)

    ax.scatter([x0], [y0], [amplitude], color='green', s=100, label='Point IMC')

    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Valeur de la gaussienne')
    ax.set_title('Surface Gaussienne autour du dernier point IMC')
    ax.legend()
    plt.tight_layout()
    plt.show()
    return result

def main():
    config_path = get_arguments()
    config_file = get_config(config_path)
    IMC_pos, IF_pos, IMC_sample_cell, IF_sample_cell = import_data(config_file['standard']['output_dir'])
    if config_file['IMC_import']['re_index']:
        IMC_pos['CellID'] = IMC_pos.index
        IMC_sample_cell['CellID'] = IMC_sample_cell.index
    if config_file['IF_import']['re_index']:
        IF_pos['CellID'] = IF_pos.index
        IF_sample_cell['CellID'] = IF_sample_cell.index
    unique_patient_samples = IF_sample_cell['patient'].drop_duplicates()
    unique_list = unique_patient_samples.tolist()

    if config_file['cell_encounter']['encoded_patient_to_drop'] is not None:
        unique_list = list(set(unique_list) - set(config_file['cell_encounter']['encoded_patient_to_drop']))

    if config_file['cell_encounter']['encoded_patient_wanted'] is not None:
        unique_list = config_file['cell_encounter']['encoded_patient_wanted']

    for patient in tqdm(unique_list, total=len(unique_list), desc="Processing Cell Encounter", position=0):
        filtre = IF_sample_cell['patient'] == patient

        IMC_pos = filter_by_patient(filtre, IMC_pos, IMC_sample_cell, config_file["IMC_import"]['there_is_duplicata'])
        IF_pos = filter_by_patient(filtre, IF_pos, IF_sample_cell, config_file["IF_import"]['there_is_duplicata'])
        tab = cell_encounter(IMC_pos, IF_pos, r_max=10, nb_cell_max=config_file['cell_encounter']['nb_cell_max_per_gaussian'], patient=patient)
        tab = pd.DataFrame(tab)
        tab.to_parquet(Path(f'cell_encounter_data/cell_encounter_for_patient_{patient}.parquet'))
        del tab
        gc.collect()
    
if __name__ == "__main__":
    main()