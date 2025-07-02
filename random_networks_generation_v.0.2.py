import numpy as np
import pandas as pd
from scipy.spatial import Delaunay
from mosna import mosna
from tysserand import tysserand as ty
import matplotlib.pyplot as plt
from tqdm import tqdm, trange
import seaborn as sns
import matplotlib.gridspec as gridspec
from scipy.ndimage import gaussian_filter
######################################################### HELPER FUNCTION #################################################################

def plotting(nodes, axes, title, pairs=None):
    axes.clear()
    clustering = nodes['Phenotypes']
    coords = nodes[['X_position', 'Y_position']]
    celltypes_color_mapper = cluster_to_cmap(clustering.copy())
    coords = np.array(coords.values.tolist())
    if pairs is None:
        pairs = coords_to_pairs(coords)

    if axes is None:
        ty.plot_network(
            coords.copy(), pairs.copy(),labels=clustering.copy(),
            color_mapper=celltypes_color_mapper,
            legend_opt={'loc': 'center left', 'bbox_to_anchor': (1.05, 0.5), 'fontsize': 10, 'markerscale': 2},
            size_nodes=50,
            figsize=(15,10)
            )
        plt.title(title)
    else:
        ty.plot_network(
            coords.copy(), pairs.copy(),labels=clustering.copy(),
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

######################################################### MRF TOOL FUNCTION #################################################################

def estimate_correlation_length(nodes, edges):
    positions = nodes[['X_position', 'Y_position']]
    distances = []
    for _, row in edges.iterrows():
        p1 = positions.loc[row['source']]
        p2 = positions.loc[row['target']]
        dist = np.linalg.norm(p1.values - p2.values)
        distances.append(dist)
    return np.mean(distances)

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
    correlation_length = estimate_correlation_length(nodes_initial, edges_initial)
    
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

    nodes, edges, fields = generate_synthetic_network_from_field(
        nodes_initial=nodes_types,
        edges_initial=edges_types,
        n_cells=nb_cells,
        domain_size=domain_size,
        target_proportions=target_proportions,
        cell_types=cell_types,
        oversample_factor=5
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
    plt.savefig(f'TEST_NETWORK_V2/CorrelatedField.png', dpi=300)

if __name__ == '__main__':
 
    SEED = 42  
    RUN_TEST = True  # active pour afficher les heatmaps
    type_of_data = 'IF' 
    panel = 'C2'
    patient = 'B'
    sample = '3'

    nb_cells = 5000
    domain_size = (1000,1000)

    if RUN_TEST:
        fig = plt.figure(figsize=(30, 20))
        gs = gridspec.GridSpec(2, 2, height_ratios=[1,1])

        ax_network = fig.add_subplot(gs[0, 0:1])
        ax_assortativity = fig.add_subplot(gs[1, 0])
        ax_ecart = fig.add_subplot(gs[1, 1])
    else:
        fig = plt.figure(figsize=(20, 15))
        
    print('\n')
    main(panel)
