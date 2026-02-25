import pandas as pd

def build_index(net_dir, id_level_1 ,id_level_2, extension):
    data_index = []
    if id_level_2 is not None:
        edges_files = sorted(net_dir.glob(f"edges_{id_level_1}-*_{id_level_2}-*.{extension}"))
        for file in edges_files:
            patient, sample = file.stem.split("_")[1:]
            patient = patient.split('-')[1]
            sample = sample.split('-')[1]

            data_index.append((patient, sample))
    else:
        edges_files = sorted(net_dir.glob(f"edges_{id_level_1}-*.{extension}"))
        for file in edges_files:
            patient = file.stem.split("-")[1]
            data_index.append(patient)
    
    return data_index
