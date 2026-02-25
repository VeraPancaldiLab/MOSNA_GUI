import pandas as pd
from pathlib import Path
from tqdm import tqdm

from package.utils.read_config import get_config, get_arguments
from package.utils.assert_params import assert_params
from package.core.assortativity.prepare_network_for_assort import prepare_network_for_assort
from package.utils.emit_qt_progress import emit_qt_info

from mosna import mosna

def main():
    analyse = "Assortativity"

    config_path, working_dir = get_arguments()
    config = get_config(config_path)[analyse]
    working_dir = Path(working_dir)

    assert_params(analyse, config)
    
    temp_folder = working_dir / "temp/net_dir_mosna"
    saving_folder = working_dir / f"Output/{analyse}"
    temp_folder.mkdir(parents=True, exist_ok=True)
    saving_folder.mkdir(parents=True, exist_ok=True)

    Pheno_col = config["Phenotype column"]
    id_level_1 = config["Patient column name"]
    id_level_2 = config["Sample column name"]
    nodes_index = config["Index"]

    if config['Network directory'] == 'Default':
        net_dir = temp_folder
        extension = 'parquet'
    else:
        net_dir = Path(working_dir).expanduser().resolve() / Path(config['Network directory']).expanduser()
        extension = config["Extension"]

    attributes_col = prepare_network_for_assort(net_dir, temp_folder, Pheno_col, id_level_1, id_level_2, extension, nodes_index)

    emit_qt_info(f"[PROCESS] Compute Assortativity")
    net_stat = mosna.groups_assort_mixmat(temp_folder, 
                                          attributes_col, 
                                          make_onehot=False, 
                                          id_level_1=id_level_1,
                                          id_level_2=id_level_2, 
                                          extension=extension,
    )
    net_stat.to_csv(saving_folder / "net_stat.csv", index="id")
    tqdm.write(f"[INFO] Assortativity table saved in {saving_folder}")
    emit_qt_info(f"[INFO] Assortativity table saved in {saving_folder}")

if __name__ == '__main__':
    main()