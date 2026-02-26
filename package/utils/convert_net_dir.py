import pandas as pd
from package.utils.find_sample import find_sample
from package.utils.read_extension import get_opener

def convert_net_dir(net_dir, id_level_1, id_level_2, extension, save_dir):
    all_files = find_sample(net_dir, extension, id_level_1, id_level_2)
    opener = get_opener(extension)

    for file in all_files:
        df = opener(file)
        df.to_parquet(save_dir / file.name)