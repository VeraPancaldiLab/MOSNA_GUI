import numpy as np
from mosna import mosna

def plot_embedding(embedding_path, cluster_labels, save_dir, cluster_params):

    embedding = np.load(embedding_path)

    mosna.plot_clusters(embedding,
                        cluster_labels,
                        save_dir,
                        cluster_params)
