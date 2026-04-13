import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import TwoSlopeNorm
from pathlib import Path

from mosna import mosna

plt.rcParams.update({ "figure.facecolor": "#0b1020", 
                    "axes.facecolor": "#0b1020", 
                    "axes.edgecolor": "#b8c1ec", 
                    "axes.labelcolor": "#e0e6ff", 
                    "xtick.color": "#cdd6ff",
                    "ytick.color": "#cdd6ff", 
                    "text.color": "#e0e6ff", 
                    "font.size": 14, 
                    "axes.titleweight": "bold"})

def assort_figures_mixing_matrix_without_diag(net_stat, save_dir, is_sample):

    saving_folder = save_dir / "assort_files_without_diag"
    saving_folder.mkdir(parents=True, exist_ok=True)

    for id in net_stat.index:
        assort_df_Z = net_stat.loc[[id]]
        assort_df_Z = assort_df_Z[net_stat.columns[net_stat.columns.str.endswith(" Z")]]
        assort_Z = assort_df_Z['assort Z']
        if is_sample is not None:
            patient = assort_df_Z.index[0].split('-')[1]
            patient = patient.split('_')[0]
            sample = assort_df_Z.index[0].split('-')[2]
        else:
            patient = assort_df_Z.index[0].split('-')[1]

        assort_df_Z = assort_df_Z.reset_index().drop(columns=['id','assort Z'])
        mat_Z = mosna.series_to_mixmat(assort_df_Z.iloc[0])

        fig, ax = plt.subplots(figsize=(12, 10))

        mat_Z = mat_Z.astype(float)
        mat_Z = mat_Z.replace([np.inf, -np.inf], np.nan)
        mat_Z = mat_Z.dropna(axis=0, how="all")
        mat_Z = mat_Z.dropna(axis=1, how="all")

        n = min(mat_Z.shape[0], mat_Z.shape[1])
        mat_Z.values[np.arange(n), np.arange(n)] = np.nan

        vals = mat_Z.to_numpy()

        norm = TwoSlopeNorm(vmin=np.nanmin(vals), 
                            vcenter=0, 
                            vmax=np.nanmax(vals))

        cmap = plt.cm.coolwarm.copy()
        cmap.set_bad(color="black")

        im = ax.imshow(
            mat_Z.to_numpy(),
            aspect="equal",
            cmap=cmap,
            norm=norm
        )

        ax.set_xticks(np.arange(mat_Z.shape[1]))
        ax.set_yticks(np.arange(mat_Z.shape[0]))
        ax.set_xticklabels(mat_Z.columns, rotation=90)
        ax.set_yticklabels(mat_Z.index)

        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label("Z-score")

        ax.set_title(f"Z-score heatmap with a general assortativity: {assort_Z.values[0]}")
        fig.tight_layout()

        if is_sample is not None:
            fig.savefig(
                saving_folder / f"heatmap_zscore_{patient}-{sample}.png",
                dpi=300,
                bbox_inches="tight"
            )
        else:
            fig.savefig(
                saving_folder / f"heatmap_zscore_{patient}.png",
                dpi=300,
                bbox_inches="tight"
            )
        plt.close(fig)