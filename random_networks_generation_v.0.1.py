import pandas as pd
import numpy as np
from scipy.spatial import Delaunay
import random
from tqdm import tqdm, trange
import matplotlib.pyplot as plt
from mosna import mosna
from tysserand import tysserand as ty

def generate_random_nodes(
    n: int,
    phenotype_props: dict,
    x_range: tuple = (0.0, 1.0),
    y_range: tuple = (0.0, 1.0),
    seed: int = 42
) -> pd.DataFrame:
    """
    Generate n random nodes with positions uniform in x_range and y_range,
    and Phenotypes sampled according to phenotype_props.
    Returns nodes_df with columns ['CellID','X_position','Y_position','Phenotypes'].
    """
    np.random.seed(seed)
    random.seed(seed)
    
    xs = np.random.uniform(x_range[0], x_range[1], size=n)
    ys = np.random.uniform(y_range[0], y_range[1], size=n)
    phenotypes = list(phenotype_props.keys())
    probs = np.array(list(phenotype_props.values()), dtype=float)
    probs /= probs.sum()
    sampled_ph = random.choices(phenotypes, weights=probs, k=n)
    
    nodes_df = pd.DataFrame({
        'CellID': [f'cell_{i:04d}' for i in range(n)],
        'X_position': xs,
        'Y_position': ys,
        'Phenotypes': sampled_ph
    })
    return nodes_df

def generate_delaunay_edges(
    nodes_df: pd.DataFrame
) -> pd.DataFrame:

    if isinstance(nodes_df, pd.DataFrame):
        pts = nodes_df[['X_position','Y_position']].values
    elif isinstance(nodes_df, np.ndarray):
        pts = nodes_df
    tri = Delaunay(pts)
    edge_set = set()
    for simplex in tri.simplices:
        for i in range(3):
            for j in range(i+1, 3):
                u, v = simplex[i], simplex[j]
                edge_set.add(tuple(sorted((u, v))))
    edges_df = pd.DataFrame(list(edge_set), columns=['source','target'])
    return edges_df

def normalize_z_scores(z_matrix: pd.DataFrame) -> pd.DataFrame:
    max_abs = np.abs(z_matrix.values).max()
    return z_matrix / max_abs

def compute_affinity_matrix(A: pd.DataFrame, beta: float = 1.0) -> pd.DataFrame:
    return np.exp(beta * A)*np.sign(A)

def reposition_nodes_by_MRF_vectorized(
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    omega: pd.DataFrame,
    iterations: int = 100,
    learning_rate: float = 0.01,
    center: bool = False,
    decay: bool = True
) -> pd.DataFrame:
    
    """
    Vectorized version of MRF node repositioning with adaptive learning rate.
    """
    # Index mapping: node ID -> row index
    node_id_to_index = {node_id: idx for idx, node_id in enumerate(nodes_df['CellID'])}
    n_nodes = len(nodes_df)

    ids = list(node_id_to_index.values())
    src_idx, tgt_idx = [], []
    for id in ids:
        target_tab = [x for x in ids if x != id]
        for id_target in target_tab:
            src_idx.append(id)
            tgt_idx.append(id_target)

    # Position and type arrays
    pos = nodes_df[['X_position', 'Y_position']].values.astype(np.float64).copy()
    types = np.array(nodes_df['Phenotypes'])

    # Build valid edge list
    def generate_source_target_from_edges(edges_df):
        src_idx, tgt_idx = [], []
        for _, row in edges_df.iterrows():
            u_id, v_id = row['source'], row['target']
            if u_id == v_id:
                continue
            if u_id in node_id_to_index and v_id in node_id_to_index:
                src_idx.append(node_id_to_index[u_id])
                tgt_idx.append(node_id_to_index[v_id])
        src_idx = np.array(src_idx)
        tgt_idx = np.array(tgt_idx)
        return src_idx, tgt_idx

    #src_idx, tgt_idx = generate_source_target_from_edges(edges_df)
    # Prepare omega matrix access (convert to 2D array + lookup dict)
    phenos = nodes_df['Phenotypes'].unique()
    pheno_to_idx = {p: i for i, p in enumerate(phenos)}
    omega_array = omega.reindex(index=phenos, columns=phenos, fill_value=0).values
    type_idx = np.array([pheno_to_idx[t] for t in types])

    for t in trange(1, iterations + 1, desc="[PROCESSING] MRF vectorized"):
        grads = np.zeros_like(pos)
        
        diff = pos[src_idx] - pos[tgt_idx]
        type_u = type_idx[src_idx]
        type_v = type_idx[tgt_idx]
        w = omega_array[type_u, type_v].reshape(-1, 1)

        forces = 2.0 * w * diff
        np.add.at(grads, src_idx, forces)
        np.subtract.at(grads, tgt_idx, forces)

        eta = learning_rate / np.sqrt(t) if decay else learning_rate
        pos -= eta * grads

        """
        print("Gradient norm:", grads.max())
        print(omega_array[type_u, type_v].mean())
        print(diff.mean())
        print(forces.max(), forces.min())
        """
        #edges_df = generate_delaunay_edges(pos)
        #src_idx, tgt_idx = generate_source_target_from_edges(edges_df)

    if center:
        pos -= pos.mean(axis=0)

    # Update DataFrame
    nodes_new = nodes_df.copy()
    nodes_new['X_position'] = pos[:, 0]
    nodes_new['Y_position'] = pos[:, 1]
    
    return nodes_new

def cluster_to_cmap(clustering):
    if clustering is not None:
        nb_clust = clustering.max()
        uniq = pd.Series(clustering).value_counts().index

        clusters_cmap = mosna.make_cluster_cmap(uniq)

        n_colors = len(clusters_cmap)
        celltypes_color_mapper = {x: clusters_cmap[i % n_colors] for i, x in enumerate(uniq)}
    return celltypes_color_mapper

def plotting(nodes, nodes_initial):

    clustering = nodes['Phenotypes']
    coords = nodes[['X_position', 'Y_position']]
    clustering_initial = nodes_initial['Phenotypes']
    coords_initial = nodes_initial[['X_position', 'Y_position']]

    celltypes_color_mapper = cluster_to_cmap(clustering)
    celltypes_color_mapper_initial = cluster_to_cmap(clustering_initial)

    def coords_to_pairs(coords):
        pairs = ty.build_delaunay(coords)
        pairs = ty.link_solitaries(coords, pairs, method='delaunay', min_neighbors=15, verbose=0)
        return pairs
    
    coords = np.array(coords.values.tolist())
    pairs = coords_to_pairs(coords)

    coords_initial = np.array(coords_initial.values.tolist())
    pairs_initial = coords_to_pairs(coords_initial)

    fig, axes = plt.subplots(1, 2, figsize=(40, 30))

    ty.plot_network(
        coords, pairs,labels=clustering,
        color_mapper=celltypes_color_mapper,
        legend_opt={'loc': 'center left', 'bbox_to_anchor': (1.05, 0.5), 'fontsize': 10, 'markerscale': 2},
        size_nodes=50,
        figsize=(15,10),
        ax=axes[1]
        )
    axes[1].set_title(f"MRF corrected network", fontsize=10)
    
    ty.plot_network(
        coords_initial, pairs_initial,labels=clustering_initial,
        color_mapper=celltypes_color_mapper_initial,
        legend_opt={'loc': 'center left', 'bbox_to_anchor': (1.05, 0.5), 'fontsize': 10, 'markerscale': 2},
        size_nodes=50,
        figsize=(15,10),
        ax=axes[0]
        )
    axes[0].set_title(f"random corrected network", fontsize=10)
    plt.tight_layout()
    plt.savefig(f"TEST_MRF_iteration_{iterations}.png", bbox_inches="tight")

def main(iterations, learning_rate, nb_cell):
    patient = "A"
    sample = "01"

    z = pd.read_parquet(f"./output_data/synthetic_network_generation/data_to_build/mixmat_mean_IMC.parquet")
    
    nodes_types = pd.read_parquet(f"./output_data/IMC_networks_sample/nodes_patient-{patient}_" 
                        f"ROI-{sample}.parquet")[['Phenotypes','CellID']]
    cell_types = nodes_types['Phenotypes'].unique() 

    phenotype_props = nodes_types['Phenotypes'].value_counts(normalize=True).to_dict()
    nodes_initial = generate_random_nodes(nb_cell, phenotype_props, x_range=(0,500), y_range=(0,500))
    edges_initial = generate_delaunay_edges(nodes_initial)

    A = normalize_z_scores(z)
    omega = compute_affinity_matrix(A, beta=1.0)
    nodes = reposition_nodes_by_MRF_vectorized(nodes_initial, edges_initial, omega,
                               iterations=iterations, learning_rate=learning_rate)
    
    return nodes, nodes_initial

if __name__ == "__main__":
    iterations = 1000
    learning_rate = 0.00005
    nb_cell = 500

    nodes, nodes_initial = main(iterations=iterations, learning_rate=learning_rate, nb_cell=nb_cell)
    plotting(nodes, nodes_initial)