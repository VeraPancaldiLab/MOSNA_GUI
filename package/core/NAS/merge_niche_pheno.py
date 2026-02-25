import pandas as pd
import numpy as np

def merge_niche_pheno(net_dir, pheno_col, niches):
    node_files = sorted(net_dir.glob("nodes_*.parquet"))
    assert node_files, f"Aucun fichier nodes_*.parquet dans {net_dir}"

    cell_types = np.hstack([
        pd.read_parquet(f, columns=[pheno_col])[pheno_col].to_numpy()
        for f in node_files
    ])

    assert len(cell_types) == len(niches), (
        f"Lengths mismatch: cell_types={len(cell_types)} vs cluster_labels={len(niches)}"
    )
    return cell_types