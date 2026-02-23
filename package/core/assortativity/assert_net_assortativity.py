def assert_nodes_assortativity(nodes, Pheno_col):
    
    assert Pheno_col in list(nodes.columns) , f"There is no {Pheno_col} in your nodes"

    return None


def assert_edges_assortativity(edges):

    assert sorted(list(edges.columns)) == ["source","target"], "edges files must contain source and target columns only"

    return None