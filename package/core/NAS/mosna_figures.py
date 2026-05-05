from mosna import mosna
import matplotlib.pyplot as plt

def mosna_figures(niches, counts, save_dir, norm=None):
    if norm is not None:
        norm = '_' + norm

    n_phenotypes = counts.shape[1] if hasattr(counts, 'shape') else len(counts.columns)
    fig_height = max(8, n_phenotypes * 0.35)

    plt.figure(figsize=(20, fig_height))
    mosna.plot_niches_composition(counts=counts)
    plt.title("Niches Aggregated Composition", fontsize=14, pad=15)

    ax = plt.gca()
    ax.set_yticklabels(ax.get_yticklabels(), fontsize=8)
    ax.set_xticklabels(ax.get_xticklabels(), fontsize=10)

    plt.tight_layout()
    plt.savefig(save_dir / f"Niches_Aggregated_Composition{norm}.png", dpi=300, bbox_inches='tight')
    plt.close()


    plt.figure(figsize=(20, 8))
    mosna.plot_niches_histogram(niches)
    plt.title('Niches histogram')
    plt.tight_layout()
    plt.savefig(save_dir / "Niches_Histogram.png", dpi=300, bbox_inches='tight')
    plt.close()