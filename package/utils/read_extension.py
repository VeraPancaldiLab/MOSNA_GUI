import pandas as pd

def get_opener(extension):
    if extension == "csv":
        def opener(path):
            return pd.read_csv(path)

    elif extension == "parquet":
        def opener(path):
            return pd.read_parquet(path)
    
    elif extension == "tsv":
        def opener(path):
            return pd.read_csv(path, sep='\t')
        
    return opener
    