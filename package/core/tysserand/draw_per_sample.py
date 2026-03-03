import pandas as pd
import gc
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.rcParams.update({ "figure.facecolor": "#0b1020", 
                    "axes.facecolor": "#0b1020", 
                    "axes.edgecolor": "#b8c1ec", 
                    "axes.labelcolor": "#e0e6ff", 
                    "xtick.color": "#cdd6ff",
                    "ytick.color": "#cdd6ff", 
                    "text.color": "#e0e6ff", 
                    "font.size": 14, 
                    "axes.titleweight": "bold"}) 
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D

from tysserand import tysserand as ty
from mosna import mosna
from ...utils.read_extension import get_opener
from ...utils.find_sample_from_file import find_sample_from_file

def draw_per_sample(file, X_position, Y_position, Pheno_col, method, min_neighbors, saving_folder, temp_folder, patient_colmun, sample_column, extension):
    opener = get_opener(extension)
    node = opener(file)
    
    patient, sample = find_sample_from_file(file, patient_colmun, sample_column)

    clustering = node[Pheno_col]
    uniq = pd.Series(clustering).value_counts().index

    clusters_cmap = mosna.make_cluster_cmap(uniq)
    n_colors = len(clusters_cmap)
    celltypes_color_mapper = {x: clusters_cmap[i % n_colors] for i, x in enumerate(uniq)}

    coords = node[[X_position,Y_position]].to_numpy()
    pairs = ty.build_delaunay(coords)
            
    pairs = ty.link_solitaries(coords, pairs, method=method, min_neighbors=min_neighbors, verbose=0)

    fig, ax = ty.plot_network(
                coords, pairs,labels=clustering,
                color_mapper=celltypes_color_mapper,
                legend_opt={'loc': 'center left', 'bbox_to_anchor': (1.05, 0.5), 'fontsize': 30, 'markerscale': 5},
                size_nodes=8,
                figsize=(30,30)
                )
    
    for line in ax.lines:
        if isinstance(line, Line2D):
            line.set_color("white")
            line.set_alpha(0.8)
            line.set_linewidth(0.6)
    
    edge = pd.DataFrame(data=pairs, columns=['source', 'target'])

    if sample_column is None:
        ax.set_title(f"Tysserand network {patient_colmun} {patient}", fontsize=30)
        fig.savefig(saving_folder / f"net_{patient}.png", dpi = 600, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        node.to_parquet(temp_folder / f"nodes_{patient_colmun}-{patient}.parquet")
        edge.to_parquet(temp_folder / f"edges_{patient_colmun}-{patient}.parquet")

    else:
        ax.set_title(f"Tysserand network {patient_colmun} {patient} and {sample_column} {sample}", fontsize=30)
        fig.savefig(saving_folder / f"net_{patient}-{sample}.png", dpi = 600, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        node.to_parquet(temp_folder / f"nodes_{patient_colmun}-{patient}_{sample_column}-{sample}.parquet")
        edge.to_parquet(temp_folder / f"edges_{patient_colmun}-{patient}_{sample_column}-{sample}.parquet")
    
    del pairs, coords, celltypes_color_mapper, clustering, clusters_cmap, node, opener, n_colors, edge
    gc.collect()