import pandas as pd
import numpy as np
from scipy.spatial import Delaunay
import random
from tqdm import tqdm

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
    """
    Generate edges DataFrame from nodes via Delaunay triangulation.
    Returns edges_df with ['source','target'] where source/target are integer indices.
    """
    pts = nodes_df[['X_position','Y_position']].values
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
    return np.exp(beta * A)

def reposition_nodes_by_MRF(
    nodes_df: pd.DataFrame,
    edges_df: pd.DataFrame,
    omega: pd.DataFrame,
    iterations: int = 100,
    learning_rate: float = 0.01
) -> pd.DataFrame:
    """
    Adjust node positions using a Gaussian MRF-like continuous optimization:
    E = sum_{(i,j) in edges} ω[type_i, type_j] * ||x_i - x_j||^2.
    Uses initial adjacency edges_df for forces.
    Returns a new DataFrame with updated 'X_position' and 'Y_position'.
    """
    pos = nodes_df[['X_position','Y_position']].values.copy()
    types = nodes_df['Phenotypes'].values
    edge_pairs = edges_df[['source','target']].values.astype(int)
    
    for _ in range(iterations):
        grads = np.zeros_like(pos)
        for u, v in edge_pairs:
            w = omega.loc[types[u], types[v]]
            diff = pos[u] - pos[v]
            force = 2 * w * diff
            grads[u] += force
            grads[v] -= force
        pos -= learning_rate * grads

    nodes_new = nodes_df.copy()
    nodes_new['X_position'] = pos[:, 0]
    nodes_new['Y_position'] = pos[:, 1]
    return nodes_new
def main():
    patient = "A"
    sample = "01"

    z = pd.read_parquet(f"./output_data/synthetic_network_generation/data_to_build/mixmat_mean_IMC.parquet")
    
    nodes_types = pd.read_parquet(f"./output_data/IMC_networks_sample/nodes_patient-{patient}_" 
                        f"ROI-{sample}.parquet")[['Phenotypes','CellID']]

    cell_types = nodes_types['Phenotypes'].unique() 

    phenotype_props = nodes_types['Phenotypes'].value_counts(normalize=True).to_dict()
    nodes_initial = generate_random_nodes(2000, phenotype_props, x_range=(0,500), y_range=(0,500))
    edges_initial = generate_delaunay_edges(nodes_initial)

    A = normalize_z_scores(z)
    omega = compute_affinity_matrix(A, beta=1.0)

    
    nodes = reposition_nodes_by_MRF(nodes_initial, edges_initial, omega,
                               iterations=200, learning_rate=0.005)
    edges = generate_delaunay_edges(nodes)

if __name__ == "__main__":
    main()