import pandas as pd
import numpy as np
import networkx as nx
import random

# Fixer la graine pour la reproductibilité
random.seed(42)
np.random.seed(42)

# --- 1. Charger les fichiers ---
nodes_df = pd.read_parquet("nodes.parquet")
edges_df = pd.read_parquet("edges.parquet")
net_df = pd.read_parquet("net.parquet", index_col=0)

# --- 2. Encoder les types cellulaires ---
cell_types = sorted(nodes_df['CellID'].unique())
type_to_idx = {t: i for i, t in enumerate(cell_types)}
idx_to_type = {i: t for t, i in type_to_idx.items()}
n_types = len(cell_types)

# --- 3. Fonction pour extraire la matrice z-score d’assortativité ---
def get_zscore_matrix(net_df, patient_id, sample_id):
    if isinstance(net_df.columns, pd.MultiIndex):
        submatrix = net_df.xs((patient_id, sample_id), axis=1, drop_level=False)
    else:
        raise ValueError("net.parquet doit avoir des colonnes multi-index (patient_id, sample_id)")
    return submatrix.values

# --- 4. Calcul de la matrice de potentiels psi ---
def compute_psi(z_matrix, beta=1.0):
    A = z_matrix / np.max(np.abs(z_matrix))  # normalisation entre -1 et 1
    psi = np.exp(beta * A)
    return psi

# --- 5. Gibbs sampling ---
def gibbs_sampling(G, psi, n_types, n_iter=20):
    for _ in range(n_iter):
        for node in G.nodes():
            neighbors = list(G.neighbors(node))
            neighbor_types = [G.nodes[n]["cell_type"] for n in neighbors]
            scores = []
            for t in range(n_types):
                if neighbor_types:
                    score = np.prod([psi[t, nt] for nt in neighbor_types])
                else:
                    score = 1.0
                scores.append(score)
            probs = np.array(scores)
            probs /= np.sum(probs)
            G.nodes[node]["cell_type"] = np.random.choice(n_types, p=probs)
    return G

# --- 6. Génération des graphes simulés pour chaque patient/sample ---
results = {}

grouped_nodes = nodes_df.groupby(["patient_id", "sample_id"])
grouped_edges = edges_df.groupby(["patient_id", "sample_id"])

for (pid, sid), node_group in grouped_nodes:
    print(f"Traitement Patient: {pid}, Sample: {sid}")

    # Extraire les arêtes correspondantes
    if (pid, sid) in grouped_edges.groups:
        edge_group = grouped_edges.get_group((pid, sid))
    else:
        edge_group = pd.DataFrame(columns=['source', 'target'])

    # Construire le graphe
    G = nx.Graph()
    for _, row in node_group.iterrows():
        node_id = row["node_id"]
        G.add_node(node_id, pos=(row["x"], row["y"]), cell_type=type_to_idx[row["cell_type"]])
    for _, row in edge_group.iterrows():
        G.add_edge(row["source"], row["target"])

    # Extraire la matrice z-score et calculer psi
    try:
        z_matrix = get_zscore_matrix(net_df, pid, sid)
        psi = compute_psi(z_matrix, beta=1.0)
    except Exception as e:
        print(f"Erreur chargement z-matrix pour ({pid}, {sid}): {e}")
        continue

    # Appliquer Gibbs sampling
    G_sampled = gibbs_sampling(G, psi, n_types=n_types, n_iter=30)
    results[(pid, sid)] = G_sampled

print("Simulation terminée. Résultats dans 'results' (dictionnaire).")
