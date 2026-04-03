import numpy as np
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ProcessPoolExecutor, as_completed

from package.utils.read_config import get_config, get_arguments
from package.utils.verif_cpu import verif_cpu
from package.core.tysserand.draw_per_sample import draw_per_sample
from package.utils.assert_params import assert_params
from package.utils.find_sample import find_sample
from package.core.tysserand.assert_file_for_tysserand import assert_file_for_tysserand
from package.utils.emit_qt_progress import emit_qt_progress, emit_qt_info
from package.core.tysserand.generate_cmap import generate_cmap

def worker_draw(args):
    return draw_per_sample(*args)

def main():
    analyse = "Tysserand"

    config_path, working_dir = get_arguments()
    config = get_config(config_path)[analyse]
    working_dir = Path(working_dir)

    assert_params(analyse, config)

    emit_qt_info('[INFO] Parameters are read correctly')

    temp_folder = working_dir / "temp/net_dir_mosna"
    saving_folder = working_dir / f"{analyse}_Network"
    temp_folder.mkdir(parents=True, exist_ok=True)
    saving_folder.mkdir(parents=True, exist_ok=True)

    net_dir = Path(working_dir).expanduser().resolve() / Path(config['Nodes directory']).expanduser()
    net_dir_list = find_sample(net_dir, config['Extension'], config["Patient column name"], config["Sample column name"])

    cpu_max = verif_cpu(config['CPU'], len(net_dir_list))
    c_map = generate_cmap(net_dir, config['Phenotype column'], config['Extension'], config["Patient column name"], config["Sample column name"])

    args_list = [(
            patient_sample,
            config["X coordinates column"],
            config["Y coordinates column"],
            config["Phenotype column"],
            c_map,
            config["Edges method"],
            config['Min neighbors'],
            saving_folder,
            temp_folder,
            config["Patient column name"],
            config["Sample column name"],
            config['Extension'],
            None
            )
            for patient_sample in net_dir_list]
    
    emit_qt_progress(0, len(net_dir_list), "[PROCESS] Verification of all file")
    for i, file in enumerate(tqdm(net_dir_list, desc="[PROCESS] Verification of all file")):
        assert_file_for_tysserand(file, config, config['Extension'])
        emit_qt_progress(i, len(net_dir_list), "[PROCESS] Verification of all file")
    
    emit_qt_info("[INFO] Files are well builded\n")

    emit_qt_progress(0, len(args_list), "[MULTI PROCESS] Processing file")
    
    results = [None] * len(args_list)
    total = len(args_list)
    finished = 0

    with ProcessPoolExecutor(max_workers=cpu_max) as executor:
        future_to_index = {
            executor.submit(worker_draw, args): (i, args[0])
            for i, args in enumerate(args_list)
        }

        for future in as_completed(future_to_index):
            index, patient_sample = future_to_index[future]
            results[index] = future.result()
            patient_sample = str(Path(patient_sample).stem[6:])

            finished += 1
            emit_qt_progress(finished, total, f"[MULTI PROCESS] Processing file - {patient_sample} DONE")

if __name__ == "__main__":
    main()