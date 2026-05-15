import pandas as pd
from pathlib import Path
from tqdm import tqdm

from package.utils.read_config import get_config, get_arguments
from package.utils.assert_params import assert_params
from package.utils.emit_qt_progress import emit_qt_info
from package.core.assortativity.assort_figures_abundance import assort_figures_abundance
from package.core.assortativity.assort_figures_heatmap import assort_figures_heatmap
from package.core.assortativity.assort_figures_mixing_matrix import assort_figures_mixing_matrix
from package.core.assortativity.assort_figures_mixing_matrix_without_diag import assort_figures_mixing_matrix_without_diag
from package.core.assortativity.assort_figures_mean_std_across_samples import assort_figures_mean_std_across_samples

from mosna import mosna

def main():
    analyse = "Assortativity"

    config_path, working_dir = get_arguments()
    config = get_config(config_path)[analyse]
    working_dir = Path(working_dir)

    assert_params(analyse, config)
    
    saving_folder = working_dir / f"{analyse}"
    saving_folder.mkdir(parents=True, exist_ok=True)

    Pheno_col = config["Phenotype column"]
    id_level_1 = config["Patient column name"]
    id_level_2 = config["Sample column name"]
    nodes_index = config["Index"]

    if config['Network directory'] == 'Default':
        net_dir = working_dir / Path(f'temp/net_dir_mosna')
        extension = 'parquet'
    else:
        net_dir = Path(working_dir).expanduser().resolve() / Path(config['Network directory']).expanduser()
        extension = config["Extension"]
        
    emit_qt_info(f"[PROCESS] Compute Assortativity")
    if config['Randomization diagnostic']:
        net_stat = mosna.groups_assort_mixmat(net_dir, 
                                          Pheno_col,
                                          make_onehot=True, 
                                          id_level_1=id_level_1,
                                          id_level_2=id_level_2, 
                                          extension=extension,
                                          n_shuffle=20
        )

    else:
        net_stat = mosna.groups_assort_mixmat(net_dir,
                                          Pheno_col,
                                          make_onehot=True, 
                                          id_level_1=id_level_1,
                                          id_level_2=id_level_2, 
                                          extension=extension,
                                          n_shuffle=config['Number of shuffle'],
        )
        net_stat = net_stat.set_index("id")
        net_stat.to_csv(saving_folder / "net_stat.csv", index=True)

        emit_qt_info(f"[INFO] Assortativity table saved in {saving_folder}")

        assort_figures_mixing_matrix(net_stat, saving_folder, is_sample=id_level_2)
        assort_figures_mixing_matrix_without_diag(net_stat, saving_folder, is_sample=id_level_2)
        assort_figures_heatmap(net_stat, saving_folder, True)
        assort_figures_heatmap(net_stat, saving_folder, False)
        assort_figures_abundance(net_stat, saving_folder)
        assort_figures_mean_std_across_samples(net_stat, saving_folder, True)
        assort_figures_mean_std_across_samples(net_stat, saving_folder, False)

if __name__ == '__main__':
    main()