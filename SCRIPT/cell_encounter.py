import pandas as pd
import yaml, os, argparse
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

def get_arguments():

    parser = argparse.ArgumentParser(description = "Draw tysserand for IMC / IF")
    parser.add_argument('--file', type = str, required=True, help = "config file")
    args = parser.parse_args()

    return args.file

def get_config(config_path):
        
    base_path = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base_path, config_path)

    if not os.path.exists(full_path):
        raise FileNotFoundError(f"❌ Config file not found : {full_path}")
    
    with open(full_path, 'r') as f:
        config = yaml.safe_load(f)
    return config

def import_data(dir):
    IMC_pos = pd.read_parquet(Path(dir) / "IMC_cell_pos.parquet")
    IF_pos = pd.read_parquet(Path(dir) / "IMC_cell_pos.parquet")
    return IMC_pos, IF_pos

def gaussian_2d(x, y, x0, y0, sigma_x, sigma_y, A=1):
    return A * np.exp(-(((x - x0) ** 2) / (2 * sigma_x ** 2) + ((y - y0) ** 2) / (2 * sigma_y ** 2)))

def main():
    config_path = get_arguments()
    config_file = get_config(config_path)
    IMC_pos, IF_pos = import_data(config_file['standard']['output_dir'])



    # Paramètres de la gaussienne
    x0, y0 = 50, 50       # Centre de la gaussienne
    sigma_x, sigma_y = 10, 15
    amplitude = 1

    # Grille de calcul
    x = np.linspace(0, 100, 200)
    y = np.linspace(0, 100, 200)
    X, Y = np.meshgrid(x, y)

    Z = gaussian_2d(X, Y, x0, y0, sigma_x, sigma_y, A=amplitude)

    # Affichage
    plt.figure(figsize=(6, 5))
    plt.contourf(X, Y, Z, levels=50, cmap='viridis')
    plt.colorbar(label='Amplitude')
    plt.scatter(x0, y0, color='red', label='Centre', s=100)
    plt.title("Gaussienne 2D centrée en ({}, {})".format(x0, y0))
    plt.xlabel("x")
    plt.ylabel("y")
    plt.legend()
    plt.axis('equal')
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()