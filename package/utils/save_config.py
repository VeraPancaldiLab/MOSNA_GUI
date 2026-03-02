import numpy as np
from pathlib import Path
import json

def save_config(save_path, config):

    def convert(obj):
        if isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        if isinstance(obj, Path):
            return str(obj)
        raise TypeError

    if config['Processing method'] == "Aggregated nodes":
        config.pop("Aggregated nodes", None)
        results = config
    elif config['Processing method'] == "Per sample":
        results = config
        config.pop("Per sample", None)
    else:
        results = config

    with (save_path / "parameters.json").open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False, default=convert)
