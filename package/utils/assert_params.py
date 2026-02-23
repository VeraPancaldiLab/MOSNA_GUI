

def assert_params(analyse_to_perform, config):
    if analyse_to_perform == "Tysserand":
        assert isinstance(config["Nodes directory"],str), "Nodes directory parameter must be str"
        assert isinstance(config["X coordinates column"],str), "X coordinates column parameter must be str"
        assert isinstance(config["Y coordinates column"],str), "Y coordinates column parameter must be str"
        assert isinstance(config["Phenotype column"],str), "Phenotype column parameter must be str"
        assert isinstance(config["Edges method"],str), "Edges method parameter must be str"
        assert isinstance(config["Patient column name"],str), "Patient column name parameter must be str"
        assert isinstance(config["Sample column name"],str), "Sample column name parameter must be str"
        assert isinstance(config['Extension'],str), "Extension parameter must be str"
        assert isinstance(config['CPU'], int), "CPU parameter must be int"
        assert isinstance(config['Min neighbors'], int), "CPU parameter must be int"

    elif analyse_to_perform == "Assortativity":
        assert isinstance(config["Phenotype column"],str), "Phenotype column parameter must be str"
        assert isinstance(config["Patient_ID"],str), "Patient_ID parameter must be str"
        assert isinstance(config["Sample_ID"],str), "Sample_ID parameter must be str"
        assert isinstance(config["Extension"],str), "Extension parameter must be str"
        assert isinstance(config["Index"],str), "Index parameter must be str"

    elif analyse_to_perform == "NAS":
        print(0)

    return None