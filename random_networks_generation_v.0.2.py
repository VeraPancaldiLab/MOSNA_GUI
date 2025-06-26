# Synthetic spatial network generation using MRF and assortativity
import numpy as np
import pandas as pd
from scipy.spatial import Delaunay


def generate_cell_positions(n_cells, domain_size=(1.0, 1.0)):
    positions = np.random.rand(n_cells, 2) * domain_size
    return positions


def build_edges_from_positions(positions):
    tri = Delaunay(positions)
    edges = set()
    for simplex in tri.simplices:
        for i in range(3):
            for j in range(i+1, 3):
                a, b = simplex[i], simplex[j]
                edges.add(tuple(sorted((a, b))))
    edge_list = list(edges)
    edge_df = pd.DataFrame(edge_list, columns=['source', 'target'])
    return edge_df


def initialize_phenotypes(n_nodes, phenotype_list):
    return [np.random.choice(phenotype_list) for _ in range(n_nodes)]


def compute_energy(edges, phenotypes, zscore_matrix, phenotype_to_index):
    energy = 0
    for _, row in edges.iterrows():
        u, v = row['source'], row['target']
        idx_u = phenotype_to_index[phenotypes[u]]
        idx_v = phenotype_to_index[phenotypes[v]]
        energy -= zscore_matrix[idx_u, idx_v]
    return energy


def gibbs_sampling(positions, edges, zscore_matrix, phenotype_list, phenotype_to_index, n_iter=1000):
    phenotypes = initialize_phenotypes(len(positions), phenotype_list)

    neighbors = {i: [] for i in range(len(positions))}
    for _, row in edges.iterrows():
        u, v = row['source'], row['target']
        neighbors[u].append(v)
        neighbors[v].append(u)

    for _ in range(n_iter):
        for node in range(len(positions)):
            energy_list = []
            for candidate_type in phenotype_list:
                e = 0
                for neighbor in neighbors[node]:
                    idx_c = phenotype_to_index[candidate_type]
                    idx_n = phenotype_to_index[phenotypes[neighbor]]
                    e -= zscore_matrix[idx_c, idx_n]
                energy_list.append(np.exp(-e))
            probs = np.array(energy_list)
            probs /= probs.sum()
            phenotypes[node] = np.random.choice(phenotype_list, p=probs)

    return phenotypes


def adjust_proportions(positions, phenotypes, zscore_matrix, phenotype_list, phenotype_to_index, target_proportions, tolerance=0.01):
    from collections import Counter

    total = len(phenotypes)
    current_counts = Counter(phenotypes)
    current_props = {p: current_counts[p] / total for p in phenotype_list}
    deficit = {p: max(0, int((target_proportions[p] - current_props.get(p, 0)) * total)) for p in phenotype_list}

    while any(deficit[p] > tolerance * total for p in phenotype_list):
        for p in phenotype_list:
            if deficit[p] <= tolerance * total:
                continue

            pos_candidates = np.random.rand(10, 2)
            best_pos = None
            best_energy = float('inf')

            for pos in pos_candidates:
                e = 0
                for i, pos_i in enumerate(positions):
                    dist = np.linalg.norm(pos - pos_i)
                    if dist < 0.1:
                        idx_c = phenotype_to_index[p]
                        idx_n = phenotype_to_index[phenotypes[i]]
                        e -= zscore_matrix[idx_c, idx_n]
                if e < best_energy:
                    best_energy = e
                    best_pos = pos

            if best_pos is not None:
                positions = np.vstack([positions, best_pos])
                phenotypes.append(p)
                total += 1
                deficit[p] -= 1

    return positions, phenotypes


if __name__ == '__main__':
    phenotypes_list = ['A', 'B', 'C']
    phenotype_to_index = {p: i for i, p in enumerate(phenotypes_list)}
    zscore_matrix = np.array([
        [ 1.0, -0.5, 0.2],
        [-0.5, 1.0, -0.3],
        [ 0.2, -0.3, 1.0]
    ])
    target_proportions = {'A': 0.4, 'B': 0.4, 'C': 0.2}

    positions = generate_cell_positions(100)
    edge_df = build_edges_from_positions(positions)
    phenotypes = gibbs_sampling(positions, edge_df, zscore_matrix, phenotypes_list, phenotype_to_index, n_iter=500)
    positions, phenotypes = adjust_proportions(positions, phenotypes, zscore_matrix, phenotypes_list, phenotype_to_index, target_proportions, tolerance=0.01)

    node_df = pd.DataFrame({
        'cellID': range(len(positions)),
        'Xpos': positions[:, 0],
        'Ypos': positions[:, 1],
        'Phenotype': phenotypes
    })

    print(node_df.head())
    print(edge_df.head())
