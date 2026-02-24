import pandas as pd
from tqdm import tqdm

from package.utils.read_extension import get_opener
from .transform_nodes import transform_nodes
from .assert_net_assortativity import assert_nodes_assortativity, assert_edges_assortativity
from ...utils.emit_qt_progress import emit_qt_progress

def prepare_network_for_assort(net_dir, temp_dir, Pheno_col, id_level_1="patient", id_level_2="sample", extension="csv", nodes_index=None):

    edges_files = sorted(net_dir.glob(f"edges_{id_level_1}-*_{id_level_2}-*.{extension}"))
    nodes_files = sorted(net_dir.glob(f"nodes_{id_level_1}-*_{id_level_2}-*.{extension}"))
    tqdm.write(f"[INFO] Find {len(edges_files)+len(nodes_files)} files to trait (Nodes + Edges)")

    opener = get_opener(extension)

    emit_qt_progress(0, len(edges_files), "[PRE-PROCESSING] Edges traitement")
    for i, edges in enumerate(tqdm(edges_files, desc="[PRE-PROCESSING] Edges traitement")):
        df_edge = opener(edges)
        assert_edges_assortativity(df_edge)
        name_file = f"{edges.stem}.parquet"
        df_edge.to_parquet(temp_dir / name_file)
        emit_qt_progress(i, len(edges_files), "[PRE-PROCESSING] Edges traitement")

    all_classes = set()
    for nodes in nodes_files:
        s = opener(nodes)[Pheno_col].dropna().unique()
        all_classes.update(s)

    emit_qt_progress(0, len(nodes_files), "[PRE-PROCESSING] Nodes traitement")
    for i, nodes in enumerate(tqdm(nodes_files, desc="[PRE-PROCESSING] Nodes traitement")):
        df_node = opener(nodes)
        df_node = transform_nodes(df_node, Pheno_col, nodes_index, all_classes)
        assert_nodes_assortativity(df_node, Pheno_col)

        name_file = f"{nodes.stem}.parquet"
        df_node.to_parquet(temp_dir / name_file)
        emit_qt_progress(i, len(nodes_files), "[PRE-PROCESSING] Nodes traitement")

    attributes_col = [f"{c}" for c in all_classes]

    return attributes_col
