import numpy as np
import pandas as pd
from mosna import mosna
from tysserand import tysserand as ty
from collections import defaultdict
import os
import shutil

from math import sqrt
from scipy.ndimage import gaussian_filter
from scipy.spatial.distance import pdist, squareform
from scipy.stats import binned_statistic
from scipy.spatial import Delaunay
from scipy.optimize import curve_fit

from tqdm import tqdm
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.gridspec as gridspec
import imageio.v2 as imageio

######################################################### HELPER FUNCTION #################################################################
def define_panel(
    type_of_data, 
    panel
):
    """
    Determine panel prefix and sample type based on data modality.

    Parameters
    ----------
    type_of_data : str
        Type of spatial data ("IMC" or "IF").
    panel : str
        Panel identifier.

    Returns
    -------
    tuple
        Updated panel name and sample type.
    """
        
    if type_of_data == 'IMC':
        panel = ''
        sample_type = 'ROI'
    elif type_of_data == 'IF':
        panel = '_' + panel
        sample_type = 'layer'
    return panel, sample_type

def generate_plotting_figure(RUN_TEST):
    """
    Create a figure layout for plotting network, assortativity, and delta maps.

    Parameters
    ----------
    RUN_TEST : bool
        If True, create a full figure with 3 subplots.

    Returns
    -------
    tuple of matplotlib.axes._subplots.AxesSubplot or None
        Axes for network, assortativity heatmap, and delta heatmap.
    """

    if RUN_TEST:
        fig = plt.figure(figsize=(40, 30))
        gs = gridspec.GridSpec(2, 2, height_ratios=[1,1], wspace=0.4, hspace=0.5)

        ax_network = fig.add_subplot(gs[0, 0:1])
        ax_assortativity = fig.add_subplot(gs[1, 0])
        ax_ecart = fig.add_subplot(gs[1, 1])

        return ax_network, ax_assortativity, ax_ecart
    else:
        fig = plt.figure(figsize=(20, 15))

def plot_field(
    fields, 
    cell_types, 
    title
):
    """
    Plot a field image for each cell type using matplotlib.

    Parameters
    ----------
    fields : dict
        Dictionary {cell_type: 2D field array}.
    cell_types : list
        List of cell type names.
    title : str
        Title for saving the figure.
    """

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
    plt.savefig(f'TEST_NETWORK_V2/{title}.png', dpi=300)

def plotting(
    nodes, 
    axes, 
    title, 
    pairs=None,
    celltypes_color_mapper=None
):
    """
    Plot the spatial cell network with phenotypic labels and optional edge pairs.

    Parameters
    ----------
    nodes : DataFrame
        Node table with 'X_position', 'Y_position', 'Phenotypes'.
    axes : matplotlib.axes.Axes or None
        Axis to plot on. If None, creates a new figure.
    title : str
        Title of the plot.
    pairs : list of tuple, optional
        List of edges (pairs of coordinates), default is computed from Delaunay.
    """

    clustering = nodes['Phenotypes']
    if celltypes_color_mapper is None:
        celltypes_color_mapper = cluster_to_cmap(clustering)

    coords = nodes[['X_position', 'Y_position']]
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

def create_video_from_frames(
    folder="TEMP_FRAMES", 
    output="gibbs_network.mp4", 
    fps=5
):
    """
    Make a video thanks to temporary files

    Parameters
    ----------
    folder : str
        Dossier contenant les frames.
    output : str
        Nom du fichier de sortie (.mp4 ou .gif).
    fps : int
        Images par seconde.
    """
    images = []
    files = sorted([f for f in os.listdir(folder) if f.endswith('.png')])
    for file_name in files:
        file_path = os.path.join(folder, file_name)
        images.append(imageio.imread(file_path))
    imageio.mimsave(output, images, fps=fps)
    shutil.rmtree("./TEMP_FRAMES")

def coords_to_pairs(coords):
    """
    Generate edge pairs from coordinates using Delaunay triangulation 
    and links isolated nodes using additional criteria.

    Parameters
    ----------
    coords : ndarray
        Nx2 array of spatial coordinates.

    Returns
    -------
    pairs : list of tuple
        List of node index pairs representing edges.
    """

    pairs = ty.build_delaunay(coords)
    pairs = ty.link_solitaries(coords, pairs, method='delaunay', min_neighbors=15, verbose=0)
    return pairs

def cluster_to_cmap(clustering):
    """
    Generate a color map for each unique phenotype cluster.

    Parameters
    ----------
    clustering : array-like
        Cluster labels for each cell.

    Returns
    -------
    dict
        Mapping from cluster value to color.
    """

    if clustering is not None:
        nb_clust = clustering.max()
        uniq = pd.Series(clustering).value_counts().index

        clusters_cmap = mosna.make_cluster_cmap(uniq)

        n_colors = len(clusters_cmap)
        celltypes_color_mapper = {x: clusters_cmap[i % n_colors] for i, x in enumerate(uniq)}
    return celltypes_color_mapper

######################################################### USING FUNCTION #################################################################

def mixmat_normalisation(mixmat):
    """
    Normalize a cell-cell interaction matrix by z-scoring.

    Parameters
    ----------
    mixmat : DataFrame
        Raw interaction matrix.

    Returns
    -------
    DataFrame
        Normalized interaction matrix (zero-mean, unit variance).
    """

    return (mixmat - mixmat.mean()) / mixmat.std()

def compute_assort(
    nodes, 
    edges
):
    """
    Compute the Z-score assortativity matrix from a spatial network.

    Parameters
    ----------
    nodes : DataFrame
        Node table with phenotypic annotations.
    edges : DataFrame
        Edge table with 'source' and 'target'.

    Returns
    -------
    DataFrame
        Z-score assortativity matrix between phenotypes.
    """

    nodes_onehot = nodes.join(pd.get_dummies(nodes['Phenotypes'], prefix='', prefix_sep=''))
    cell_types = nodes['Phenotypes'].unique().tolist()

    mixmat_zscore = mosna.sample_assort_mixmat(nodes_onehot, edges, attributes=cell_types, sample_id=None, n_shuffle=50)
    z_cols = [x for x in mixmat_zscore.columns if x.endswith('Z') and not x.startswith('assort')]
    mixmat_z = mosna.series_to_mixmat(mixmat_zscore.loc[0, z_cols], discard=' Z').astype(float)
    return mixmat_z

def build_edges_from_positions(positions):
    """
    Build a graph from spatial coordinates using Delaunay triangulation.

    Parameters
    ----------
    positions : ndarray
        Nx2 array of cell positions.

    Returns
    -------
    DataFrame
        Edge table with columns ['source', 'target'].
    """
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

def generate_correlated_field(
    shape,
    correlation_length,
):
    """
    Generate a 2D Gaussian-correlated random field.

    Parameters
    ----------
    shape : tuple
        Field dimensions (height, width).
    correlation_length : float
        Spatial correlation length (Gaussian kernel std).

    Returns
    -------
    field : ndarray
        2D correlated scalar field.
    """

    noise = np.random.randn(*shape)
    sigma = correlation_length / sqrt(2)
    field = gaussian_filter(noise, sigma=correlation_length, mode='reflect')
    return field

def build_lattice_indices(
    xs, 
    ys, 
    shape
):
    """
    Create a lattice index matrix mapping spatial coordinates to cell indices.

    Parameters
    ----------
    xs : array-like
        X coordinates of cells.
    ys : array-like
        Y coordinates of cells.
    shape : tuple
        Shape of the output lattice (height, width).

    Returns
    -------
    lattice : ndarray of int
        2D array where each position holds the index of the corresponding cell, or -1 if empty.
    """

    lattice = -np.ones(shape, dtype=int)
    lattice[ys, xs] = np.arange(len(xs))
    return lattice

######################################################### FUNCTION CORE #################################################################

def estimate_correlation_length_fit(
    nodes, 
    nb_bins=100, 
    sample_size=80000
):
    """
    Estimate the spatial correlation length by fitting exponential decay 
    to phenotype similarity vs. distance.

    Parameters
    ----------
    nodes : DataFrame
        Node table with positions and phenotypes.
    nb_bins : int
        Number of bins for distance grouping.
    sample_size : int
        Number of random pairs sampled.

    Returns
    -------
    ξ_estimated : float
        Estimated correlation length (decay parameter).
    max_dist : float
        Maximum distance considered.
    """

    rng = np.random.default_rng(SEED)
    coords = nodes[['X_position', 'Y_position']].values
    labels = pd.get_dummies(nodes['Phenotypes']).values
    n = len(coords)

    dists, sims, seen_pairs = [], [], set()

    while len(dists) < sample_size:
        i, j = rng.integers(0, n), rng.integers(0, n)
        if i == j or (i, j) in seen_pairs or (j, i) in seen_pairs:
            continue
        seen_pairs.add((i, j))
        d = np.linalg.norm(coords[i] - coords[j])
        s = np.dot(labels[i], labels[j])
        dists.append(d)
        sims.append(s)

    dists, sims = np.array(dists), np.array(sims)
    bins = np.linspace(0, dists.max(), nb_bins)
    bin_means, bin_edges, _ = binned_statistic(dists, sims, statistic='mean', bins=bins)
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    bin_means = np.nan_to_num(bin_means, nan=0.0)

    def exp_decay(x, a, ξ): return a * np.exp(-x / ξ)
    popt, _ = curve_fit(exp_decay, bin_centers, bin_means, p0=(1.0, 50.0))

    ξ_estimated = popt[1]
    return ξ_estimated, dists.max()

def generate_balanced_fields(
    shape,
    cell_types,
    correlation_length,
    amplitude=1.0,
    local_noise_level=0.5,          ### between 0 and 1 
    save_dir="FIELDS"
):
    """
    Génère un champ global spatialement corrélé + un bruit local filtré pour chaque type.

    Parameters:
    -----------
    shape : tuple
        Dimensions du champ (height, width)
    cell_types : list
        Liste des types cellulaires
    correlation_length : float
        Longueur de corrélation spatiale
    amplitude : float
        Amplitude globale du champ
    local_noise_level : float
        Intensité du bruit local relatif
    save_dir : str
        Dossier où sauvegarder les champs générés

    Returns:
    --------
    fields : dict
        Dictionnaire {type_cellulaire: champ 2D}
    """
    local_noise_level = local_noise_level/100 + 0.05


    os.makedirs(save_dir, exist_ok=True)
    fields = {}

    # === Génère un champ global corrélé ===
    base_field = generate_correlated_field(shape, correlation_length)

    for ct in tqdm(cell_types, desc="[PROCESS] Correlated Field per Type"):
        field_path = f"{save_dir}/{ct}_field_corrl-{int(correlation_length)}_domain-{shape}.npy"

        if os.path.isfile(field_path):
            fields[ct] = np.load(field_path)
        else:
            # === Génère un bruit local filtré ===
            local_noise = np.random.randn(*shape)
            filtered_noise = gaussian_filter(local_noise, sigma=correlation_length / 3)

            # === Champ final : base + bruit doux ===
            final_field = amplitude * (base_field + local_noise_level * filtered_noise)
            fields[ct] = final_field

            np.save(field_path, final_field)

    return fields

def gibbs_sampling_potts_field(
    labels_init,
    fields,
    lattice_indices,
    edges,
    beta,
    J,
    n_iter,
    cell_types,
    mixmat,
    verbose=False,
    apply_gibbs=True,
    PLOT_GIBBS=False,
    record_frames=False
):
    """
    Perform Gibbs sampling using a Potts model with spatial field and cell-cell interaction matrix.

    Parameters
    ----------
    labels_init : array-like
        Initial cell type labels (strings).
    fields : dict
        Dictionary of {cell_type: 2D field array}.
    lattice_indices : ndarray
        Matrix mapping spatial positions to cell indices.
    edges : DataFrame
        DataFrame of graph edges with columns ['source', 'target'].
    beta : float
        Weight of the spatial field in energy calculation.
    J : float
        Global interaction strength scaling factor.
    n_iter : int
        Number of Gibbs iterations.
    cell_types : list
        List of cell types (labels).
    mixmat : DataFrame
        Normalized cell-cell interaction matrix.
    verbose : bool
        If True, print progress.
    apply_gibbs : bool
        If False, skip sampling and return initial labels.
    PLOT_GIBBS: bool
        if true, plot the convergence of Gibbs sampling
    record_frames : bool
        if True, generate a video of Gibbs sampling
    Returns
    -------
    final_labels : ndarray
        Final cell type labels after sampling.
    """
    if record_frames: 
        os.makedirs('./TEMP_FRAMES', exist_ok=True)

    shape = next(iter(fields.values())).shape
    n_types = len(cell_types)
    inv_cell_types = {ct: i for i, ct in enumerate(cell_types)}
    dict_cell_types = {i: ct for i, ct in enumerate(cell_types)}
    labels_int = np.array([inv_cell_types[label] for label in labels_init])

    xs, ys = np.where(lattice_indices != -1)
    n_cells = len(xs)
    field_stack = np.stack([fields[ct] for ct in cell_types], axis=-1)

    if not apply_gibbs:
        if verbose:
            print("[INFO] Gibbs sampling skipped — returning initial labels.")
        return np.array(labels_init)

    # === Carte des voisins basée sur les arêtes du graphe ===
    neighbor_map = defaultdict(list)
    for _, row in edges.iterrows():
        neighbor_map[row['source']].append(row['target'])
        neighbor_map[row['target']].append(row['source'])

    mixmat = mixmat_normalisation(mixmat)
    changes = []
    frames = []
    cell_types_color_mapper = None
    pairs = None
    for it in tqdm(range(n_iter), desc='[PROCESS] Gibbs Sampling to balance phenotypes'):

        old_labels = labels_int.copy()
        
        for idx in np.random.permutation(n_cells):
            neighbors = neighbor_map[idx]
            neighbor_labels = labels_int[neighbors] if neighbors else []

            log_probs = np.zeros(n_types)
            for k in range(n_types):

                # === Interaction Cells-Cells Energy ===
                interaction_energy = 0.0
                for label_j in neighbor_labels:
                    interaction_energy += J * mixmat.loc[dict_cell_types[k], dict_cell_types[label_j]]

                # === Fields Influence Energy ===
                x, y = xs[idx], ys[idx]
                field_energy = beta * field_stack[x, y, k]


                log_probs[k] = interaction_energy + field_energy

            # === Coversion in Probalities ===

            probs = np.exp(log_probs)
            probs /= np.sum(probs)

            # === Switch Phenotype ===

            labels_int[idx] = np.random.choice(n_types, p=probs)
        
        changes.append(np.sum(old_labels != labels_int))
        if record_frames:
            
            current_labels = np.array([cell_types[i] for i in labels_int])
            nodes_frame = pd.DataFrame({
                'CellID': range(len(xs)),
                'X_position': xs,
                'Y_position': ys,
                'Phenotypes': current_labels
            })
            if cell_types_color_mapper is None:
                clustering = nodes_frame['Phenotypes']
                cell_types_color_mapper = cluster_to_cmap(clustering)
            if pairs is None:
                coords = nodes_frame[['X_position', 'Y_position']]
                coords = np.array(coords.values.tolist())
                pairs = coords_to_pairs(coords)
            fig = plt.figure(figsize=(12, 10))
            plotting(nodes_frame, plt.gca(), f"Gibbs Iteration {it+1}", 
                     pairs=pairs, celltypes_color_mapper=cell_types_color_mapper)
            plt.axis('off')
            plt.tight_layout()
            plt.savefig(os.path.join('./TEMP_FRAMES', f"frame_{it:03d}.png"), dpi=300)
            plt.close()

        if verbose:
            changes = np.sum(old_labels != labels_int)
            tqdm.write(f"[Gibbs iteration {it+1}] Changes: {changes[it]}")
    if PLOT_GIBBS:
        plt.figure(figsize=(10, 6))
        plt.plot(changes, marker='o')
        plt.xlabel('Gibbs Iteration')
        plt.ylabel('Number of label changes')
        plt.title('Gibbs Sampling Convergence')
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(f'TEST_NETWORK_V2/convergence_gibbs_{nb_cells}.png', dpi=300)

    final_labels = np.array([cell_types[i] for i in labels_int])
    return final_labels

def generate_synthetic_network_potts_field(
    nodes_initial,
    n_cells,
    domain_size,
    target_proportions,
    cell_types,
    max_dist_domain,
    mixmat,
    randomness_rate=0.8,
    beta=1.0,
    J=1.0,
    oversample_factor=10,
    n_iter=5,
    verbose=False,
    gibbs_sampling=True,
    PLOT_GIBBS=False
):
    """
    Generate a synthetic spatial network of cells using Potts field dynamics and correlated attraction.

    Parameters
    ----------
    nodes_initial : DataFrame
        Input nodes from real data, with coordinates and phenotype info.
    n_cells : int
        Desired number of cells in the synthetic network.
    domain_size : tuple
        Size of the spatial domain (width, height).
    target_proportions : dict
        Desired cell type proportions.
    cell_types : list
        List of all possible cell types.
    max_dist_domain : float
        Max possible distance in the domain (for normalization).
    mixmat : DataFrame
        Interaction matrix for cell-cell affinity.
    randomness_rate : float
        rate to select random positions with correlated fields or by noise
        0.0 = random pick
        1.0 = pick only by correlated fields. 
    beta : float
        Weight of the spatial field.
    J : float
        Scaling factor for cell-cell interaction energy.
    oversample_factor : int
        Number of candidates generated before selecting final n_cells.
    n_iter : int
        Number of Gibbs sampling iterations.
    verbose : bool
        If True, print info during execution.
    gibbs_sampling : bool
        Whether to apply Gibbs sampling or not.
    PLOT_GIBBS : bool
        if True, plot the convergence of Gibbs sampling
    record_frames : bool
        if True, generate a video of Gibbs sampling
    Returns
    -------
    nodes : DataFrame
        Final node table with coordinates and phenotypes.
    edges : DataFrame
        Final edge list based on spatial proximity.
    fields : dict
        Correlated fields used for sampling.
    """
    # === Compute the correlation length ===

    shape = (domain_size[1], domain_size[0])
    non_corrected_correlation_length, max_distances = estimate_correlation_length_fit(nodes_initial)
    correlation_length = max_dist_domain / max_distances * non_corrected_correlation_length
    tqdm.write(f"Correlation Lentgh Estimated = {correlation_length}")

    # === Generate Fields ===

    fields = generate_balanced_fields(shape, cell_types, correlation_length)

    # === Generate random point and compute score by using fields ===

    n_points = n_cells * oversample_factor
    xs = np.random.randint(0, domain_size[0], size=n_points)
    ys = np.random.randint(0, domain_size[1], size=n_points)

    scores = np.vstack([fields[ct][ys, xs] for ct in cell_types]).T
    assigned_types = np.full(n_points, fill_value=None, dtype=object)
    target_counts = {ct: int(p * n_cells) for ct, p in target_proportions.items()}
    remaining_indices = set(range(n_points))

    for i, ct in enumerate(tqdm(cell_types, desc='[PROCESS] Cell Assignation')):
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
        num_main = int(count * randomness_rate)
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
        mixmat=mixmat,
        verbose=verbose,
        apply_gibbs=gibbs_sampling,
        PLOT_GIBBS=PLOT_GIBBS,
        record_frames=record_frames
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
def main():
    """
    Main function to load real data, compute fields, generate a synthetic spatial network, 
    and optionally visualize results.

    This function:
    - Loads input nodes and edges
    - Computes correlation length
    - Builds spatially correlated fields
    - Performs Gibbs sampling with Potts model
    - Computes and visualizes assortativity
    - Saves plots and synthetic network
    """

    global panel
    max_dist_domain = (domain_size[0]**2+domain_size[1]**2)**(1/2)
    np.random.seed(SEED)
    panel, sample_type = define_panel(type_of_data, panel)

    ################################### Import Data ###########################

    nodes_types = pd.read_parquet(f"./OUTPUT_DATA/temp/{type_of_data}{panel}_networks_sample/nodes_patient-{patient}_" 
                        f"{sample_type}-{sample}.parquet")
    edges_types = pd.read_parquet(f"./OUTPUT_DATA/temp/{type_of_data}{panel}_networks_sample/edges_patient-{patient}_" 
                        f"{sample_type}-{sample}.parquet")

    target_proportions = nodes_types['Phenotypes'].value_counts(normalize=True).to_dict()

    mixmat_inital = pd.read_parquet(f'OUTPUT_DATA/synthetic_network_generation/mixmat_IF_IMC/{type_of_data}{panel}_patient-{patient}_{sample_type}-{sample}_mixmat.parquet')
    cell_types = mixmat_inital.columns.tolist()

    ################################### RUN ###################################

    nodes, edges, fields = generate_synthetic_network_potts_field(
            nodes_initial=nodes_types,
            n_cells=nb_cells,
            domain_size=domain_size,
            target_proportions=target_proportions,
            cell_types=cell_types,
            max_dist_domain=max_dist_domain,
            beta=beta,
            J=J,
            mixmat=mixmat_inital,
            n_iter=iter_Gibbs,
            verbose=verbose,
            gibbs_sampling=gibbs_sampling,
            PLOT_GIBBS=PLOT_GIBBS,
            record_frames=record_frames
        )
    if FIELD_PLOT:
        plot_field(fields, cell_types, 'original_field')
        cor_l_before_process = estimate_correlation_length_fit(nodes, nb_bins=100)[0]
        print(f'[INFO] Generated Network Correlation Length = {cor_l_before_process}')

    if RUN_TEST:
        ax_network, ax_assortativity, ax_ecart = generate_plotting_figure(RUN_TEST)

        mixmat_z = compute_assort(nodes, edges)
        sns.heatmap(mixmat_z, center=0, cmap="vlag", annot=False, linewidths=.5, ax=ax_assortativity)
        ax_assortativity.set_title("Generated network assortativity")
        plt.xticks(rotation=45, ha='right')

        ecart_mixmat = (mixmat_z - mixmat_inital).abs()
        sns.heatmap(ecart_mixmat, center=0, cmap="vlag", annot=False, linewidths=.5, ax=ax_ecart)
        ax_ecart.set_title("Delta assortativity ground truth vs generated network")
        plt.xticks(rotation=45, ha='right')

        plotting(nodes, ax_network, f"Synthetic Network with {len(nodes)} cells")

    else:
        generate_plotting_figure(RUN_TEST)
        plotting(nodes, None, f"Synthetic Network with {len(nodes)} cells")

    plt.tight_layout()
    plt.savefig(f'TEST_NETWORK_V2/test_{nb_cells}.png', dpi=300)

    if gibbs_sampling and record_frames:
        create_video_from_frames(folder="TEMP_FRAMES", output=f"TEST_NETWORK_V2/gibbs_network_{nb_cells}.mp4", fps=5)
if __name__ == '__main__':

    # === Global parameter ===
    SEED = 42  
    RUN_TEST = False
    FIELD_PLOT = False
    
    # === Gibbs Sampling parameters ===
    gibbs_sampling = True
    iter_Gibbs = 50
    verbose = False
    PLOT_GIBBS = True
    record_frames = True

    # === Data parameter ===
    type_of_data = 'IF' 
    panel = 'C2'
    patient = 'B'
    sample = '3'

    # === Network parameter ===
    nb_cells = 10000
    domain_size = (5000,5000)

    # === Pott parameter ===
    J = 1.0
    beta = 0.5
    
    # === MAIN ===
    print('\n')
    main()
