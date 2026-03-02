import pandas as pd
from package.utils.find_sample import find_sample

def find_all_pheno(net_dir, extension, pheno_col, id_level_1, id_level_2):
    frames = []
    files = find_sample(net_dir, extension, id_level_1, id_level_2)
    for file in files:
        df = pd.read_parquet(file, columns=[pheno_col])
        frames.append(df)  
    df_tot = pd.concat(frames, ignore_index=True)
    return df_tot[pheno_col].unique().tolist()