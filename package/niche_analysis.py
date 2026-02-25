import pandas as pd
from pathlib import Path

from package.utils.read_config import get_config, get_arguments
from package.utils.assert_params import assert_params


from mosna import mosna

def main():

    ### --- PRE-PROCESS --- ###

    analyse = "Niche Analysis"

    config_path, working_dir = get_arguments()
    config = get_config(config_path)[analyse]
    working_dir = Path(working_dir)

    assert_params(analyse, config)

    with_aggregation = config["Aggregated nodes"]
    per_sample = config['Per sample']

    ### --- PROCESS --- ###
    if with_aggregation:


        save_dir = working_dir / "Output/Niche Analysis/Aggregation"
        save_dir.mkdir(exist_ok=True, parents=True)
        uniq_phenotype = 
        kwargs = {
            "method": config.get("method", "NAS"),
            "net_dir": config['Network directory'],
            "save_dir": save_dir,
            "pheno_col": config["Phenotype column"], 
            "uniq_phenotype": uniq_phenotype,   
            "stat_funcs": config.get("stat_funcs", "default"),
            "stat_names": config.get("stat_names", "default"),
            "id_level_1": config.get("Patient column name", "patient"),
            "id_level_2": config.get("Sample column name:", "sample"),

            # Clustering / réduction
            "reducer_type": config["Aggregated nodes"].get("reducer_type", "umap"),
            "clusterer_type": config["Aggregated nodes"].get("clusterer_type", "leiden"),
            "n_neighbors": int(config["Aggregated nodes"].get("n_neighbors", 15)),
            "metric": config["Aggregated nodes"].get("metric", "euclidean"),
            "n_clusters": int(config["Aggregated nodes"].get("n_clusters", 15)),
            "resolution": float(config["Aggregated nodes"].get("resolution", 0.005)),
            "min_dist": float(config["Aggregated nodes"].get("min_dist", 0.0)),
            "dim_clust": int(config["Aggregated nodes"].get("dim_clust", 2)),
            "min_cluster_size": float(config["Aggregated nodes"].get("min_cluster_size", 0.001)),
            "k_cluster": int(config["Aggregated nodes"].get("k_cluster", 8)),

            # Normalisation composition niches
            "normalize": config["Aggregated nodes"].get("normalize", "total"),
        }
        from package.core.NAS.aggregated_niches import aggregated_niches

        aggregated_niches(**kwargs)

    elif per_sample:

        save_dir = save_dir = working_dir / "Output/Niche Analysis/Per sample"
        save_dir.mkdir(exist_ok=True, parents=True)
        uniq_phenotype = 

        kwargs = {
            "method": config.get("method", "NAS"),
            "net_dir": config['Network directory'],
            "save_dir": save_dir,
            "pheno_col": config["Phenotype column"], 
            "uniq_phenotype": uniq_phenotype,    
            "stat_funcs": config.get("stat_funcs", "default"),
            "stat_names": config.get("stat_names", "default"),
            "id_level_1": config.get("Patient column name", "patient"),
            "id_level_2": config.get("Sample column name:", "sample"),

            # Clustering / réduction
            "reducer_type": config["Per sample"].get("reducer_type", "umap"),
            "clusterer_type": config["Per sample"].get("clusterer_type", "leiden"),
            "n_neighbors": int(config["Per sample"].get("n_neighbors", 15)),
            "metric": config["Per sample"].get("metric", "euclidean"),
            "n_clusters": int(config["Per sample"].get("n_clusters", 15)),
            "resolution": float(config["Per sample"].get("resolution", 0.005)),
            "min_dist": float(config["Per sample"].get("min_dist", 0.0)),
            "dim_clust": int(config["Per sample"].get("dim_clust", 2)),
            "min_cluster_size": float(config["Per sample"].get("min_cluster_size", 0.001)),
            "k_cluster": int(config["Per sample"].get("k_cluster", 8)),

            # Normalisation composition niches
            "normalize": config["Per sample"].get("normalize", "total"),
        }
        from package.core.NAS.niches_per_sample import niches_per_sample

        niches_per_sample(**kwargs)
