import matplotlib.pyplot as plt
import numpy as np
from ...utils.style_figures import apply_style
apply_style()

def assort_figures_abundance(net_stat, save_dir):

    plot_df = net_stat.loc[:, net_stat.columns.str.startswith('% ')]
    plot_df = plot_df.div(plot_df.sum(axis=1), axis=0)

    fig, ax = plt.subplots(figsize=(18, 9))

    palettes = [plt.cm.tab20(np.linspace(0, 1, 20))]
    
    n_colors = plot_df.shape[1]
    if n_colors > 20:
        palettes.append(plt.cm.tab20b(np.linspace(0, 1, 20)))
    if n_colors > 40:
        palettes.append(plt.cm.tab20c(np.linspace(0, 1, 20)))

    all_colors = np.vstack(palettes)
    colors = all_colors[:n_colors]

    plot_df.plot(
        kind='bar',
        stacked=True,
        width=0.8,
        ax=ax,
        color=colors
    )

    ax.set_xlabel('Sample', fontsize=20)
    ax.set_ylabel('Proportion', fontsize=20)
    ax.set_title('Abondance relative des types cellulaires par sample', fontsize=25)

    handles, labels = ax.get_legend_handles_labels()
    labels = [l[2:] for l in labels]
    ax.legend(
        handles[::-1],
        labels[::-1],
        title='Cell type',
        bbox_to_anchor=(1.02, 1),
        loc='upper left',
        fontsize=8,
        title_fontsize=12
    )

    plt.xticks(rotation=45, ha='right')
    fig.subplots_adjust(left=0.08, right=0.78, bottom=0.18, top=0.90)
    plt.savefig(save_dir / "abundance.png", dpi=300)
    plt.close()

    return