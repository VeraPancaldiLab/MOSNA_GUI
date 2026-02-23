from ...utils.read_extension import get_opener

def assert_file_for_tysserand(file, config, extension):
    opener = get_opener(extension)
    df = opener(file)

    assert config["X coordinates column"] in df.columns, f'{config["X coordinates column"]} are not {df}'
    assert config["Y coordinates column"] in df.columns, f'{config["Y coordinates column"]} are not {df}'
    assert config["Phenotype column"] in df.columns, f'{config["Phenotype column"]} are not in {df}'
    assert config["Patient column name"] in file.stem, f'{config["Patient column name"]} are not present in this file name : {file}'
    assert config["Sample column name"] in file.stem, f'{config["Sample column name"]} are not present in this file name : {file}'