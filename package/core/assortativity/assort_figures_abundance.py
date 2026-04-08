import matplotlib.pyplot as plt

def assort_figures_abundance(net_stat, save_dir):
    plot_df = net_stat.loc[:, net_stat.columns.str.startswith('% ')]
    plot_df = plot_df.div(plot_df.sum(axis=1), axis=0)
    plot_df.columns = plot_df.columns.str.replace(r'^%\s*', '', regex=True)
    
    ax = plot_df.plot(
    kind='bar',
    stacked=True,
    figsize=(12, 6),
    width=0.8
    )

    ax.set_xlabel('Sample')
    ax.set_ylabel('Proportion')
    ax.set_title('Abondance relative des types cellulaires par sample')
    ax.legend(title='Cell type', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(save_dir / "abundance.png", dpi=300)
    plt.close()

    return