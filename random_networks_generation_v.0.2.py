import numpy as np
import pandas as pd
from mosna import mosna
from tysserand import tysserand as ty
from collections import defaultdict

from scipy.ndimage import gaussian_filter
from scipy.spatial.distance import pdist, squareform
from scipy.stats import binned_statistic
from scipy.spatial import Delaunay

from tqdm import tqdm
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.gridspec as gridspec
######################################################### HELPER FUNCTION #################################################################

def plotting(nodes, axes, title, pairs=None):
    clustering = nodes['Phenotypes']
    coords = nodes[['X_position', 'Y_position']]
    celltypes_color_mapper = cluster_to_cmap(clustering)
    coords = np.array(coords.values.tolist())
    if pairs is None:
        pairs = coords_to_pairs(coords)

    if axes is None:
        ty.plot_network(
            coords, pairs,labels=clustering,
            color_mapper=celltypes_color_mapper,
            legend_opt={'loc': 'center left', 'bbox_to_anchor': (1.05, 0.5), 'fontsize': 10, 'markerscale': 2},
            size_nodes=50,
            figsize=(15,10)
            )
        plt.title(title)
    else:
        ty.plot_network(
            coords, pairs,labels=clustering,
            color_mapper=celltypes_color_mapper,
            legend_opt={'loc': 'center left', 'bbox_to_anchor': (1.05, 0.5), 'fontsize': 10, 'markerscale': 2},
            size_nodes=50,
            figsize=(15,10),
            ax=axes
            )
        axes.set_title(title)

def coords_to_pairs(coords):
    pairs = ty.build_delaunay(coords)
    pairs = ty.link_solitaries(coords, pairs, method='delaunay', min_neighbors=15, verbose=0)
    return pairs

def cluster_to_cmap(clustering):
    if clustering is not None:
        nb_clust = clustering.max()
        uniq = pd.Series(clustering).value_counts().index

        clusters_cmap = mosna.make_cluster_cmap(uniq)

        n_colors = len(clusters_cmap)
        celltypes_color_mapper = {x: clusters_cmap[i % n_colors] for i, x in enumerate(uniq)}
    return celltypes_color_mapper

######################################################### USING FUNCTION #################################################################

def estimate_correlation_length_naive(nodes, edges):
    positions = nodes[['X_position', 'Y_position']]
    distances = []
    for _, row in edges.iterrows():
        p1 = positions.loc[row['source']]
        p2 = positions.loc[row['target']]
        dist = np.linalg.norm(p1.values - p2.values)
        distances.append(dist)
    return np.mean(distances)

def estimate_correlation_length(nodes, max_distance=600, nb_bins=30, sample_size=80000):
    rng = np.random.default_rng(SEED)

    coords = nodes[['X_position', 'Y_position']].values
    labels = pd.get_dummies(nodes['Phenotypes']).values
    n = len(coords)

    dists = []
    sims = []
    seen_pairs = set()

    while len(dists) < sample_size:
        i = rng.integers(0, n)
        j = rng.integers(0, n)
        if i == j or (i, j) in seen_pairs or (j, i) in seen_pairs:
            continue
        seen_pairs.add((i, j))

        dist = np.linalg.norm(coords[i] - coords[j])
        sim = np.dot(labels[i], labels[j])  # peut être 0 ou 1 (ou plus si multi-labels)
        dists.append(dist)
        sims.append(sim)

    dists = np.array(dists)
    sims = np.array(sims)

    # Binning
    bins = np.linspace(0, max_distance, nb_bins)
    stat, bin_edges, _ = binned_statistic(dists, sims, statistic='mean', bins=bins)

    stat = np.nan_to_num(stat, nan=0.0)
    try:
        decay_index = np.where(stat < (stat[0] / np.e))[0][0]
        return (bins[decay_index] + bins[decay_index - 1]) / 2
    except IndexError:
        return np.mean(bins)

def compute_assort(nodes, edges):
    nodes_onehot = nodes.join(pd.get_dummies(nodes['Phenotypes'], prefix='', prefix_sep=''))
    cell_types = nodes['Phenotypes'].unique().tolist()

    mixmat_zscore = mosna.sample_assort_mixmat(nodes_onehot, edges, attributes=cell_types, sample_id=None, n_shuffle=50)
    z_cols = [x for x in mixmat_zscore.columns if x.endswith('Z') and not x.startswith('assort')]
    mixmat_z = mosna.series_to_mixmat(mixmat_zscore.loc[0, z_cols], discard=' Z').astype(float)
    return mixmat_z

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

def generate_correlated_field(shape, correlation_length):
    noise = np.random.randn(*shape)
    field = gaussian_filter(noise, sigma=correlation_length, mode='reflect')
    return field

######################################################### FUNCTION CORE #################################################################

def generate_synthetic_network_from_field(
    nodes_initial,
    edges_initial,
    n_cells,
    domain_size,
    target_proportions,
    cell_types,
    oversample_factor=5,
):
    shape = (domain_size[1], domain_size[0])
    correlation_length = estimate_correlation_length_naive(nodes_initial, edges_initial)
    
    # Générer un champ corrélé par type cellulaire (pour affichage + diversité)
    fields = {}
    for ct in tqdm(cell_types, desc='[PROCESS] Generate all fields'):
        fields[ct] = generate_correlated_field(shape, correlation_length)

    n_points = n_cells * oversample_factor
    xs = np.random.uniform(0, domain_size[0], n_points).astype(int)
    ys = np.random.uniform(0, domain_size[1], n_points).astype(int)

    # Construire matrice score (n_points x n_types)
    scores = np.vstack([fields[ct][ys, xs] for ct in cell_types]).T

    assigned_types = np.full(n_points, fill_value=None, dtype=object)
    target_counts = {ct: int(p * n_cells) for ct, p in target_proportions.items()}
    remaining_indices = set(range(n_points))

    for i, ct in enumerate(tqdm(cell_types, desc="[PROCESS] Assigning cell types through fields")):
        count = target_counts.get(ct, 0)
        if not remaining_indices or count == 0:
            continue
        subset = np.array(list(remaining_indices))
        subset_scores = scores[subset, i]
        if len(subset_scores) < count:
            count = len(subset_scores)
        top_idx_local = np.argsort(subset_scores)[-count:]
        top_idx_global = subset[top_idx_local]
        assigned_types[top_idx_global] = ct
        remaining_indices -= set(top_idx_global)

    keep_indices = np.where(assigned_types != None)[0]
    if len(keep_indices) > n_cells:
        keep_indices = keep_indices[:n_cells]

    nodes = pd.DataFrame({
        'CellID': range(len(keep_indices)),
        'X_position': xs[keep_indices],
        'Y_position': ys[keep_indices],
        'Phenotypes': assigned_types[keep_indices]
    })

    positions = nodes[['X_position', 'Y_position']].values
    edges = build_edges_from_positions(positions)

    return nodes, edges, fields

def build_lattice_indices(xs, ys, shape):
    lattice = -np.ones(shape, dtype=int)
    lattice[ys, xs] = np.arange(len(xs))
    return lattice

def gibbs_sampling_potts_field_beta(
    labels_init,
    fields,
    lattice_indices,
    beta,
    J,
    n_iter,
    cell_types
):
    shape = next(iter(fields.values())).shape
    n_types = len(cell_types)
    inv_cell_types = {ct: i for i, ct in enumerate(cell_types)}
    labels_int = np.array([inv_cell_types[label] for label in labels_init])
    xs, ys = np.where(lattice_indices != -1)
    n_cells = len(xs)

    field_stack = np.stack([fields[ct] for ct in cell_types], axis=-1)

    for _ in tqdm(range(n_iter), desc='[PROCESS] Gibbs Sampling to balance phenotypes'):
        for idx in np.random.permutation(n_cells):
            x, y = xs[idx], ys[idx]
            neighbors = [
                (x + dx, y + dy)
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]
                if 0 <= x + dx < shape[0] and 0 <= y + dy < shape[1]
            ]
            neighbor_idxs = [lattice_indices[nx, ny] for nx, ny in neighbors if lattice_indices[nx, ny] != -1]
            neighbor_labels = labels_int[neighbor_idxs]

            log_probs = np.zeros(n_types)
            for k in range(n_types):
                interaction_energy = -J * np.sum(neighbor_labels == k)
                field_energy = -beta * field_stack[x, y, k]
                log_probs[k] = interaction_energy + field_energy
            probs = np.exp(log_probs - np.max(log_probs))
            probs /= np.sum(probs)

            labels_int[idx] = np.random.choice(n_types, p=probs)

    final_labels = np.array([cell_types[i] for i in labels_int])
    return final_labels

def gibbs_sampling_potts_field(
    labels_init,
    fields,
    lattice_indices,
    edges,
    beta,
    J,
    n_iter,
    cell_types,
    verbose=False
):
    shape = next(iter(fields.values())).shape
    n_types = len(cell_types)
    inv_cell_types = {ct: i for i, ct in enumerate(cell_types)}
    labels_int = np.array([inv_cell_types[label] for label in labels_init])
    
    xs, ys = np.where(lattice_indices != -1)
    n_cells = len(xs)

    field_stack = np.stack([fields[ct] for ct in cell_types], axis=-1)

    # --- Construire la carte des voisins à partir du graphe ---
    neighbor_map = defaultdict(list)
    for _, row in edges.iterrows():
        neighbor_map[row['source']].append(row['target'])
        neighbor_map[row['target']].append(row['source'])

    for it in tqdm(range(n_iter), desc='[PROCESS] Gibbs Sampling to balance phenotypes'):
        old_labels = labels_int.copy()
        for idx in np.random.permutation(n_cells):
            neighbors = neighbor_map[idx]
            neighbor_labels = labels_int[neighbors] if neighbors else []

            log_probs = np.zeros(n_types)
            for k in range(n_types):
                interaction_energy = -J * np.sum(neighbor_labels == k)
                x, y = xs[idx], ys[idx]
                field_energy = -beta * field_stack[x, y, k]
                log_probs[k] = interaction_energy + field_energy

            probs = np.exp(log_probs - np.max(log_probs))
            probs /= np.sum(probs)

            labels_int[idx] = np.random.choice(n_types, p=probs)

        if verbose:
            changes = np.sum(old_labels != labels_int)
            tqdm.write(f"[Gibbs iteration {it+1}] Number of label changes: {changes}")

    final_labels = np.array([cell_types[i] for i in labels_int])
    return final_labels

def generate_synthetic_network_potts_field(
    nodes_initial,
    n_cells,
    domain_size,
    target_proportions,
    cell_types,
    beta=1.0, # intensité du champ externe
    J=1.0,    # interaction entre voisins
    amplitude=1000,
    oversample_factor=5,
    n_iter=5,
    verbose=False
):
    shape = (domain_size[1], domain_size[0])
    correlation_length = estimate_correlation_length(nodes_initial)
    tqdm.write(f"Correlation Lentgh Estimated = {correlation_length}")

    fields = {}
    for ct in tqdm(cell_types, desc="[PROCESS] Generating correlated fields"):
        fields[ct] = amplitude * generate_correlated_field(shape, correlation_length)

    n_points = n_cells * oversample_factor
    xs = np.random.randint(0, domain_size[0], size=n_points)
    ys = np.random.randint(0, domain_size[1], size=n_points)

    scores = np.vstack([fields[ct][ys, xs] for ct in cell_types]).T
    assigned_types = np.full(n_points, fill_value=None, dtype=object)
    target_counts = {ct: int(p * n_cells) for ct, p in target_proportions.items()}
    remaining_indices = set(range(n_points))

    for i, ct in enumerate(tqdm(cell_types, desc='[PROCESS] adding cells through Ising field by phenotypes ')):
        count = target_counts.get(ct, 0)
        if not remaining_indices or count == 0:
            continue
        subset = np.array(list(remaining_indices))
        raw_scores = scores[subset, i]

        # Rescale les scores pour avoir des probabilités positives
        min_score = raw_scores.min()
        scaled_scores = raw_scores - min_score

        if scaled_scores.sum() == 0:
            probabilities = np.ones_like(scaled_scores) / len(scaled_scores)
        else:
            probabilities = scaled_scores / scaled_scores.sum()

        # Choix principal par scores pondérés
        num_main = int(count * 0.9)
        num_random = count - num_main

        chosen_main = np.random.choice(subset, size=min(num_main, len(subset)), replace=False, p=probabilities)

        # Choix aléatoire bruité
        remaining_for_noise = list(set(subset) - set(chosen_main))
        if len(remaining_for_noise) < num_random:
            num_random = len(remaining_for_noise)
        chosen_noise = np.random.choice(remaining_for_noise, size=num_random, replace=False)

        chosen_indices = np.concatenate([chosen_main, chosen_noise])
        assigned_types[chosen_indices] = ct
        remaining_indices -= set(chosen_indices)

    keep_indices = np.where(assigned_types != None)[0]
    if len(keep_indices) > n_cells:
        keep_indices = keep_indices[:n_cells]

    xs_final = xs[keep_indices]
    ys_final = ys[keep_indices]
    assigned_types = np.array(assigned_types)[keep_indices]
    """
    lattice_indices = build_lattice_indices(xs_final, ys_final, shape)
    updated_labels = gibbs_sampling_potts_field_beta(
        assigned_types,
        fields,
        lattice_indices,
        beta=beta,
        J=J,
        n_iter=n_iter,
        cell_types=cell_types
    )
    """
    lattice_indices = build_lattice_indices(xs_final, ys_final, shape)
    positions = np.vstack((xs_final, ys_final)).T
    edges = build_edges_from_positions(positions)

    updated_labels = gibbs_sampling_potts_field(
        labels_init=assigned_types,
        fields=fields,
        lattice_indices=lattice_indices,
        edges=edges,                    
        beta=beta,
        J=J,
        n_iter=n_iter,
        cell_types=cell_types,
        verbose=verbose
    )

    nodes = pd.DataFrame({
        'CellID': range(len(xs_final)),
        'X_position': xs_final,
        'Y_position': ys_final,
        'Phenotypes': updated_labels
    })

    positions = nodes[['X_position', 'Y_position']].values
    edges = build_edges_from_positions(positions)

    return nodes, edges, fields

######################################################### MAIN #################################################################

def main(panel):
    np.random.seed(SEED)
    if type_of_data == 'IMC':
        panel = ''
        sample_type = 'ROI'
    elif type_of_data == 'IF':
        panel = '_' + panel
        sample_type = 'layer'

    nodes_types = pd.read_parquet(f"./output_data/{type_of_data}{panel}_networks_sample/nodes_patient-{patient}_" 
                        f"{sample_type}-{sample}.parquet")
    edges_types = pd.read_parquet(f"./output_data/{type_of_data}{panel}_networks_sample/edges_patient-{patient}_" 
                        f"{sample_type}-{sample}.parquet")

    target_proportions = nodes_types['Phenotypes'].value_counts(normalize=True).to_dict()

    df = pd.read_parquet(f'output_data/synthetic_network_generation/mixmat_IF_IMC/{type_of_data}{panel}_patient-{patient}_{sample_type}-{sample}_mixmat.parquet')
    cell_types = df.columns.tolist()

    if NAIVE:
        nodes, edges, fields = generate_synthetic_network_from_field(
        nodes_initial=nodes_types,
        edges_initial=edges_types,
        n_cells=nb_cells,
        domain_size=domain_size,
        target_proportions=target_proportions,
        cell_types=cell_types,
        oversample_factor=10
        )

    else:
        nodes, edges, fields = generate_synthetic_network_potts_field(
            nodes_initial=nodes_types,
            n_cells=nb_cells,
            domain_size=domain_size,
            target_proportions=target_proportions,
            cell_types=cell_types,
            beta=beta,
            J=J,
            n_iter=iter_Gibbs,
            verbose=verbose
        )

    if RUN_TEST:
        mixmat_z = compute_assort(nodes, edges)
        sns.heatmap(mixmat_z, center=0, cmap="vlag", annot=False, linewidths=.5, ax=ax_assortativity)
        ax_assortativity.set_title("Generated network assortativity")
        plt.xticks(rotation=45, ha='right')

        ecart_mixmat = (mixmat_z - df).abs()
        sns.heatmap(ecart_mixmat, center=0, cmap="vlag", annot=False, linewidths=.5, ax=ax_ecart)
        ax_ecart.set_title("Delta assortativity ground truth vs generated network")
        plt.xticks(rotation=45, ha='right')

        plotting(nodes, ax_network, f"Synthetic Network with {len(nodes)} cells")

    else:
        plotting(nodes, None, f"Synthetic Network with {len(nodes)} cells")

    plt.tight_layout()
    plt.savefig(f'TEST_NETWORK_V2/test_{nb_cells}.png', dpi=300)

    # --- Affichage des champs par type ---

    n_types = len(cell_types)
    fig_fields, axes_fields = plt.subplots(1, n_types, figsize=(4 * n_types, 4))
    if n_types == 1:
        axes_fields = [axes_fields]
    for ax, ct in zip(axes_fields, cell_types):
        im = ax.imshow(fields[ct], cmap='viridis')
        ax.set_title(f'Correlated Field: {ct}')
        ax.axis('off')
        fig_fields.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    plt.tight_layout()
    plt.savefig(f'TEST_NETWORK_V2/CorrelatedField.png', dpi=300)

if __name__ == '__main__':
 
    SEED = 42  
    RUN_TEST = False
    NAIVE = False
    type_of_data = 'IF' 
    panel = 'C2'
    patient = 'B'
    sample = '3'

    nb_cells = 1000
    domain_size = (2000,2000)

    J = 3.0
    beta = 0.3
    iter_Gibbs = 50
    verbose = True

    if RUN_TEST:
        fig = plt.figure(figsize=(40, 30))
        gs = gridspec.GridSpec(2, 2, height_ratios=[1,1], wspace=0.4, hspace=0.5)

        ax_network = fig.add_subplot(gs[0, 0:1])
        ax_assortativity = fig.add_subplot(gs[1, 0])
        ax_ecart = fig.add_subplot(gs[1, 1])
    else:
        fig = plt.figure(figsize=(20, 15))
        
    print('\n')
    main(panel)
