import pandas as pd

def get_opener(extension):
    if extension == "csv":
        def opener(path):
            return pd.read_csv(path)
        return opener

    elif extension == "parquet":
        def opener(path):
            return pd.read_parquet(path)
        return opener
    