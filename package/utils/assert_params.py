

def assert_params(analyse_to_perform, config):
    if analyse_to_perform == "Tysserand":
        assert isinstance(config["Nodes directory"],str), "Nodes directory parameter must be str"
        assert isinstance(config["X coordinates column"],str), "X coordinates column parameter must be str"
        assert isinstance(config["Y coordinates column"],str), "Y coordinates column parameter must be str"
        assert isinstance(config["Phenotype column"],str), "Phenotype column parameter must be str"
        assert isinstance(config["Edges method"],str), "Edges method parameter must be str"
        assert isinstance(config["Patient column name"],str), "Patient column name parameter must be str"
        assert isinstance(config["Sample column name"],str) or isinstance(config['Sample column name'], type(None)), "Sample column name parameter must be str or None"
        assert isinstance(config['Extension'],str), "Extension parameter must be str"
        assert isinstance(config['CPU'], int), "CPU parameter must be int"
        assert isinstance(config['Min neighbors'], int), "CPU parameter must be int"

    elif analyse_to_perform == "Assortativity":
        assert isinstance(config["Phenotype column"],str), "Phenotype column parameter must be str"
        assert isinstance(config["Patient column name"],str), "Patient column name parameter must be str"
        assert isinstance(config["Sample column name"],str) or isinstance(config['Sample column name'], type(None)), "Sample column name parameter must be str"
        assert isinstance(config["Extension"],str), "Extension parameter must be str"
        assert config["Index"] is None or isinstance(config["Index"],str), "Index parameter must be str"
        assert isinstance(config['Number of shuffle'],int), 'Number of shuffle must be an integer'

    elif analyse_to_perform == "NAS":
        import re

        assert isinstance(config['Saving directory'], str), 'Saving directory need to be a str'
        assert re.fullmatch(r"^[A-Za-z0-9_\- ]+$", config["Saving directory"]), 'The saving folder name is not valid'

        assert isinstance(config["Column to aggregate"],(str, list)), "Column to aggregate parameter must be str or list"
        assert isinstance(config["Patient column name"],str), "Patient column name parameter must be str"
        assert isinstance(config["Sample column name"],str) or isinstance(config['Sample column name'], type(None)), "Sample column name parameter must be str"
        assert isinstance(config["Extension"],str), "Extension parameter must be str"
        assert isinstance(config["Processing method"], str), "Processing method must be str"
        assert isinstance(config["Niches method"], str), "Niches method must be str"

        if config["Processing method"] == "Aggregated nodes":
            verification_list = ['Aggregated nodes']
        elif config["Processing method"] == "Per sample":
            verification_list = ['Per sample']
        else:
            verification_list = ["Aggregated nodes", 'Per sample']

        for verification_process in verification_list:
            assert isinstance(config[verification_process]["order"], str), "order must be str"
            assert isinstance(config[verification_process]['stat_funcs'],list), "stat_funcs must be list"
            assert isinstance(config[verification_process]["stat_names"],list), "stat_names must be list"
            assert isinstance(config[verification_process]["clusterer_type"], str), "clusterer_type must be str"
            assert config[verification_process]["clusterer_type"] in ["leiden","ecg",'spectral',"gmm"]

            assert isinstance(config[verification_process]["n_clusters"], int), "n_clusters must be int"
            assert isinstance(config[verification_process]["reducer_type"], str), 'reducer type must be str'
            assert config[verification_process]["reducer_type"] in ['umap']

            assert isinstance(config[verification_process]["metric"], str), "metric must be str"
            assert config[verification_process]["metric"] in ['manhattan', 'euclidean', 'cosine']

            assert isinstance(config[verification_process]["resolution"], float), "resolution must be float"
            assert isinstance(config[verification_process]["n_neighbors"], int), "n_neighbors must be int"
            assert isinstance(config[verification_process]["min_dist"], float), "min_dist must be float"
            assert isinstance(config[verification_process]["dim_clust"], int), "dim_clust must be int"
            assert isinstance(config[verification_process]["min_cluster_size"], int), "min_cluster_size must be int"
            assert isinstance(config[verification_process]["k_cluster"], int), "k_cluster must be int"
            assert isinstance(config[verification_process]["normalize"], str), "normalize must be str"
            assert config[verification_process]["normalize"] in ['total', 'niche', 'obs', 'clr', 'niche&obs', 'all']

    return None