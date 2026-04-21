import re

def find_sample(net_dir, extension, patient_column_name, sample_column_name=None):
    if sample_column_name is None:
        pattern = re.compile(
            rf"^nodes_{re.escape(patient_column_name)}-[^_]+\.{re.escape(extension)}$"
        )
    else:
        pattern = re.compile(
            rf"^nodes_{re.escape(patient_column_name)}-[^_]+_{re.escape(sample_column_name)}-[^_]+\.{re.escape(extension)}$"
        )

    return sorted(
        path for path in net_dir.iterdir()
        if path.is_file() and pattern.match(path.name)
    )