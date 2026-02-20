import pandas as pd
from pathlib import Path

from .utils.read_config import get_config, get_arguments
from .core.prepare_network_for_assort import prepare_network_for_assort
from mosna import mosna

def main():

    config_path, working_dir = get_arguments()
    config = get_config(config_path)['Assortativity']
    working_dir = Path(working_dir)

    temp_folder = working_dir / "temp/net_dir_mosna"
    saving_folder = working_dir / "Output/Assortativity"

    temp_folder.mkdir(parents=True, exist_ok=True)
    saving_folder.mkdir(parents=True, exist_ok=True)

    net_dir = Path(working_dir).expanduser().resolve() / Path(config['Network directory'])

    Pheno_col = config["Phenotype column"]
    id_level_1 = config["Patient_ID"]
    id_level_2 = config["Sample_ID"]
    extension = config["Extension"]
    nodes_index = config["Index"]

    attributes_col = prepare_network_for_assort(net_dir, Pheno_col, id_level_1, id_level_2, extension, nodes_index)

    net_stat = mosna.groups_assort_mixmat(temp_folder, 
                                          attributes_col, 
                                          make_onehot=False, 
                                          id_level_1=id_level_1,
                                          id_level_2=id_level_2, 
                                          extension=extension
    )
    net_stat.to_csv(saving_folder / "net_stat.csv", index=False)

if __name__ == '__main__':
    main()