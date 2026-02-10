import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"
import warnings
import gc
from time import time
from sklearn.exceptions import ConvergenceWarning, FitFailedWarning
warnings.simplefilter('ignore', FitFailedWarning)
warnings.simplefilter('ignore', ConvergenceWarning)
warnings.simplefilter('ignore', FutureWarning)
warnings.simplefilter('ignore', DeprecationWarning)
warnings.simplefilter('ignore', UserWarning)
warnings.simplefilter('ignore', RuntimeWarning)
import pandas as pd  
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
import yaml
from time import time
import warnings
from pathlib import Path
from time import time
from tqdm import tqdm

import matplotlib as mpl
import matplotlib as mpl
import matplotlib.gridspec as gridspec
from matplotlib.patches import Patch

from mosna import mosna
from package.utils import verif_folder, define_panel, get_arguments, get_config, define_sample_name, replace_sample_name

mpl.rcParams["figure.facecolor"] = 'white'
mpl.rcParams["axes.facecolor"] = 'white'
mpl.rcParams["savefig.facecolor"] = 'white'

########################################## Function ##########################################  

def nodes_transfo(nodes_dir, marker_cols, sample_name=None, sample_present=True):
    if sample_name is not None:
        sample_name = replace_sample_name(sample_name)
        nodes_dir = mosna.transform_nodes(
            nodes_dir=nodes_dir,
            id_level_1='patient',
            id_level_2=sample_name, 
            use_cols=marker_cols,
            method='clr',
            save_dir='auto',
        )
    elif sample_present:
        nodes_dir = mosna.transform_nodes(
            nodes_dir=nodes_dir,
            id_level_1='patient',
            id_level_2='sample', 
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

def mix_mat_assortativity(net_dir, pheno_col, n_shuffle = 50, type=None):

    sample_name = define_sample_name(type)

    net_stats = mosna.groups_assort_mixmat(
        net_dir=net_dir, 
        attributes_col=pheno_col,
        make_onehot=True,
        id_level_1='patient',
        id_level_2=replace_sample_name(sample_name), 
        extension='parquet',
        n_shuffle=n_shuffle,
        parallel_groups='max',  # or False
        memory_limit='max',
        save_intermediate_results=False,
        verbose=0)
    net_stats.index = net_stats['id']
    net_stats.drop(columns=['id'], inplace=True)
    return net_stats

def plot_mix_mat(save_dir, net_stats, sample_id, type, panel):
    z_cols = [x for x in net_stats.columns if x.endswith('Z') and not x.startswith('assort')]

    mixmat_z = mosna.series_to_mixmat(net_stats.loc[sample_id, z_cols], discard=' Z').astype(float)
    mixmat_z.to_parquet(f"OUTPUT_DATA/synthetic_network_generation/mixmat_IF_IMC/{type}{panel}_{sample_id}_mixmat.parquet")
    assort_z = net_stats.loc[sample_id, "assort Z"]
    
    sns.set_context("notebook")
    figsize = (9, 8)
    title = "Z-scored assortativity for {} on panel{} for {} by cell types: {:.2f}".format(type,panel,sample_id,assort_z)
    f, ax = plt.subplots(figsize=figsize)
    sns.heatmap(mixmat_z, center=0, cmap="vlag", annot=False, linewidths=.5, ax=ax)
    ax.set_title(title)
    plt.xticks(rotation=45, ha='right')
    plt.savefig(save_dir / f"assortativity_z-scored_{sample_id}", bbox_inches='tight', facecolor='white')
    return z_cols

def clean_net_stat(z_net_stats):
    z_net_stats_cleaned, _ = mosna.clean_data(
        z_net_stats, 
        method='mixed',
        thresh=0.8,
        verbose=0)
    return z_net_stats_cleaned

def correct_batch_effect(nodes_dir, marker_col, sample, save_dir):
    nodes_dir, nodes_corr = mosna.batch_correct_nodes(
        nodes_dir=nodes_dir,
        id_level_1 = 'patient',
        id_level_2 = sample, 
        extension ='parquet',
        data_index = None,
        use_cols = marker_col,
        add_sample_info = True,
        batch_key = 'patient',
        max_dimred= 100,
        return_dense = True,
        save_dir = save_dir,
        force_recompute = False,
        return_nodes = True,
        verbose = 0,
        )
    return nodes_dir, nodes_corr

def group_assort(net_stat, z_cols, save_dir, type, panel):

    z_net_stats = net_stat[z_cols].astype(float)
    z_net_stats = clean_net_stat(z_net_stats)
    z_mean = z_net_stats.mean()
    z_std = z_net_stats.std()

    mixmat_z_mean = mosna.series_to_mixmat(z_mean.loc[z_cols], discard=' Z').astype(float)
    mixmat_z_std = mosna.series_to_mixmat(z_std.loc[z_cols], discard=' Z').astype(float)

    mixmat_z_mean.to_parquet(f"./OUTPUT_DATA/synthetic_network_generation/mixmat_mean_{type}{panel}.parquet")
    mixmat_z_std.to_parquet(f"./OUTPUT_DATA/synthetic_network_generation/mixmat_std_{type}{panel}.parquet")

    data = []
    already_seen = set()
    for i in mixmat_z_mean.index:
        for j in mixmat_z_mean.columns:
            pair_key = tuple(sorted([i, j]))  
            if pair_key in already_seen:
                continue  
            already_seen.add(pair_key)
            data.append({
                'pair': f"{i} <=> {j}",
                'mean': mixmat_z_mean.loc[i, j],
                'std': mixmat_z_std.loc[i, j],
                'is_auto': i == j
            })
    df_plot = pd.DataFrame(data)
    df_plot["color"] = df_plot["is_auto"].map({True: "darkorange", False: "seagreen"})
    df_plot = df_plot.sort_values(by="mean")

    sns.set_context("notebook")

    def plotting(df_plot):
        fig = plt.figure(figsize=(20, 10))
        gs = gridspec.GridSpec(1, 2, width_ratios=[5, 3])
        ax_bar = fig.add_subplot(gs[1])
        ax_heat = fig.add_subplot(gs[0])
        if type == 'IF':
            title = f"mean Z-scored assortativity for {type} with {config_file['Assortativity']['panel']} panel dataset by cell types"
        if type == 'IMC':
            title = f"mean Z-scored assortativity for {type} dataset by cell types"
            
        # --- Assortativity matrix ---

        sns.heatmap(mixmat_z_mean, center=0, cmap="vlag", annot=False, linewidths=.5, ax=ax_heat)
        ax_heat.set_title("Z_scored assortativity")
        ax_heat.tick_params(axis='x', rotation=45)

        # --- BARPLOT of mean ± std ---

        ax_bar.barh(y=df_plot["pair"], width=df_plot["mean"], xerr=df_plot["std"],
                    capsize=4, color=df_plot["color"], edgecolor='black')
        legend_elements = [
            Patch(facecolor='darkorange', edgecolor='black', label='Auto-assortativity'),
            Patch(facecolor='seagreen', edgecolor='black', label='Hetero-assortativity')
        ]
        ax_bar.legend(handles=legend_elements, loc='lower right')
        ax_bar.set_title("Mean ± Std per Cell-Type Pair")
        ax_bar.set_ylabel("Z-scored Assortativity")
        ax_bar.tick_params(axis='x', rotation=45)

        # --- Plot subplot ---

        fig.suptitle(title)
        plt.tight_layout()
        plt.savefig(save_dir / f"assortativity_z-scored_{type}{panel}", bbox_inches='tight', facecolor='white')
        plt.close()

    if len(df_plot['pair']) <= 30:
        plotting(df_plot)
    else:
        if type == 'IF':
            title_hear = f"mean Z-scored assortativity for {type} with {config_file['Assortativity']['panel']} panel dataset by cell types"
            title_bar=f"Mean ± Std Assortativity per Cell-Type Pair for {type} with {config_file['Assortativity']['panel']} panel"
        if type == 'IMC':
            title_heat = f"mean Z-scored assortativity for {type} dataset by cell types"
            title_bar=f"Mean ± Std Assortativity per Cell-Type Pair for {type} dataset"
    
        # --- BARPLOT of mean ± std ---

        fig2_height = max(6, len(df_plot["pair"]) * 0.3)
        fig2 = plt.figure(figsize=(20, fig2_height))
        ax_bar = fig2.add_subplot(111)

        ax_bar.barh(
            y=df_plot["pair"],
            width=df_plot["mean"],
            xerr=df_plot["std"],
            capsize=4,
            color=df_plot["color"],
            edgecolor='black'
        )
        legend_elements = [
            Patch(facecolor='darkorange', edgecolor='black', label='Auto-assortativity'),
            Patch(facecolor='seagreen', edgecolor='black', label='Hetero-assortativity')
        ]
        ax_bar.legend(handles=legend_elements, loc='lower right')
        ax_bar.set_title(title_bar)
        ax_bar.set_xlabel("Z-scored Assortativity")
        ax_bar.tick_params(axis='x', rotation=45)

        plt.tight_layout()
        plt.savefig(save_dir / f"Mean_Std_Assortativity_z-scored_{type}{panel}", bbox_inches='tight', facecolor='white')
        plt.close(fig2)

        # --- Assortativity matrix ---

        df_plot["abs_mean"] = df_plot["mean"].abs()
        df_plot = df_plot.sort_values(by="abs_mean", ascending=False).head(30)
        df_plot = df_plot.sort_values(by="mean")
        plotting(df_plot)

########################################## MAIN #######################################

def main(IF, IMC, config_file):

    save_dir = Path("./OUTPUT_DATA/Assortativity")
    save_dir.mkdir(parents=True, exist_ok=True)
    Path("./OUTPUT_DATA/synthetic_network_generation/mixmat_IF_IMC").mkdir(parents=True, exist_ok=True)

    def process(type, config_file, panel=None):

        # === Compute Assortativity ===

        if not (save_dir / f"{type}{panel}_net_stat.parquet").exists():
            t = time()
            print(f"\t[INFO] Processing Assortativity for {type} data\t\t\t", end='')
            net_stat = mix_mat_assortativity(net_dir=f"./temp/{type}{define_panel(type, panel)}_networks_sample", 
                                                pheno_col="Phenotypes", 
                                                type=type)
            net_stat.to_parquet(save_dir / f"{type}{define_panel(type, panel)}_net_stat.parquet")
            print(f"DONE\n\t[INFO] Assortativity for {type} took {time()-t} s")
            del net_stat, t
            gc.collect()

        net_stat = pd.read_parquet(save_dir / f'{type}{define_panel(type, panel)}_net_stat.parquet')
        list_id = net_stat.index.to_list()
        save_dir_type = save_dir / f"figures/{type}{define_panel(type, panel)}"
        save_dir_type.mkdir(parents=True, exist_ok=True)
        
        # === Plot Assortativity ===

        for id in tqdm(list_id, desc=f"\t[PROCESS]  └─ Processing assortativity for {type}"):
            z_cols = plot_mix_mat(save_dir_type, clean_net_stat(net_stat), id, type, panel)
        
        z_net_stat = group_assort(net_stat, z_cols, save_dir, type, panel)
    
    try:
        if IMC: 
            if verif_folder(Path.cwd(),'IMC', "_networks_sample", define_panel('IMC')):
                process('IMC', config_file)
            else:
                raise ValueError("There is no IMC in your data or the Tysserand networks were not generated")
    except ValueError as e:
        print(f"\t[INFO] IMC error: {e}")

    try:
        if IF:
            if config_file['Assortativity']['panel'] == 'all':
                for panel in config_file['panel_list']:
                    if verif_folder(Path.cwd(),'IF', "_networks_sample", define_panel('IF', panel)):
                        process('IF', config_file, panel)
                    else:
                        raise ValueError("There is no IF in your data or the Tysserand networks were not generated")
            else:
                if verif_folder(Path.cwd(),'IF', define_panel('IF', "_networks_sample", config_file['Assortativity']['panel'])):
                    process('IF', config_file, config_file['Assortativity']['panel'])
                else:
                    raise ValueError("There is no IF in your data or the Tysserand networks were not generated")
    except ValueError as e:
        print(f"\t[INFO] IF error: {e}")

if __name__ == "__main__":
    print('\n\n[ASSORTATIVITY]')
    config_path = get_arguments()
    config_file = get_config(config_path)
    main(config_file['Assortativity']['IF_perform'],
                config_file['Assortativity']['IMC_perform'],
                config_file)