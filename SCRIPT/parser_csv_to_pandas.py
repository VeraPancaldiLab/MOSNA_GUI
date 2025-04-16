################################################# Import ###################################################
print("\n############### Welcome in parser CSV to pandas ###############")
print("\nImport Package\t\t\t\t",end="")
import yaml
import argparse
import warnings
import numpy as np
import pandas as pd
import os
import glob
from pathlib import Path
import copy
print("DONE")

################################################# Main Function ###################################################

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

def import_data(path_data, marker_columns, spatial_columns, cell_id_columns, path_encoding_patient = None, path_file_to_patient = None, columns_to_drop = None, other_columns = None, other_columns_name = None):
    objects_path = glob.glob(path_data)
    files=dict()

    if path_encoding_patient is not None:
        ID_patient_to_alphabet = pd.read_csv(Path(path_encoding_patient))
        ID_patient_to_alphabet = dict(zip(ID_patient_to_alphabet['Original_ID'], ID_patient_to_alphabet['Encoded_ID']))

    ##### GENERATE A FILES DICTIONNARY WITH ALL DATASET FOR EACH DATASET_INDICES, WE MAKE THAT TO CONCATENATE AFTER #####

    sample_number=1
    for file in objects_path:
        if path_file_to_patient is not None:
            file_to_patient = pd.read_csv(Path(path_file_to_patient))
            file_to_patient = dict(zip(file_to_patient['file'], file_to_patient['patient']))

        if Path(file).with_suffix('.parquet').exists():
            obj = pd.read_parquet(Path(file).with_suffix('.parquet'))
            if columns_to_drop is not None:
                obj.drop(columns=columns_to_drop, inplace=True)
            if path_file_to_patient is not None:
                if '_' in file_to_patient[Path(file).name]: 
                    name_file = file_to_patient[Path(file).name].split('_')
                    obj['patient'] = name_file[0]
                    obj['sample'] = name_file[1]
                else:
                    obj['patient'] = file_to_patient[Path(file).name]
            files.setdefault(f'sample {sample_number}', obj)
        else:
            obj = pd.read_csv(Path(file))
            obj.to_parquet(Path(file).with_suffix('.parquet'))
            if columns_to_drop is not None:
                obj.drop(columns=columns_to_drop, inplace=True)
            if path_file_to_patient is not None:
                if '_' in file_to_patient[Path(file).name]: 
                    name_file = file_to_patient[Path(file).name].split('_')
                    obj['patient'] = name_file[0]
                    obj['sample'] = name_file[1]
                else:
                    obj['patient'] = file_to_patient[Path(file).name]
            files.setdefault(f'sample {sample_number}', obj)
        
        sample_number+=1

    ##### CONCATENATION VERIFICATION AND PROCESS #####

    verif = files["sample 1"].columns
    concatanable = True

    for file in files.values():
        
        if file.columns.all() != verif.all():
            print("not concatanable files")
            concatanable = False

    nb_row=0
    nb_row_concat=0
    if concatanable:
        IMC_markers=pd.DataFrame()
        for file in files.values():
            nb_row+=file.shape[0]
            IMC_markers = pd.concat([IMC_markers, file], ignore_index=True)
        nb_row_concat=IMC_markers.shape[0]
    

    ##### BUILD PANDAS DATAFRAME THANKS TO COLUMNS INDICES #####

    ### sample information

    IMC_sample_cell = pd.DataFrame({})
    IMC_sample_cell['cell_ID'] = IMC_markers.iloc[:, cell_id_columns]
    if 'sample' not in IMC_markers.columns:
        IMC_sample_cell = pd.concat([IMC_sample_cell,IMC_markers['patient']],axis=1)
    else:
        IMC_sample_cell = pd.concat([IMC_sample_cell,IMC_markers[['patient','sample']]],axis=1)
    
    """
    if ':' in other_columns:
        ind_min_max = other_columns.split(':')
        IMC_sample_cell[other_columns_name] = IMC_markers.iloc[:, int(ind_min_max[0]):int(ind_min_max[1])]
    else:
        IMC_sample_cell[other_columns_name] = IMC_markers.iloc[:, other_columns]
    """

    if path_encoding_patient is not None:
        IMC_sample_cell['patient'] = IMC_sample_cell['patient'].map(ID_patient_to_alphabet)
    
    ### spatial information
        
    temp = pd.DataFrame({})
    temp['cell_ID'] = IMC_markers.iloc[:, cell_id_columns]
    if ' ' in spatial_columns:
        spatial_columns = spatial_columns.split(' ')
        for column in spatial_columns:
            if ':' in column:
                ind_min_max = column.split(':')
                temp = pd.concat([temp,IMC_markers.iloc[:, int(ind_min_max[0]):int(ind_min_max[1])]], axis=1)
            else:
                temp = pd.concat([temp,IMC_markers.iloc[:, [int(column)]]], axis=1)
        IMC_cell_pos = temp
    else:
        if ':' in spatial_columns:
            ind_min_max = spatial_columns.split(':')
            temp = pd.concat([temp,IMC_markers.iloc[:, int(ind_min_max[0]):int(ind_min_max[1])]], axis=1)
        else:
            temp = pd.concat([temp,IMC_markers.iloc[:, [int(spatial_columns)]]], axis=1)
        IMC_cell_pos = temp


    ### markers

    temp = pd.DataFrame({})
    temp['cell_ID']= IMC_markers.iloc[:, cell_id_columns]
    if ' ' in marker_columns:
        marker_columns = marker_columns.split(' ')
        for column in marker_columns:
            if ':' in column:
                ind_min_max = column.split(':')
                temp = pd.concat([temp,IMC_markers.iloc[:, int(ind_min_max[0]):int(ind_min_max[1])]], axis=1)
            else:
                temp = pd.concat([temp, IMC_markers.iloc[:, column]])
        IMC_markers = temp
    else:
        if ':' in marker_columns:
            ind_min_max = marker_columns.split(':')
            temp = pd.concat([temp, IMC_markers.iloc[:, int(ind_min_max[0]):int(ind_min_max[1])]], axis=1)
        else:
            temp = pd.concat([temp, IMC_markers.iloc[:, marker_columns]], axis=1)
        IMC_markers = temp
    
    return IMC_markers, IMC_sample_cell, IMC_cell_pos

def main():
    print('Import Config\t\t\t\t',end='')
    config_path = get_arguments()
    config_file = get_config(config_path)
    print("DONE")

    print("Import IMC data\t\t\t\t",end="")
    IMC_markers, IMC_sample_cell, IMC_cell_pos = import_data(config_file['IMC_import']['directory_path'],
                                                            marker_columns=config_file['IMC_import']['marker_columns'],
                                                            spatial_columns=config_file['IMC_import']['spatial_columns'],
                                                            cell_id_columns=config_file['IMC_import']['cell_id_columns'],
                                                            other_columns=config_file['IMC_import']['other_columns'],
                                                            path_encoding_patient=config_file['IMC_import']['path_encoding_patient'],
                                                            path_file_to_patient=config_file['IMC_import']['path_file_to_patient'],
                                                            columns_to_drop=config_file['IMC_import']['columns_to_drop']
                                                            )
    print("DONE")
    print("Import IF data\t\t\t\t",end="")
    IF_markers, IF_sample_cell, IF_cell_pos = import_data(config_file['IF_import']['directory_path'],
                                                        marker_columns=config_file['IF_import']['marker_columns'],
                                                        spatial_columns=config_file['IF_import']['spatial_columns'],
                                                        cell_id_columns=config_file['IF_import']['cell_id_columns'],
                                                        other_columns=config_file['IF_import']['other_columns'],
                                                        path_encoding_patient=config_file['IF_import']['path_encoding_patient'],
                                                        path_file_to_patient=config_file['IF_import']['path_file_to_patient'],
                                                        columns_to_drop=config_file['IF_import']['columns_to_drop']
                                                        )
    print("DONE")

    if config_file['standard']['saving']:
        print("Saving pandas in parquet\t\t",end='')
        IMC_cell_pos.to_parquet(Path(config_file['standard']['output_dir']) / "IMC_cell_pos.parquet")
        IMC_markers.to_parquet(Path(config_file['standard']['output_dir']) / "IMC_markers.parquet")
        IMC_sample_cell.to_parquet(Path(config_file['standard']['output_dir']) / "IMC_sample_cell.parquet")

        IF_cell_pos.to_parquet(Path(config_file['standard']['output_dir']) / "IF_cell_pos.parquet")
        IF_markers.to_parquet(Path(config_file['standard']['output_dir']) / "IF_markers.parquet")
        IF_sample_cell.to_parquet(Path(config_file['standard']['output_dir']) / "IF_sample_cell.parquet")
        print('DONE')

if __name__ == "__main__":
    main()
    print('\n')