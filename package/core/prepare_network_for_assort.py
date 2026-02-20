import pandas as pd
from tqdm import tqdm

from package.utils.read_extension import get_opener
from package.core.transform_nodes import transform_nodes
from package.core.assert_net_assortativity import assert_nodes_assortativity, assert_edges_assortativity

def prepare_network_for_assort(net_dir, temp_dir, Pheno_col, id_level_1="patient", id_level_2="sample", extension="csv", nodes_index=None):

    edges_files = sorted(net_dir.glob(f"edges_{id_level_1}-*_{id_level_2}-*.{extension}"))
    nodes_files = sorted(net_dir.glob(f"nodes_{id_level_1}-*_{id_level_2}-*.{extension}"))

    opener = get_opener(extension)

    for edges in tqdm(edges_files, desc="[PRE-PROCESSING] Edges traitement"):
        df_edge = opener(edges)
        assert_edges_assortativity(df_edge)
        name_file = f"{edges.stem}.parquet"
        df_edge.to_parquet(temp_dir / name_file)

    all_classes = set()
    for nodes in nodes_files:
        s = pd.read_csv(nodes)[Pheno_col].dropna().unique()
        all_classes.update(s)

    for nodes in tqdm(nodes_files, desc="[PRE-PROCESSING] Nodes traitement"):
        df_node = opener(nodes)
        df_node = transform_nodes(df_node, Pheno_col, nodes_index, all_classes)
        assert_nodes_assortativity(df_node, Pheno_col)

        name_file = f"{nodes.stem}.parquet"
        df_node.to_parquet(temp_dir / name_file)

    attributes_col = [f"{c}" for c in all_classes]

    return attributes_col
