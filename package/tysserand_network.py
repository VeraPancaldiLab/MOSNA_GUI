import numpy as np
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from tqdm.contrib.concurrent import process_map

from package.utils.read_config import get_config, get_arguments
from package.utils.verif_cpu import verif_cpu
from package.core.tysserand.draw_per_sample import draw_per_sample
from package.utils.assert_params import assert_params
from package.utils.find_sample import find_sample
from package.core.tysserand.assert_file_for_tysserand import assert_file_for_tysserand

def worker_draw(args):
    return draw_per_sample(*args)

def main():
    analyse = "Tysserand"

    config_path, working_dir = get_arguments()
    config = get_config(config_path)[analyse]
    working_dir = Path(working_dir)

    assert_params(analyse, config)
    tqdm.write('[INFO] Parameters are read correctly')

    temp_folder = working_dir / "temp/net_dir_mosna"
    saving_folder = working_dir / f"Output/{analyse}_Network"
    temp_folder.mkdir(parents=True, exist_ok=True)
    saving_folder.mkdir(parents=True, exist_ok=True)

    net_dir = Path(working_dir).expanduser().resolve() / Path(config['Nodes directory']).expanduser()
    net_dir_list = find_sample(net_dir, config['Extension'], config["Patient column name"], config["Sample column name"])

    cpu_max = verif_cpu(config['CPU'], len(net_dir_list))
    args_list = [(
            patient_sample,
            config["X coordinates column"],
            config["Y coordinates column"],
            config["Phenotype column"],
            config["Edges method"],
            config['Min neighbors'],
            saving_folder,
            temp_folder,
            config["Patient column name"],
            config["Sample column name"],
            config['Extension']
            )
            for patient_sample in net_dir_list]
    
    for file in tqdm(net_dir_list, desc="[PROCESS] Verification of all file"):
        assert_file_for_tysserand(file, config, config['Extension'])
    tqdm.write("[INFO] Files are well builded\n")

    process_map(
        worker_draw,
        args_list,
        max_workers=cpu_max,
        desc=" └─ [MULTI PROCESS] Processing file",
        chunksize=1
    )

if __name__ == "__main__":
    main()