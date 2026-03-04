from package.utils.find_sample import find_sample

import pandas as pd

from tysserand import tysserand as ty
from mosna import mosna
from package.utils.emit_qt_progress import emit_qt_progress

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

def draw_tysserand_niches(net_dir, save_dir, id_level_1, id_level_2, X, Y):

    files = find_sample(net_dir, 'parquet', id_level_1, id_level_2)
    emit_qt_progress(0,len(files),"[PROCESS] Draw Tysserand with niches labels")

    for i, file in enumerate(files):

        node = pd.read_parquet(file)
        clustering = node['niches']
        uniq = pd.Series(clustering).value_counts().index
        clusters_cmap = mosna.make_cluster_cmap(uniq)
        n_colors = len(clusters_cmap)
        celltypes_color_mapper = {x: clusters_cmap[i % n_colors] for i, x in enumerate(uniq)}

        coords = node[[X, Y]].to_numpy()

        edges_path = file.parent / ("edges_" + file.name[6:])
        edges = pd.read_parquet(edges_path)
        pairs = edges[["source", "target"]].to_numpy(dtype=int)

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

        ax.set_title(f"Network with niches clusters for {file.stem[6:]}")

        fig.savefig(save_dir / f"net_{file.stem[6:]}_niches.png", dpi = 300, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        emit_qt_progress(i,len(files),"[PROCESS] Draw Tysserand with niches labels")

    return None