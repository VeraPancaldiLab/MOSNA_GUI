from package.utils.find_sample import find_sample
from package.utils.read_extension import get_opener

import pandas as pd

def assert_net_niches(net_dir, id_level_1, id_level_2, extension, Pheno_col):
    files = find_sample(net_dir, extension, id_level_1, id_level_2)
    opener = get_opener(extension)
    for file in files:
        df = opener(file)
        if isinstance(Pheno_col, str):
            assert Pheno_col in df.columns, f"{Pheno_col} does not exist in df.columns"
        else:
            assert all(col in df.columns for col in Pheno_col), (
                f"Certaines colonnes de Pheno_col n'existent pas dans le DataFrame : "
                f"{[col for col in Pheno_col if col not in df.columns]}"
            )