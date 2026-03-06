import pandas as pd
from pathlib import Path
import shutil

from package.utils.read_config import get_config, get_arguments
from package.utils.assert_params import assert_params
from package.core.NAS.find_all_pheno import find_all_pheno
from package.utils.convert_net_dir import convert_net_dir
from package.core.NAS.assert_net_niches import assert_net_niches
from package.utils.emit_qt_progress import emit_qt_info
from package.utils.save_config import save_config
from package.core.tysserand.draw_tysserand_niches import draw_tysserand_niches

from mosna import mosna

def main():

    ############################## --- PRE-PROCESS --- ####################################
    analyse = "Niche Analysis"

    config_path, working_dir = get_arguments()
    config = get_config(config_path)[analyse]
    working_dir = Path(working_dir)
    temp_folder = working_dir / "temp/net_dir_mosna"

    assert_params(analyse, config)

    with_aggregation = per_sample = False
    if config["Processing method"] == 'Aggregated nodes':
        with_aggregation = True
    elif config["Processing method"] == 'Per sample':
        per_sample = True
    else:
        per_sample = with_aggregation = True

    

    if config['Network directory'] == 'Default':
        net_dir = temp_folder
        extension = 'parquet'
        assert_net_niches(net_dir, 
                        config["Patient column name"],
                        config.get("Sample column name", "sample"),
                        extension,
                        config["Phenotype column"])
    else:
        extension = config['Extension']
        net_dir = Path(working_dir).expanduser().resolve() / Path(config['Network directory']).expanduser()
        assert_net_niches(net_dir, 
                        config["Patient column name"],
                        config.get("Sample column name", "sample"),
                        extension,
                        config["Phenotype column"])

        if extension != "parquet":
            convert_net_dir(net_dir, config["Patient column name"], config.get("Sample column name", "sample"), extension, temp_folder)
            extension = 'parquet'
            net_dir = temp_folder

    emit_qt_info('[INFO] Verification and Convertion of the files')

    uniq_phenotype = find_all_pheno(net_dir,
                                    extension,
                                    config["Phenotype column"],
                                    config["Patient column name"],
                                    config.get("Sample column name", "sample"))
    
    emit_qt_info('[INFO] Phenotypes for all sample found')
    ############################## --- PROCESS --- #######################################

    if with_aggregation:

        save_dir = working_dir / "Niche_Analysis/Aggregation" / config['Saving directory']
        save_dir.mkdir(exist_ok=True, parents=True)
        kwargs = {
            "method": config.get("method", "NAS"),
            "net_dir": net_dir,
            "save_dir": save_dir,
            "temp_dir": temp_folder,
            "pheno_col": config["Phenotype column"], 
            "uniq_phenotype": uniq_phenotype,   
            "stat_funcs": config.get("stat_funcs", "default"),
            "stat_names": config.get("stat_names", "default"),
            "id_level_1": config.get("Patient column name", "patient"),
            "id_level_2": config.get("Sample column name", "sample"),

            ################ Clustering / réduction
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

            ################ Normalisation composition niches
            "normalize": config["Aggregated nodes"].get("normalize", "total"),
        }
        from package.core.NAS.aggregated_niches import aggregated_niches
        aggregated_niches(**kwargs)

        emit_qt_info('[INFO] Niches found for aggregated nodes')

        for path in save_dir.glob("reducer-umap*"):
            if path.is_dir():
                shutil.rmtree(path)
        save_config(save_dir, config)

        X, Y = get_config(config_path)[analyse]['X coordinates column'], get_config(config_path)['Tysserand']['Y coordinates column']
        
        if X is None or Y is None:
            draw_tysserand_niches(net_dir, save_dir, kwargs['id_level_1'], kwargs['id_level_2'], X, Y)

    elif per_sample:

        save_dir = save_dir = working_dir / "Niche_Analysis/Per_sample" / config['Saving directory']
        save_dir.mkdir(exist_ok=True, parents=True)
        kwargs = {
            "method": config.get("method", "NAS"),
            "net_dir": net_dir,
            "save_dir": save_dir,
            "temp_dir": temp_folder,
            "pheno_col": config["Phenotype column"], 
            "uniq_phenotype": uniq_phenotype,    
            "stat_funcs": config.get("stat_funcs", "default"),
            "stat_names": config.get("stat_names", "default"),
            "id_level_1": config.get("Patient column name", "patient"),
            "id_level_2": config.get("Sample column name", "sample"),

            ############# Clustering / réduction
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

            ########## Normalisation composition niches
            "normalize": config["Per sample"].get("normalize", "total"),
        }
        from package.core.NAS.niches_per_sample import niches_per_sample
        niches_per_sample(**kwargs)

        emit_qt_info('[INFO] Niches found for each samples')

        for path in save_dir.glob("reducer-umap*"):
            if path.is_dir():
                shutil.rmtree(path)
        save_config(save_dir, config)

        X, Y = get_config(config_path)[analyse]['X coordinates column'], get_config(config_path)['Tysserand']['Y coordinates column']

        if X is None or Y is None:
            draw_tysserand_niches(net_dir, save_dir, kwargs['id_level_1'], kwargs['id_level_2'], X, Y)
        
        

if __name__ == '__main__':
    main()