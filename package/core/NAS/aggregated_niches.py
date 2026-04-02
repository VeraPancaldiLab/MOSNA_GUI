import pandas as pd
from mosna import mosna
from package.utils.emit_qt_progress import emit_qt_progress, emit_qt_info
from package.core.NAS.merge_niche_pheno import merge_niche_pheno
from package.core.NAS.mosna_figures import mosna_figures

def aggregated_niches(method, net_dir, save_dir, temp_dir ,pheno_col, uniq_phenotype, stat_funcs, stat_names, id_level_1, id_level_2, 
                     reducer_type, clusterer_type, n_neighbors, metric, n_clusters, resolution, min_dist, dim_clust, 
                     min_cluster_size, k_cluster, normalize):
    
    emit_qt_info("[PROCESS] Spatial Omic Features for all networks")
    emit_qt_progress(0,3, "[PROCESS] Niches Analysis")
    if (temp_dir / 'var_aggreg.parquet').exists():
        var_aggreg = pd.read_parquet(temp_dir / 'var_aggreg.parquet')
    else:
        var_aggreg = mosna.compute_spatial_omic_features_all_networks(
            method=method,
            net_dir=net_dir,
            nodes_dir=net_dir,
            edges_dir=net_dir,
            attributes_col=pheno_col,
            use_attributes=uniq_phenotype, 
            make_onehot=True,
            stat_funcs=stat_funcs,
            stat_names=stat_names,
            id_level_1=id_level_1,
            id_level_2=id_level_2,
            parallel_groups='max',
            memory_limit='max',
            save_intermediate_results=False, 
            dir_save_interm=None,
            verbose=0,
        )
        var_aggreg.to_parquet(temp_dir / "var_aggreg.parquet")

    emit_qt_progress(1,3, "[PROCESS] Niches Analysis")

    emit_qt_info("[PROCESS] Reduction and Clustering of Spatial Niches")
    cluster_labels, _, _, _ = mosna.get_clusterer(
        data=var_aggreg.values,
        data_dir=save_dir,
        reducer_type=reducer_type,
        clusterer_type=clusterer_type,
        n_neighbors=n_neighbors,
        metric=metric,
        n_clusters=n_clusters,
        resolution=resolution,
        min_dist=min_dist,
        dim_clust=dim_clust,
        min_cluster_size=min_cluster_size,
        use_gpu=False,
        k_cluster=k_cluster,
        verbose=0,
    )
    emit_qt_progress(2,3, "[PROCESS] Niches Analysis")

    cell_types = merge_niche_pheno(net_dir, pheno_col, cluster_labels)

    emit_qt_info("[PROCESS] Generate Niches Composition")
    if normalize == 'all':
        for normalization in ['total', 'niche', 'obs', 'clr', 'niche&obs']:
            counts = mosna.make_niches_composition(
                    var=cell_types,
                    niches=cluster_labels,
                    var_label=pheno_col,
                    normalize=normalization
            )
            save_dir_norm = save_dir / f'{normalization}'
            save_dir_norm.mkdir(exist_ok=True, parents=True)
            mosna_figures(cluster_labels, counts, save_dir_norm)
    else:
        counts = mosna.make_niches_composition(
                    var=cell_types,
                    niches=cluster_labels,
                    var_label=pheno_col,
                    normalize=normalize
        )
        mosna_figures(cluster_labels, counts, save_dir)
    emit_qt_progress(3,3, "[PROCESS] Niches Analysis")