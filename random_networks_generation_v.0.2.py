import numpy as np
import pandas as pd
from scipy.spatial import Delaunay
from mosna import mosna
from tysserand import tysserand as ty
import matplotlib.pyplot as plt
from tqdm import tqdm, trange
import seaborn as sns
######################################################### HELPER FUNCTION #################################################################
def generate_node(positions, phenotypes):
    if phenotypes != None:
        nodes = pd.DataFrame({
            'CellID': range(len(positions)),
            'X_position': positions[:, 0],
            'Y_position': positions[:, 1],
            'Phenotypes': phenotypes
        })
    else:
        nodes = pd.DataFrame({
            'CellID': range(len(positions)),
            'X_position': positions[:, 0],
            'Y_position': positions[:, 1],
            'Phenotypes': 'NaN'
        })
    return nodes

def plotting(nodes, axes, title, pairs=None):
    axes.clear()
    clustering = nodes['Phenotypes']
    coords = nodes[['X_position', 'Y_position']]
    celltypes_color_mapper = cluster_to_cmap(clustering.copy())
    coords = np.array(coords.values.tolist())
    if pairs is None:
        pairs = coords_to_pairs(coords)

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

def generate_cell_positions(n_cells, domain=(250.0, 250.0)):
    positions = np.random.rand(n_cells, 2) * domain
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

def initialize_phenotypes(n_nodes, phenotype_list, target_proportions):
    probs = [target_proportions.get(p, 0.0) for p in phenotype_list]
    probs = np.array(probs)
    probs /= probs.sum()
    return [np.random.choice(phenotype_list, p=probs) for _ in range(n_nodes)]

def compute_energy(edges, phenotypes, zscore_matrix, phenotype_to_index):
    energy = 0
    for _, row in edges.iterrows():
        u, v = row['source'], row['target']
        idx_u = phenotype_to_index[phenotypes[u]]
        idx_v = phenotype_to_index[phenotypes[v]]
        energy -= zscore_matrix[idx_u, idx_v]
    return energy

def gibbs_sampling(positions, edges, zscore_matrix, phenotype_list, phenotype_to_index, target_proportions, axes, n_iter=1000):
    phenotypes = initialize_phenotypes(len(positions), phenotype_list, target_proportions)

    nodes = generate_node(positions, phenotypes)
    plotting(nodes, axes[0,0],f"initial network with {len(nodes)} cells")

    neighbors = {i: [] for i in range(len(positions))}
    for _, row in edges.iterrows():
        u, v = row['source'], row['target']
        neighbors[u].append(v)
        neighbors[v].append(u)

    for _ in tqdm(range(n_iter), desc=f'[PROCESS] GIBBS Sampling for {len(positions)} cells '):
        for node in range(len(positions)):
            energy_list = []
            for candidate_type in phenotype_list:
                e = 0
                for neighbor in neighbors[node]:
                    idx_c = phenotype_to_index[candidate_type]
                    idx_n = phenotype_to_index[phenotypes[neighbor]]
                    e -= zscore_matrix[idx_c, idx_n]
                energy_list.append(e)  
            energy_array = np.array(energy_list)
            probs = np.exp(-(energy_array - energy_array.min()))  # stabilisation numérique
            probs /= probs.sum()
            phenotypes[node] = np.random.choice(phenotype_list, p=probs)

    return phenotypes

def adjust_proportions(
    positions,
    phenotypes,
    zscore_matrix,
    phenotype_list,
    phenotype_to_index,
    target_proportions,
    domain_size,
    axes,
    tolerance=0.01,
    n_following_add=50
):
    from collections import Counter

    def compute_deficit(current):
        return {
            p: max(0, float((target_proportions[p] - current.get(p, 0))))
            for p in phenotype_list
        }

    # Étape 1 — Ajout initial de n_initial_add cellules
    for _ in tqdm(range(n_following_add), desc='[PROCESS] Adding cells with assortivity gradient'):


        total = len(phenotypes)
        current_counts = Counter(phenotypes)
        current_props = {p: current_counts[p] / total for p in phenotype_list}
        deficit = compute_deficit(current_props)

        weights = np.array([deficit[p] for p in phenotype_list], dtype=float)
        """
        if np.all(weights < tolerance):
            break  
        """
        weights /= weights.sum()
        chosen_type = np.random.choice(phenotype_list, p=weights)

        pos_candidates = np.random.rand(20, 2) * domain_size

        best_pos = None
        best_energy = float('inf')

        for pos in pos_candidates:
            e = 0
            for i, pos_i in enumerate(positions):
                dist = np.linalg.norm(pos - pos_i)
                if dist < 0.1:
                    idx_c = phenotype_to_index[chosen_type]
                    idx_n = phenotype_to_index[phenotypes[i]]
                    e -= zscore_matrix[idx_c, idx_n]
            if e < best_energy:
                best_energy = e
                best_pos = pos

        if best_pos is not None:
            positions = np.vstack([positions, best_pos])
            phenotypes.append(chosen_type)


    # Étape 2 — Ajustement final via boucle `while`
    total = len(phenotypes)
    current_counts = Counter(phenotypes)
    current_props = {p: current_counts[p] / total for p in phenotype_list}
    deficit = compute_deficit(current_props)

    tqdm.write("[PROCESS] adding cell through phenotype proportion")
    while any(deficit[p] > tolerance * total for p in phenotype_list):
        for p in phenotype_list:
            if deficit[p] <= tolerance * total:
                continue
                        
            pos_candidates = np.random.rand(20, 2) * domain_size

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

def compute_assort(nodes, edges):
    nodes_onehot = nodes.join(pd.get_dummies(nodes['Phenotypes'], prefix='', prefix_sep=''))

    cell_types = nodes['Phenotypes'].unique().tolist()

    """
    mixmat = mosna.mixing_matrix(nodes_onehot, edges, cell_types)
    assort = mosna.attribute_ac(mixmat)
    mixmat_rand, assort_rand = mosna.randomized_mixmat(
        nodes_onehot, edges, cell_types, 
        n_shuffle=50, 
        parallel='max', 
        memory_limit='10GB',
        verbose=0)
    
    mixmat_mean, mixmat_std, mixmat_zscore = mosna.zscore(mixmat, mixmat_rand, return_stats=True)
    assort_mean, assort_std, assort_zscore = mosna.zscore(assort, assort_rand, return_stats=True)
    """
    mixmat_zscore = mosna.sample_assort_mixmat(nodes_onehot, edges, attributes=cell_types, sample_id=None, n_shuffle=50)
    z_cols = [x for x in mixmat_zscore.columns if x.endswith('Z') and not x.startswith('assort')]
    mixmat_z = mosna.series_to_mixmat(mixmat_zscore.loc[0, z_cols], discard=' Z').astype(float)
    return mixmat_z

def main(SEED, type_of_data, panel, patient, sample, iteration, domain_size, nb_cells, RUN_TEST):
    np.random.seed(SEED)

    if type_of_data == 'IMC':
        panel = ''
        sample_type = 'ROI'
    elif type_of_data == 'IF':
        panel = '_' + panel
        sample_type = 'layer'
    
    nodes_types = pd.read_parquet(f"./output_data/{type_of_data}{panel}_networks_sample/nodes_patient-{patient}_" 
                        f"{sample_type}-{sample}.parquet")[['Phenotypes','CellID']]
    
    cell_types = nodes_types['Phenotypes'].unique()
    target_proportions = nodes_types['Phenotypes'].value_counts(normalize=True).to_dict()
    phenotype_to_index = {p: i for i, p in enumerate(cell_types)}

    df = pd.read_parquet(f'output_data/synthetic_network_generation/mixmat_IF_IMC/{type_of_data}{panel}_patient-{patient}_{sample_type}-{sample}_mixmat.parquet')
    zscore_matrix = df.values

    fig, axes = plt.subplots(3, 2, figsize=(40, 30))

    ###### initial network ######

    initial_add = int(nb_cells * 0.2)
    positions = generate_cell_positions(initial_add, domain=domain_size)
    edges = build_edges_from_positions(positions)

    ###### post Gibbs sampling network ######

    phenotypes = gibbs_sampling(positions, edges, zscore_matrix, cell_types, phenotype_to_index, target_proportions, axes ,n_iter=iteration)

    nodes = generate_node(positions, phenotypes)
    plotting(nodes, axes[1,0], f"post Gibbs sampling network with {len(nodes)} cells")

    ###### post adding cell network ######

    positions, phenotypes = adjust_proportions(positions, phenotypes, zscore_matrix, cell_types, 
                                               phenotype_to_index, target_proportions, domain_size, axes, 
                                               tolerance=0.01, n_following_add=nb_cells-initial_add)

    nodes = generate_node(positions, phenotypes)
    if RUN_TEST:
        edges = build_edges_from_positions(positions)
        mixmat_z = compute_assort(nodes, edges)
        mixmat_z.to_parquet('test_assort.parquet')
        sns.heatmap(mixmat_z, center=0, cmap="vlag", annot=False, linewidths=.5, ax=axes[0,1])
        axes[0,1].set_title("assortativity")
        plt.xticks(rotation=45, ha='right')

        ecart_mixmat = (mixmat_z - df).abs()
        sns.heatmap(ecart_mixmat, center=0, cmap="vlag", annot=False, linewidths=.5, ax=axes[2,1])
        axes[2,1].set_title("assortativity")
        plt.xticks(rotation=45, ha='right')

    plotting(nodes, axes[2,0], f"post adjust proportion with {len(nodes)} cells")
    plt.tight_layout()
    plt.savefig(f'TEST_NETWORK_V2/test_{nb_cells}_{iteration}.png', dpi=300)

if __name__ == '__main__':
    type_of_data = 'IF' 
    panel = 'C2'
    patient = 'B'
    sample = '3'
    SEED = 42  
    RUN_TEST = True


    nb_cells = 2000
    iteration_MRF = [1]
    domain_size = (1000,1000)
    for i in iteration_MRF:
        main(SEED, type_of_data, panel, patient, sample, i, domain_size, nb_cells, RUN_TEST)