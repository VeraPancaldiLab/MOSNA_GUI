from mosna import mosna
import matplotlib.pyplot as plt

def mosna_figures(niches, counts, save_dir):

    plt.figure(figsize=(20, 8))
    mosna.plot_niches_composition(counts=counts)
    plt.title("Niches Aggregated Composition")
    plt.tight_layout()
    plt.savefig(save_dir / "Niches_Aggregated_Composition.png", dpi=600)
    plt.close()


    plt.figure(figsize=(20, 8))
    mosna.plot_niches_histogram(niches)
    plt.title('Niches histogram')
    plt.tight_layout()
    plt.savefig(save_dir / "Niches_Histogram.png", dpi=600)
    plt.close()