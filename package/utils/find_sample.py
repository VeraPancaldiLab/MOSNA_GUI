from pathlib import Path

def find_sample(net_dir, extension, patient_colmun_name, sample_colmun_name=None):
    if sample_colmun_name is None:
        nodes_files = sorted(net_dir.glob(f"nodes_{patient_colmun_name}-*.{extension}"))
    else:
        nodes_files = sorted(net_dir.glob(f"nodes_{patient_colmun_name}-*_{sample_colmun_name}-*.{extension}"))
    return nodes_files