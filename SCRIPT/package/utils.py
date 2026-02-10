import argparse
import os
import yaml
import tqdm
import multiprocessing
from pathlib import Path

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

def verif_file(cwd, type, suffix, panel=""):
    path = Path(cwd) / "temp" / f"{type}{panel}{suffix}"
    return path.is_file()

def verif_folder(cwd, type, suffix, panel=""):
    path = Path(cwd) / "temp" / f"{type}{panel}{suffix}"
    return path.is_dir()

def define_panel(type, panel=None):
    if type == 'IMC':
        panel = ''
    if type == 'IF':
        panel = '_' + panel
    return panel 

def sample_are_present_in_data(data, name):
    if name is None:
        name = 'sample'
    if name in data.columns:
        return True
    else:
        return False

def open_markers(file):
    with open(file, 'r') as f:
        markers = [line.strip() for line in f if line.strip()]
    return markers

def replace_sample_name(sample_name):
    return sample_name.replace('_', '-')

def verif_cpu(cpu, unique_list):
    if cpu > multiprocessing.cpu_count():
        cpu = min(multiprocessing.cpu_count(), len(unique_list))
        tqdm.write(f"\t[INFO] You've selected a higher number of cpu than your current available cpu : {multiprocessing.cpu_count()}")
    if cpu > len(unique_list):
        cpu = min(cpu, len(unique_list))
        tqdm.write(f"\t[INFO] You've selected a higher number of cpu than the number needed : {multiprocessing.cpu_count()}")
    tqdm.write(f"\t[INFO] you are currently using {cpu} cpu")
    return cpu