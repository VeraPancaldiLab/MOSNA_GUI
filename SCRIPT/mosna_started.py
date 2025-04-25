import warnings
from sklearn.exceptions import ConvergenceWarning, FitFailedWarning
warnings.simplefilter('ignore', FitFailedWarning)
warnings.simplefilter('ignore', ConvergenceWarning)
warnings.simplefilter('ignore', FutureWarning)
warnings.simplefilter('ignore', DeprecationWarning)
warnings.simplefilter('ignore', UserWarning)
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import argparse
import yaml
from time import time
import warnings
import joblib
from pathlib import Path
from time import time
from tqdm import tqdm
import copy
import matplotlib as mpl
import napari
import colorcet as cc
import composition_stats as cs
from sklearn.impute import KNNImputer
from lifelines import KaplanMeierFitter, CoxPHFitter

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

def nodes_aggregate(nodes_dir, marker_cols, sample=None):
    if sample is not None:
        nodes_dir = mosna.transform_nodes(
            nodes_dir=nodes_dir,
            id_level_1='patient',
            id_level_2=sample, 
            use_cols=marker_cols,
            method='clr',
            save_dir='auto',
        )
    else:
        nodes_dir = mosna.transform_nodes(
            nodes_dir=nodes_dir,
            id_level_1='patient',
            use_cols=marker_cols,
            method='clr',
            save_dir='auto',
        )


def main():
    config_path = get_arguments()
    config_file = get_config(config_path)
    IF_markers = pd.read_csv('../output_data/description/IF_markers.csv', header=None)[0].tolist()
    IMC_markers = pd.read_csv('../output_data/description/IMC_markers.csv', header=None)[0].tolist()
    print(IF_markers,IMC_markers)
    nodes_aggregate("../output_data/nodes/IF", IF_markers, config_file["IF_import"]["if_sample_take_an_other_name"])
    nodes_aggregate("../output_data/nodes/IMC", IMC_markers, config_file["IMC_import"]["if_sample_take_an_other_name"])

    
if __name__ == "__main__":
    main()