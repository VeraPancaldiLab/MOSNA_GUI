################################################# Import ###################################################
print("\n[PARSER CSV TO PANDAS]")

import yaml
import argparse
import numpy as np
import pandas as pd
import os
import glob
from pathlib import Path
import copy

#################### Main Function ####################
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

def get_encoding_map(kwargs):
    path = kwargs.get('path_encoding_patient')
    if path:
        df = pd.read_csv(Path(path))
        return dict(zip(df['Original_ID'], df['Encoded_ID']))
    return None

def load_and_process_files(**kwargs):
    base_path = kwargs['directory_path']
    panel = kwargs.get('panel')
    columns_to_drop = kwargs.get('columns_to_drop')
    path_encoding_patient = kwargs.get('path_encoding_patient')
    path_file_to_patient = kwargs.get('path_file_to_patient')

    if panel:
        path_data = str(Path(base_path) / panel / "*.csv")
    else:
        path_data = str(Path(base_path) / "*.csv")

    if path_encoding_patient:
        id_map = pd.read_csv(Path(path_encoding_patient))
        id_map = dict(zip(id_map['Original_ID'], id_map['Encoded_ID']))
    else:
        id_map = None

    if path_file_to_patient:
        file_map = pd.read_csv(Path(path_file_to_patient))
        file_map = dict(zip(file_map['file'], file_map['patient']))
    else:
        file_map = None

    files = {}
    for i, file in enumerate(glob.glob(path_data), 1):
        file_path = Path(file)
        if file_path.with_suffix('.parquet').exists():
            df = pd.read_parquet(file_path.with_suffix('.parquet'))
        else:
            df = pd.read_csv(file_path)
            df.to_parquet(file_path.with_suffix('.parquet'))

        if columns_to_drop:
            df.drop(columns=columns_to_drop, inplace=True)

        if file_map:
            patient_sample = file_map[file_path.name]
            parts = patient_sample.split('_')
            df['patient'] = parts[0]
            if len(parts) > 1:
                df['sample'] = parts[1]

        files[f'sample {i}'] = df

    return files

def get_column_slice(df, col_ref):
    """
    Retourne un DataFrame de colonnes selon :
    - str : nom de colonne
    - int : index unique
    - 'start:end' : plage de colonnes par indices
    """
    if isinstance(col_ref, str) and col_ref in df.columns:
        return df[[col_ref]]
    elif isinstance(col_ref, str) and ':' in col_ref:
        start, end = map(int, col_ref.split(':'))
        return df.iloc[:, start:end+1]
    elif isinstance(col_ref, int):
        return df.iloc[:, [col_ref]]
    else:
        raise ValueError(f"Format de 'layer_columns' non reconnu : {col_ref}")

def get_column_slices(df, index_string):
    """Gère les cas comme '4 7:9 15'"""
    if not isinstance(index_string, str):
        return get_column_slice(df, index_string)

    parts = index_string.split()
    slices = [get_column_slice(df, part) for part in parts]
    return pd.concat(slices, axis=1)

def concatenate_dataframes(files):
    # Vérifie la compatibilité avant concaténation
    base_cols = files["sample 1"].columns
    if not all(df.columns.equals(base_cols) for df in files.values()):
        raise ValueError("All files must have identical columns to concatenate.")
    return pd.concat(files.values(), ignore_index=True)

####### Function to extract the 3 pandas ########

def extract_sample_info(df, type=None,**kwargs):
    sample_info = pd.DataFrame()
    cell_id_columns = kwargs['cell_id_columns']
    sample_info['CellID'] = df.iloc[:, cell_id_columns]
    patient_column = kwargs['patient_columns']
    sample_column = kwargs['layer_columns']
    # Si colonne "patient" explicitement fournie, on l'utilise telle quelle
    encoding_map = get_encoding_map(kwargs)

    if patient_column and patient_column in df.columns:
        sample_info['patient'] = df[patient_column]
    else:
        sample_info['patient'] = df['patient'] if 'patient' in df.columns else None
    if encoding_map:
        sample_info['patient'] = sample_info['patient'].map(encoding_map)
        
    # Gérer la colonne "sample" si elle est présente
    if sample_column and sample_column in df.columns:
        sample_info['sample'] = df[sample_column]
    elif 'sample' in df.columns:
        sample_info['sample'] = df['sample']
    else:
        sample_info['sample'] = None

    # Si patient == sample => tout est fusionné, ne garder que "sample"
    if sample_info['patient'].equals(sample_info['sample']):
        sample_info.drop(columns='patient', inplace=True)
        sample_info.rename(columns={'sample': 'sample'}, inplace=True)
    else:
        sample_info.rename(columns={'sample': define_sample_name(type)}, inplace=True)

    return sample_info

def extract_spatial_info(df, **kwargs):
    spatial_columns = kwargs['spatial_columns']
    cell_id_columns = kwargs['cell_id_columns']
    layer_columns = kwargs.get('layer_columns')
    type = kwargs.get('type')
    encoding_map = get_encoding_map(kwargs)

    spatial_info = pd.DataFrame()
    spatial_info[df.columns[cell_id_columns]] = df.iloc[:, cell_id_columns]

    spatial_cols = get_column_slices(df, spatial_columns)

    if 'sample' in df.columns:
        spatial_info = pd.concat([spatial_info, df[['patient', 'sample']], spatial_cols], axis=1)
        spatial_info.rename(columns={'sample': define_sample_name(type)}, inplace=True)
    elif layer_columns is not None:
        layer_data = get_column_slice(df, layer_columns)
        spatial_info = pd.concat([spatial_info, df['patient'], layer_data, spatial_cols], axis=1)
        spatial_info.rename(columns={layer_columns: define_sample_name(type)}, inplace=True)
    else:
        spatial_info = pd.concat([spatial_info, df['patient'], spatial_cols], axis=1)

    if encoding_map:
        spatial_info['patient'] = spatial_info['patient'].map(encoding_map)

    return spatial_info

def extract_markers(df, **kwargs):
    marker_columns = kwargs['marker_columns']
    cell_id_columns = kwargs['cell_id_columns']

    markers = pd.DataFrame()
    markers[df.columns[cell_id_columns]] = df.iloc[:, cell_id_columns]
    marker_data = get_column_slices(df, marker_columns)
    return pd.concat([markers, marker_data], axis=1)

def import_data(**kwargs):

    dataframes = load_and_process_files(**kwargs)

    # 2. Fusion si possible
    combined_df = concatenate_dataframes(dataframes)
    # 3. Extraction des trois tables
    markers_df = extract_markers(combined_df, **kwargs)
    sample_df = extract_sample_info(combined_df, **kwargs)
    spatial_df = extract_spatial_info(combined_df, **kwargs)

    return markers_df, sample_df, spatial_df

######################################## Main ########################################

def main():
    config_path = get_arguments()
    config_file = get_config(config_path)

    if config_file['IMC_import']['present_in']:
        print("\t[TASK] Import IMC data\t\t\t\t", end="")
        IMC_params = config_file['IMC_import'].copy()
        IMC_params.update({'layer_name': 'ROI', 'type': 'IMC'})

        IMC_markers, IMC_sample_cell, IMC_cell_pos = import_data(**IMC_params)
        print("DONE")

    if config_file['IF_import']['present_in']:
        print("\t[TASK] Import IF data\t\t\t\t", end="")
        IF_params = config_file['IF_import'].copy()
        IF_params.update({'layer_name': 'layer', 'type': 'IF'})

        IF_markers, IF_sample_cell, IF_cell_pos = import_data(**IF_params)
        print("DONE")
        

    if config_file['save_file']:
        print("\t[TASK] Saving pandas in parquet\t\t\t",end='')
        if config_file['IMC_import']['present_in']:
            IMC_cell_pos.to_parquet(Path('./output_data') / "IMC_cell_pos.parquet")
            IMC_markers.to_parquet(Path('./output_data') / "IMC_markers.parquet")
            IMC_sample_cell.to_parquet(Path('./output_data') / "IMC_sample_cell.parquet")
            IMC_markers = IMC_markers.drop('CellID', axis=1)
            IMC_markers.columns.to_series().to_csv(Path('./output_data') / "description/IMC_markers.csv",
                                                   index=False,
                                                   header=False)
            IMC_sample_cell = IMC_sample_cell.drop('CellID', axis=1).drop_duplicates()
            IMC_sample_cell.to_csv(Path('./output_data') / "description/IMC_file_description.csv",
                                  index=False,
                                  header=False)
            
        if config_file['IF_import']['present_in']:
            IF_cell_pos.to_parquet(Path('./output_data') / f"IF_{config_file['IF_import']['panel']}_cell_pos.parquet")
            IF_markers.to_parquet(Path('./output_data') / f"IF_{config_file['IF_import']['panel']}_markers.parquet")
            IF_sample_cell.to_parquet(Path('./output_data') / f"IF_{config_file['IF_import']['panel']}_sample_cell.parquet")
            IF_markers = IF_markers.drop('CellID', axis=1)
            IF_markers.columns.to_series().to_csv(Path('./output_data') / f"description/IF_{config_file['IF_import']['panel']}_markers.csv",
                                                  index=False,
                                                  header=False)
            IF_sample_cell = IF_sample_cell.drop('CellID', axis=1).drop_duplicates()
            IF_sample_cell.to_csv(Path('./output_data') / f"description/IF_{config_file['IF_import']['panel']}_file_description.csv",
                                  index=False,
                                  header=False)
        print('DONE')

if __name__ == "__main__":
    main()