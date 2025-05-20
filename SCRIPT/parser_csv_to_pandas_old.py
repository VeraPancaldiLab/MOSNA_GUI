################################################# Import ###################################################
print("\n############### Welcome in parser CSV to pandas ###############")

import yaml
import argparse
import numpy as np
import pandas as pd
import os
import glob
from pathlib import Path
import copy


################################################# Main Function ############################################

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

def import_data(path_data, marker_columns, spatial_columns, cell_id_columns, 
                path_encoding_patient = None, path_file_to_patient = None, columns_to_drop = None, 
                layer_columns=None, layer_name=None, type=None):
    
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

    if concatanable:
        IMC_markers=pd.DataFrame()
        for file in files.values():
            IMC_markers = pd.concat([IMC_markers, file], ignore_index=True)
    
    ##### BUILD PANDAS DATAFRAME THANKS TO COLUMNS INDICES #####

    ### sample information

    IMC_sample_cell = pd.DataFrame({})
    IMC_sample_cell[IMC_markers.columns[cell_id_columns]] = IMC_markers.iloc[:, cell_id_columns]
    if 'sample' not in IMC_markers.columns:
        IMC_sample_cell = pd.concat([IMC_sample_cell,IMC_markers['patient']],axis=1)
    else:
        IMC_sample_cell = pd.concat([IMC_sample_cell,IMC_markers[['patient','sample']]],axis=1)
        IMC_sample_cell.rename(columns={'sample':define_sample_name(type)}, inplace=True)

    if layer_columns is not None:
        if ':' in str(layer_columns):
            ind_min_max = str(layer_columns).split(':')
            ind_columns = [i for i in range(int(ind_min_max[0]), int(ind_min_max[1]+1))]
            IMC_sample_cell[layer_name] = IMC_markers.iloc[:, ind_columns]
        else:
            IMC_sample_cell[layer_name] = IMC_markers.iloc[:, layer_columns]
        

    if path_encoding_patient is not None:
        IMC_sample_cell['patient'] = IMC_sample_cell['patient'].map(ID_patient_to_alphabet)
    
    ### spatial information
        
    temp = pd.DataFrame({})
    temp[IMC_markers.columns[cell_id_columns]] = IMC_markers.iloc[:, cell_id_columns]

    if ' ' in spatial_columns:
        spatial_columns = spatial_columns.split(' ')
        for column in spatial_columns:
            if ':' in column:
                ind_min_max = column.split(':')
                if 'sample' in IMC_markers.columns:
                    temp = pd.concat([temp,IMC_markers[['patient','sample']],IMC_markers.iloc[:, int(ind_min_max[0]):int(ind_min_max[1])+1]], axis=1)
                    temp.rename(columns={'sample':define_sample_name(type)}, inplace=True)
                elif layer_columns is not None:
                    current_layer_name = IMC_markers.columns[int(layer_columns)]
                    temp = pd.concat([temp,IMC_markers['patient'],IMC_markers.iloc[:, int(layer_columns)],IMC_markers.iloc[:, int(ind_min_max[0]):int(ind_min_max[1])+1]], axis=1)
                    temp.rename(columns={current_layer_name:define_sample_name(type)}, inplace=True)
                else:
                    temp = pd.concat([temp,IMC_markers['patient'],IMC_markers.iloc[:, int(ind_min_max[0]):int(ind_min_max[1])+1]], axis=1)
            else:
                if 'sample' in IMC_markers.columns:
                    temp = pd.concat([temp,IMC_markers[['patient','sample']],IMC_markers.iloc[:, [int(column)]]], axis=1)
                    temp.rename(columns={'sample':define_sample_name(type)}, inplace=True)
                elif layer_columns is not None:
                    current_layer_name = IMC_markers.columns[int(layer_columns)]
                    temp = pd.concat([temp,IMC_markers['patient'],IMC_markers.iloc[:, int(layer_columns)],IMC_markers.iloc[:, [int(column)]]], axis=1)
                    temp.rename(columns={current_layer_name:define_sample_name(type)}, inplace=True)
                else:
                    temp = pd.concat([temp,IMC_markers['patient'],IMC_markers.iloc[:,[int(column)]]], axis=1)


        IMC_cell_pos = temp
    else:
        if ':' in spatial_columns:
            ind_min_max = spatial_columns.split(':')
            if 'sample' in IMC_markers.columns:
                temp = pd.concat([temp,IMC_markers[['patient','sample']],IMC_markers.iloc[:, int(ind_min_max[0]):int(ind_min_max[1])+1]], axis=1)
                temp.rename(columns={'sample':define_sample_name(type)}, inplace=True)
            elif layer_columns is not None:
                current_layer_name = IMC_markers.columns[int(layer_columns)]
                temp = pd.concat([temp,IMC_markers['patient'],IMC_markers.iloc[:, int(layer_columns)],IMC_markers.iloc[:, int(ind_min_max[0]):int(ind_min_max[1])+1]], axis=1)
                temp.rename(columns={current_layer_name:define_sample_name(type)}, inplace=True)
            else:
                temp = pd.concat([temp,IMC_markers['patient'],IMC_markers.iloc[:, int(ind_min_max[0]):int(ind_min_max[1])+1]], axis=1)

        else:
            if 'sample' in IMC_markers.columns:
                temp = pd.concat([temp,IMC_markers[['patient','sample']],IMC_markers.iloc[:, [int(spatial_columns)]]], axis=1)
                temp.rename(columns={'sample':define_sample_name(type)}, inplace=True)
            elif layer_columns is not None:
                current_layer_name = IMC_markers.columns[int(layer_columns)]
                temp = pd.concat([temp,IMC_markers['patient'],IMC_markers.iloc[:, int(layer_columns)],IMC_markers.iloc[:, [int(spatial_columns)]]], axis=1)
                temp.rename(columns={current_layer_name:define_sample_name(type)}, inplace=True)
            else:
                temp = pd.concat([temp,IMC_markers['patient'],IMC_markers.iloc[:,[int(spatial_columns)]]], axis=1)

        IMC_cell_pos = temp

    if path_encoding_patient is not None:
        IMC_cell_pos['patient'] = IMC_cell_pos['patient'].map(ID_patient_to_alphabet)

    ### markers

    temp = pd.DataFrame({})
    temp[IMC_markers.columns[cell_id_columns]]= IMC_markers.iloc[:, cell_id_columns]
    if ' ' in marker_columns:
        marker_columns = marker_columns.split(' ')
        for column in marker_columns:
            if ':' in column:
                ind_min_max = column.split(':')
                temp = pd.concat([temp,IMC_markers.iloc[:, int(ind_min_max[0]):int(ind_min_max[1])+1]], axis=1)
            else:
                temp = pd.concat([temp, IMC_markers.iloc[:, column]])
        IMC_markers = temp
    else:
        if ':' in marker_columns:
            ind_min_max = marker_columns.split(':')
            temp = pd.concat([temp, IMC_markers.iloc[:, int(ind_min_max[0]):int(ind_min_max[1])+1]], axis=1)
        else:
            temp = pd.concat([temp, IMC_markers.iloc[:, marker_columns]], axis=1)
        IMC_markers = temp
    
    return IMC_markers, IMC_sample_cell, IMC_cell_pos

################################################# Main #####################################################

def main():
    config_path = get_arguments()
    config_file = get_config(config_path)

    if config_file['IMC_import']['present_in']:
        print("Import IMC data\t\t\t\t",end="")
        IMC_markers, IMC_sample_cell, IMC_cell_pos = import_data(config_file['IMC_import']['directory_path'],
                                                            marker_columns=config_file['IMC_import']['marker_columns'],
                                                            spatial_columns=config_file['IMC_import']['spatial_columns'],
                                                            cell_id_columns=config_file['IMC_import']['cell_id_columns'],
                                                            layer_columns=config_file['IMC_import']['layer_columns'],
                                                            path_encoding_patient=config_file['IMC_import']['path_encoding_patient'],
                                                            path_file_to_patient=config_file['IMC_import']['path_file_to_patient'],
                                                            columns_to_drop=config_file['IMC_import']['columns_to_drop'],
                                                            layer_name = 'ROI', type='IMC')
        print("DONE")
    if config_file['IF_import']['present_in']:
        print("Import IF data\t\t\t\t",end="")
        IF_markers, IF_sample_cell, IF_cell_pos = import_data(config_file['IF_import']['directory_path'],
                                                        marker_columns=config_file['IF_import']['marker_columns'],
                                                        spatial_columns=config_file['IF_import']['spatial_columns'],
                                                        cell_id_columns=config_file['IF_import']['cell_id_columns'],
                                                        layer_columns=config_file['IF_import']['layer_columns'],
                                                        path_encoding_patient=config_file['IF_import']['path_encoding_patient'],
                                                        path_file_to_patient=config_file['IF_import']['path_file_to_patient'],
                                                        columns_to_drop=config_file['IF_import']['columns_to_drop'],
                                                        layer_name = 'layer', type='IF')
        
        print("DONE")
    if config_file['save_file']:
        print("Saving pandas in parquet\t\t",end='')
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
    print('\n')