from package.utils.find_sample import find_sample

import pandas as pd

from tysserand import tysserand as ty
from mosna import mosna
from package.utils.emit_qt_progress import emit_qt_progress

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def draw_tysserand_niches(net_dir, save_dir, id_level_1, id_level_2, X, Y):
    files = find_sample(net_dir, 'parquet', id_level_1, id_level_2)
    emit_qt_progress(0,len(files),"[PROCESS] Draw Tysserand with niches labels")
    for file in files:

        clustering = file['niches']
        uniq = pd.Series(clustering).value_counts().index
        clusters_cmap = mosna.make_cluster_cmap(uniq)
        n_colors = len(clusters_cmap)
        celltypes_color_mapper = {x: clusters_cmap[i % n_colors] for i, x in enumerate(uniq)}

        coords = file[[X, Y]].to_numpy()

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
        fig.tight_layout()

        fig.savefig(save_dir / f"net_{file.stem[6:]}_niches", dpi = 300, bbox_inches="tight")
        plt.close(fig)
        emit_qt_progress(1,len(files),"[PROCESS] Draw Tysserand with niches labels")

    return None