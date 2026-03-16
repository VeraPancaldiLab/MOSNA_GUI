from mosna import mosna
import pandas as pd
from package.utils.read_extension import get_opener
from package.utils.find_sample import find_sample


def generate_cmap(net_dir, pheno_col, extension, patient_column_name, sample_column_name):
    opener = get_opener(extension)
    clustering = []
    for file in find_sample(net_dir, extension, patient_column_name, sample_column_name):
        node = opener(file)
        clustering.extend(node[pheno_col].dropna().tolist())
    uniq = pd.Series(clustering).value_counts().index

    clusters_cmap = mosna.make_cluster_cmap(uniq)
    n_colors = len(clusters_cmap)
    celltypes_color_mapper = {x: clusters_cmap[i % n_colors] for i, x in enumerate(uniq)}

    return celltypes_color_mapper