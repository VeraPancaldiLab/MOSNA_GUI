import yaml
import argparse

def get_arguments():
    parser = argparse.ArgumentParser(description = "Get all arguments")
    parser.add_argument('--file', type = str, required=True, help = "config file")
    parser.add_argument("--working_dir", required=True, help="Working directory chosen in the GUI")
    args = parser.parse_args()
    return args.file, args.working_dir

def get_config(config_path):
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config