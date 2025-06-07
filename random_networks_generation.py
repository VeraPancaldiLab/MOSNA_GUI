import pandas as pd
import numpy as np
import igraph as ig
import leidenalg
import random
from collections import Counter

def rebuild_zmatrix(zmatrix, cell_type):
    df = pd.DataFrame(0.0, index=cell_type, columns=cell_type)
    for i in zmatrix.index:
        z_score = zmatrix.loc[i]
        type1 = i.split(' - ')[0]
        type2 = i.split(' - ')[1].removesuffix(" Z")
        df.loc[type1, type2] = z_score
        df.loc[type2, type1] = z_score
    return df
def normalize_z_scores(z_matrix: pd.DataFrame) -> pd.DataFrame:
    max_abs = np.abs(z_matrix.values).max()
    return z_matrix / max_abs

def compute_affinity_matrix(A: pd.DataFrame, beta: float = 1.0) -> pd.DataFrame:
    """
    Compute affinity matrix ω_ab = exp(β * A_ab).
    """
    return np.exp(beta * A)

def generate_initial_assortative_configuration(
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    omega: pd.DataFrame
) -> pd.DataFrame:
    """
    Génère un DataFrame edges_init_df ['source','target']
    selon le modèle de configuration assortatif.
    """

    counts = pd.concat([edges_df.source, edges_df.target]).value_counts().to_dict()
    stubs = sum(([node] * deg for node, deg in counts.items()), [])
    types = dict(zip(nodes_df.CellID, nodes_df.Phenotypes))
    edges = []
    
    while len(stubs) >= 2:
        u = random.choice(stubs); stubs.remove(u)
        candidates = stubs
        weights = [omega.loc[types[u], types[y]] for y in candidates]
        v = random.choices(candidates, weights=weights, k=1)[0]; stubs.remove(v)
        edges.append((u, v))

    return pd.DataFrame(edges, columns=["source","target"])

def coarsen_graph_leiden(
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    resolution: float = 1.0
) -> (pd.DataFrame, pd.DataFrame):
    """
    Agrège en ~2k super-nœuds via Leiden.
    Renvoie nodes_coarse_df et edges_coarse_df.
    """

    verts = nodes_df.rename(columns={"CellID":"name"})[
        ["name","X_position","Y_position","Phenotypes"]
    ]

    g = ig.Graph.DataFrame(edges_df, directed=False, vertices=verts)
    part = leidenalg.find_partition(
        g, leidenalg.RBConfigurationVertexPartition,
        resolution_parameter=resolution
    )

    mem = part.membership

    g2 = g.contract_vertices(
        mem,
        combine_attrs={
            "name": lambda L: L[0],
            "X_position": lambda xs: float(np.mean(xs)),
            "Y_position": lambda ys: float(np.mean(ys)),
            "Phenotypes": lambda ph: Counter(ph).most_common(1)[0][0]
        }
    )
    g2.simplify(multiple=True, loops=True)

    nodes_coarse = pd.DataFrame({
        "CellID": g2.vs["name"],
        "X_position": g2.vs["X_position"],
        "Y_position": g2.vs["Y_position"],
        "Phenotypes": g2.vs["Phenotypes"],
    })

    edges_coarse = pd.DataFrame([
        (g2.vs[e.tuple[0]]["name"], g2.vs[e.tuple[1]]["name"])
        for e in g2.es
    ], columns=["source","target"])
    return nodes_coarse, edges_coarse

def edge_swap_mcmc(
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    omega: pd.DataFrame,
    num_iters: int = 100000
) -> pd.DataFrame:
    
    """
    Raffine edges_df par Metropolis MCMC pour ajuster l’assortativité.
    Renvoie edges_final_df ['source','target'].
    """
    edges = [tuple(r) for r in edges_df[["source","target"]].values]
    edge_set = {tuple(sorted(e)) for e in edges}
    types = dict(zip(nodes_df.CellID, nodes_df.Phenotypes))

    def score(a, b):
        return np.log(omega.loc[types[a], types[b]])

    for _ in range(num_iters):
        (u, v), (x, y) = random.sample(edges, 2)
        if len({u, v, x, y}) < 4: continue
        if tuple(sorted((u, y))) in edge_set or tuple(sorted((x, v))) in edge_set:
            continue
        delta = score(u, y) + score(x, v) - (score(u, v) + score(x, y))
        if delta >= 0 or random.random() < np.exp(delta):
            # swap
            edges.remove((u, v)); edges.remove((x, y))
            edge_set.remove(tuple(sorted((u, v)))); edge_set.remove(tuple(sorted((x, y))))
            e1, e2 = (u, y), (x, v)
            edges.extend([e1, e2])
            edge_set.update({tuple(sorted(e1)), tuple(sorted(e2))})
    return pd.DataFrame(edges, columns=["source","target"])

def main():
    patient = "A"
    sample = "01"

    z = pd.read_parquet(f"./output_data/assortativity/IMC_net_stat.parquet")
    nodes = pd.read_parquet(f"./output_data/IMC_networks_sample/nodes_patient-{patient}_" 
                        f"ROI-{sample}.parquet")[['CellID','X_position','Y_position','Phenotypes']]
    edges = pd.read_parquet(f"./output_data/IMC_networks_sample/edges_patient-{patient}_"
                            f"ROI-{sample}.parquet")
    
    submatrix = z.loc[:, z.columns.str.endswith('Z')].drop(columns='assort Z', axis=1).mean(axis=0)
    cell_types = nodes['Phenotypes'].unique() 

    A = rebuild_zmatrix(submatrix, cell_types)
    omega = compute_affinity_matrix(A, beta=1.0)

    ##### START TEST #####

    mask = np.isinf(z.values)
    rows, cols = np.where(mask)
    locations = [(z.index[i], z.columns[j], z.loc[z.index[i], z.columns[j]]) for i, j in zip(rows, cols)]
    print(locations)
    print(z.loc['patient-G_ROI-02', 'T-Cell CD3 - T-Cell CD3 Z'])

    ##### END TEST #####

    """
    init  = generate_initial_assortative_configuration(nodes, edges, omega)
    nodes_reduced_graph, edges_not_reduced_graph = coarsen_graph_leiden(nodes, init, resolution=1.0)
    final_edges = edge_swap_mcmc(nodes_reduced_graph, edges_not_reduced_graph, omega,
                                    num_iters=10*len(edges_not_reduced_graph))
    """
if __name__ == "__main__":
    main()