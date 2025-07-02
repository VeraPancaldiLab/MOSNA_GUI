import numpy as np
import pandas as pd
from scipy.spatial import Delaunay
from mosna import mosna
from tysserand import tysserand as ty
import matplotlib.pyplot as plt
from tqdm import tqdm, trange
import seaborn as sns
import matplotlib.gridspec as gridspec
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

def gibbs_sampling(nodes, edges, zscore_matrix, cell_types, phenotype_to_index, n_iter=10, temperature=1000.0, update_fraction=0.3):

    positions = nodes[["X_position", "Y_position"]].values
    types = nodes["Phenotypes"].values
    for _ in tqdm(range(n_iter), desc=f'[PROCESS] Gibbs Sampling iterations = {len(nodes)} '):
        nodes_to_update = np.random.choice(len(positions), size=int(update_fraction * len(positions)), replace=False)
        for i in nodes_to_update:
            current_type = types[i]
            neighbor_indices = np.where((edges["source"] == i) | (edges["target"] == i))[0]
            if len(neighbor_indices) == 0:
                continue
            neighbors = []
            for idx in neighbor_indices:
                row = edges.iloc[idx]
                neighbor = row["target"] if row["source"] == i else row["source"]
                neighbors.append(neighbor)
            neighbor_types = types[neighbors]
            energy_array = []
            for t in cell_types:
                e = 0
                for nt in neighbor_types:
                    idx_c = phenotype_to_index[t]
                    idx_n = phenotype_to_index[nt]
                    e -= zscore_matrix[idx_c, idx_n]
                energy_array.append(e)
            energy_array = np.array(energy_array)
            # Softmax with temperature
            logits = -energy_array / temperature
            logits -= np.max(logits)
            probs = np.exp(logits)
            probs /= probs.sum()
            print(probs)
            types[i] = np.random.choice(cell_types, p=probs)
    nodes["Phenotypes"] = types
    return nodes

def adjust_proportions(
    nodes,
    zscore_matrix,
    phenotype_list,
    phenotype_index,
    target_proportions,
    n_following_add=50
):
    from collections import Counter

    def compute_deficit(current):
        return {
            p: max(0, float((target_proportions[p] - current.get(p, 0))))
            for p in phenotype_list
        }
    
    positions = nodes[["X_position", "Y_position"]].values
    phenotypes = nodes["Phenotypes"].values

    target_counts = {ct: int(prop * (len(nodes) + n_following_add)) for ct, prop in target_proportions.items()}

    # Étape 1 — Ajout initial de n_initial_add cellules
    for ct, target_count in target_counts.items():
        current_count = (nodes["Phenotypes"] == ct).sum()
        to_add = target_count - current_count
        
        if to_add <= 0:
            continue
        for _ in tqdm(range(to_add), desc=f'[PROCESS] adding {to_add} {ct} in Network '):
            best_pos = None
            best_energy = np.inf
            for _ in range(100):  # Plus de candidats
                pos = np.random.rand(2)
                e = 0
                for i, pos_i in enumerate(positions):
                    dist = np.linalg.norm(pos - pos_i)
                    
                    if dist > 5:  # Ignore voisins trop proche
                        continue
                    
                    weight = np.exp(-dist / 0.05)  # pondération gaussienne
                    neighbor_type = nodes.iloc[i]["Phenotypes"]
                    idx_c = phenotype_index[ct]
                    idx_n = phenotype_index[neighbor_type]
                    e -= weight * zscore_matrix[idx_c, idx_n]
                if e < best_energy:
                    best_energy = e
                    best_pos = pos
            # Ajout de la cellule avec la meilleure position trouvée
            new_node = {"X_position": best_pos[0], "Y_position": best_pos[1], "Phenotypes": ct}
            nodes = pd.concat([nodes, pd.DataFrame([new_node])], ignore_index=True)
            positions = np.vstack([positions, best_pos])

    return nodes

def compute_assort(nodes, edges):
    nodes_onehot = nodes.join(pd.get_dummies(nodes['Phenotypes'], prefix='', prefix_sep=''))
    cell_types = nodes['Phenotypes'].unique().tolist()

    mixmat_zscore = mosna.sample_assort_mixmat(nodes_onehot, edges, attributes=cell_types, sample_id=None, n_shuffle=50)
    z_cols = [x for x in mixmat_zscore.columns if x.endswith('Z') and not x.startswith('assort')]
    mixmat_z = mosna.series_to_mixmat(mixmat_zscore.loc[0, z_cols], discard=' Z').astype(float)
    return mixmat_z

def main(panel):

    np.random.seed(SEED)

    ############## INITIALIZE DATA ##############

    if type_of_data == 'IMC':
        panel = ''
        sample_type = 'ROI'
    elif type_of_data == 'IF':
        panel = '_' + panel
        sample_type = 'layer'
    
    nodes_types = pd.read_parquet(f"./output_data/{type_of_data}{panel}_networks_sample/nodes_patient-{patient}_" 
                        f"{sample_type}-{sample}.parquet")[['Phenotypes','CellID']]
    
    target_proportions = nodes_types['Phenotypes'].value_counts(normalize=True).to_dict()
    
    df = pd.read_parquet(f'output_data/synthetic_network_generation/mixmat_IF_IMC/{type_of_data}{panel}_patient-{patient}_{sample_type}-{sample}_mixmat.parquet')
    cell_types = df.columns
    phenotype_to_index = {p: i for i, p in enumerate(cell_types)}
    zscore_matrix = df.values
    ############## GENERATE NETWORK ##############

    ###### initial network ######

    initial_add = int(nb_cells * 0.2)
    positions = generate_cell_positions(initial_add, domain=domain_size)
    edges = build_edges_from_positions(positions)

    ###### post Gibbs sampling network ######
    phenotypes = initialize_phenotypes(len(positions), cell_types, target_proportions)
    nodes = generate_node(positions, phenotypes)
    plotting(nodes, ax_network_1, f"Initial Network")

    nodes = gibbs_sampling(nodes, edges, zscore_matrix, cell_types, phenotype_to_index, n_iter=iteration_MRF_run1)
    plotting(nodes, ax_network_2, f"post Gibbs sampling network with {len(nodes)} cells")

    ###### post adding cell network ######

    nodes = adjust_proportions(nodes, zscore_matrix, cell_types, phenotype_to_index, target_proportions,n_following_add=nb_cells-initial_add)
    edges = build_edges_from_positions(nodes[['X_position','Y_position']])  

    if gibbs_sampling_ENDING_RUN:
        nodes = gibbs_sampling(nodes, edges, zscore_matrix, cell_types, phenotype_to_index,n_iter=iteration_MRF_run2)

    if RUN_TEST:
        mixmat_z = compute_assort(nodes, edges)
        sns.heatmap(mixmat_z, center=0, cmap="vlag", annot=False, linewidths=.5, ax=ax_assortativity)
        ax_assortativity.set_title("generated network assorativity")
        plt.xticks(rotation=45, ha='right')

        ecart_mixmat = (mixmat_z - df).abs()
        sns.heatmap(ecart_mixmat, center=0, cmap="vlag", annot=False, linewidths=.5, ax=ax_ecart)
        ax_ecart.set_title("delta assortativity ground truth and generated network assorativity")
        plt.xticks(rotation=45, ha='right')

    plotting(nodes, ax_network_3, f"post adjust proportion with {len(nodes)} cells")
    plt.tight_layout()
    plt.savefig(f'TEST_NETWORK_V1/test_{nb_cells}_GB1-{iteration_MRF_run1}_GB2-{iteration_MRF_run2}.png', dpi=300)

if __name__ == '__main__':    
    SEED = 42  
    RUN_TEST = False
    gibbs_sampling_ENDING_RUN = False

    ############## INITIALIZE PLOT ##############
    
    if RUN_TEST:
        fig = plt.figure(figsize=(40, 30))
        gs = gridspec.GridSpec(2, 3, height_ratios=[1, 1])

        ax_assortativity = fig.add_subplot(gs[1, 0:2])
        ax_ecart = fig.add_subplot(gs[1, 2])
    else:
        fig = plt.figure(figsize=(30, 15))
        gs = gridspec.GridSpec(1, 3, height_ratios=[1])
    ax_network_1 = fig.add_subplot(gs[0, 0])
    ax_network_2 = fig.add_subplot(gs[0, 1])
    ax_network_3 = fig.add_subplot(gs[0, 2])

    ############## INPUT PARAMETERS ##############
    type_of_data = 'IF' 
    panel = 'C2'
    patient = 'B'
    sample = '3'


    nb_cells = 2000
    iteration_MRF_run1 = 5
    iteration_MRF_run2 = 2
    domain_size = (1000,1000)

    main(panel)