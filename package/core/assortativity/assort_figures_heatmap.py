import matplotlib.pyplot as plt
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from matplotlib.colors import TwoSlopeNorm
from matplotlib.gridspec import GridSpec
from scipy.cluster.hierarchy import linkage, dendrogram
from scipy.spatial.distance import pdist

def assort_figures_heatmap(net_stat, save_dir, homo_pair=False):
    assort_cols = net_stat.columns[net_stat.columns.str.endswith(" Z")]
    assort_cols = [col for col in assort_cols if col != "assort Z"]

    if not homo_pair:
        col_to_remove = []
        for col in assort_cols:
            col_treated = col[:-2]
            pheno1, pheno2 = col_treated.split(" - ")
            if pheno1 == pheno2:
                col_to_remove.append(col)

        assort_cols = [col for col in assort_cols if col not in col_to_remove]

    heatmap_data = net_stat[assort_cols].T.astype(float)
    heatmap_data = heatmap_data.replace([np.inf, -np.inf], np.nan)
    heatmap_data = heatmap_data.dropna(axis=0, how="all")
    heatmap_data = heatmap_data.dropna(axis=1, how="all")

    cluster_matrix_cols = heatmap_data.T.fillna(0)
    col_linkage = linkage(pdist(cluster_matrix_cols, metric="euclidean"), method="ward")

    cluster_matrix_rows = heatmap_data.fillna(0)
    row_linkage = linkage(pdist(cluster_matrix_rows, metric="euclidean"), method="ward")

    col_dendro_preview = dendrogram(col_linkage, no_plot=True)
    col_leaf_order = col_dendro_preview["leaves"]

    row_dendro_preview = dendrogram(row_linkage, no_plot=True)
    row_leaf_order = row_dendro_preview["leaves"]

    heatmap_data = heatmap_data.iloc[row_leaf_order, col_leaf_order]

    vals = heatmap_data.to_numpy()
    valid_vals = vals[~np.isnan(vals)]

    if valid_vals.size == 0:
        raise ValueError("La matrice ne contient aucune valeur exploitable.")

    zlim = np.nanmax(np.abs(valid_vals))
    norm = TwoSlopeNorm(vmin=-zlim, vcenter=0, vmax=zlim)

    cmap = plt.cm.coolwarm.copy()
    cmap.set_bad(color="black")

    fig = plt.figure(figsize=(28, 24))

    gs = GridSpec(
        nrows=2,
        ncols=3,
        width_ratios=[24, 7, 1],
        height_ratios=[3, 16],
        wspace=0.08,
        hspace=0.05
    )

    ax_dendro_col = fig.add_subplot(gs[0, 0])
    ax_heat = fig.add_subplot(gs[1, 0])
    ax_dendro_row = fig.add_subplot(gs[1, 1])

    right_gs = gs[1, 2].subgridspec(
        nrows=1,
        ncols=1
    )

    cbar_ax = fig.add_subplot(right_gs[0, 0])

    ax_top_unused_1 = fig.add_subplot(gs[0, 1])
    ax_top_unused_2 = fig.add_subplot(gs[0, 2])

    ax_top_unused_1.axis("off")
    ax_top_unused_2.axis("off")

    dendrogram(
        col_linkage,
        ax=ax_dendro_col,
        no_labels=True,
        color_threshold=None
    )

    ax_dendro_col.set_xticks([])
    ax_dendro_col.set_yticks([])
    ax_dendro_col.set_xlabel("")
    ax_dendro_col.set_ylabel("")
    ax_dendro_col.set_title("Images Clustering", fontsize=14)

    sns.heatmap(
        heatmap_data,
        cmap=cmap,
        center=0,
        vmin=-zlim,
        vmax=zlim,
        ax=ax_heat,
        cbar_ax=cbar_ax,
        cbar_kws={"label": "Z-score"},
        yticklabels=heatmap_data.index,
        xticklabels=heatmap_data.columns
    )

    ax_heat.set_ylabel("Assortativity Z-scores", fontsize=13)
    ax_heat.set_xlabel("Images sample", fontsize=13)
    ax_heat.set_title("Assortativity heatmap by images", fontsize=16)
    ax_heat.tick_params(axis="x", rotation=45, labelsize=9)
    ax_heat.tick_params(axis="y", labelsize=9)

    ax_heat.yaxis.tick_left()
    ax_heat.yaxis.set_label_position("left")

    dendrogram(
        row_linkage,
        ax=ax_dendro_row,
        orientation="right",
        no_labels=True,
        color_threshold=None
    )

    ax_dendro_row.set_xticks([])
    ax_dendro_row.set_yticks([])
    ax_dendro_row.set_xlabel("")
    ax_dendro_row.set_ylabel("")
    ax_dendro_row.set_title("Clustering of assortativity scores", fontsize=14)

    n_rows = heatmap_data.shape[0]
    ax_dendro_row.set_ylim(10 * n_rows, 0)

    cbar_ax.tick_params(labelsize=11)
    cbar_ax.set_ylabel("Z-score", fontsize=13)

    plt.tight_layout()
    if homo_pair:
        plt.savefig(save_dir / "Assortativity_heatmap_with_dendrogram.png", dpi=300)
    else:
        plt.savefig(save_dir / "Assortativity_heatmap_with_dendrogram_without_auto_paired_pheno.png", dpi=300)
    plt.close()
    return