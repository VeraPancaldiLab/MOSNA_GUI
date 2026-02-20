import pandas as pd 

def transform_nodes(nodes, Pheno_col, nodes_index, all_classes):
    if nodes_index is not None:
        nodes = nodes.set_index(nodes_index)
    ph = pd.Categorical(nodes[Pheno_col], categories=all_classes)
    dummies = pd.get_dummies(ph)
    dummies = dummies.reindex(columns=[f"{c}" for c in all_classes], fill_value=0)      
    dummies = dummies.fillna(0).astype("uint8")
    nodes = pd.concat([nodes, dummies], axis=1)

    return nodes