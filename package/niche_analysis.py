import pandas as pd
from pathlib import Path
import shutil
from tqdm.contrib.concurrent import process_map

from package.utils.read_config import get_config, get_arguments
from package.utils.assert_params import assert_params
from package.core.NAS.find_all_pheno import find_all_pheno
from package.utils.convert_net_dir import convert_net_dir
from package.core.NAS.assert_net_niches import assert_net_niches
from package.utils.emit_qt_progress import emit_qt_info
from package.utils.save_config import save_config
from package.utils.verif_cpu import verif_cpu
from package.core.tysserand.draw_per_sample import draw_per_sample
from package.utils.find_sample import find_sample
from package.core.tysserand.generate_cmap import generate_cmap

from mosna import mosna

def worker_draw_wrapper(args):
    result = worker_draw(args)
    return result

def worker_draw(args):
    return draw_per_sample(*args)

def main():

    ############################## --- PRE-PROCESS --- ####################################
    analyse = "Niche Analysis"

    config_path, working_dir = get_arguments()
    config = get_config(config_path)[analyse]
    working_dir = Path(working_dir)

    assert_params(analyse, config)

    with_aggregation = per_sample = False
    if config["Processing method"] == 'Aggregated nodes':
        with_aggregation = True
    elif config["Processing method"] == 'Per sample':
        per_sample = True
    else:
        per_sample = with_aggregation = True


    if config['Network directory'] == 'Default':
        extension = 'parquet'
        net_dir = working_dir / "temp/net_dir_mosna"
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
            convert_net_dir(net_dir, config["Patient column name"], config.get("Sample column name", "sample"), extension, net_dir)
            extension = 'parquet'

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
            "temp_dir": net_dir,
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

        X, Y = config['X coordinates column for niches'], config['Y coordinates column for niches']
        
        if X is not None and Y is not None:
            c_map = generate_cmap(net_dir, 'niche', 'parquet', kwargs['id_level_1'], kwargs['id_level_2'])
            files = find_sample(net_dir, 'parquet', kwargs['id_level_1'], kwargs['id_level_2'])
            cpu_max = verif_cpu(config['CPU'], len(files))

            save_dir = save_dir / 'Tysserand_Network_Niches'
            save_dir.mkdir(exist_ok=True, parents=True)

            args_list = [(
                patient_sample,
                X,
                Y,
                'niches',
                c_map,
                'delaunay',3,
                save_dir,'None',
                kwargs['id_level_1'],kwargs['id_level_2'],
                'parquet')for patient_sample in files]
            
            process_map(
                worker_draw_wrapper,
                args_list,
                max_workers=cpu_max,
                desc=" └─ [MULTI PROCESS] Processing file",
                chunksize=1
            )

    elif per_sample:

        save_dir = save_dir = working_dir / "Niche_Analysis/Per_sample" / config['Saving directory']
        save_dir.mkdir(exist_ok=True, parents=True)
        kwargs = {
            "method": config.get("method", "NAS"),
            "net_dir": net_dir,
            "save_dir": save_dir,
            "temp_dir": net_dir,
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

        X, Y = config['X coordinates column for niches'], config['Y coordinates column for niches']

        if X is not None and Y is not None:
            pass

if __name__ == '__main__':
    main()