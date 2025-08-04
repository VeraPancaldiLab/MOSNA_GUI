#!/bin/bash
set -e 
mkdir -p OUTPUT_DATA
mkdir -p temp/description

# === Installation de dépendances système ===

printf "\n[PROCESS] System Dependancies Installation (sudo needed)\t\t\n"
sudo apt install -y \
    build-essential \
    libglib2.0-0 \
    libgl1 \
    libgomp1 \
    libxcb-cursor0 \
    libhdf5-dev \
    libzstd1 \
    libxml2 \
    libffi-dev \
    libxcb-xinerama0 \
    jq
sudo snap install yq

# === Detection de Conda ===

printf "\n[INFO] Conda Verification\t\t"
if ! command -v conda &> /dev/null; then
    echo "[ERROR] Conda is not installed. Please install Miniconda or Anaconda before continuing"
    exit 1
fi
echo "DONE"

# === Détection de GPU NVIDIA ===

read -p "Do you want to install MOSNA with a GPU using or not | (y/n): " HAS_GPU
printf "\n[PROCESS] Conda Env generation\t\t\n"
if [[ "$HAS_GPU" == "y" || "$HAS_GPU" == "Y" ]]; then
    conda create --yes -n mosna-gpu -c rapidsai -c conda-forge -c nvidia -c pytorch \
        rapids=23.04.01 python=3.10 cuda-version=11.2 \
        pytorch==1.12.1 torchvision==0.13.1 \
        statsmodels=0.14.4 torchaudio==0.12.1 scanpy
    ENV_NAME=mosna-gpu
else
    conda create --yes -n mosna -c conda-forge python=3.10 scanpy statsmodels=0.14.4
    ENV_NAME=mosna
fi

# === Activation (à rappeler manuellement dans la session actuelle) ===

printf "\n[PROCESS] Environnement update by using 'mosna.yml'\t\t\n"
eval "$(conda shell.bash hook)"
conda activate "$ENV_NAME"
conda env update -n "$ENV_NAME" -f mosna.yml 

# === Installation du package local mosna===

if [ -d "./mosna" ]; then
    echo "[INFO] Mosna already installed"
else
    printf "\n[PROCESS] MOSNA package Installation\t\t\n"
    git clone https://github.com/AlexCoul/mosna.git
fi
cd mosna
pip install -e . 
cd ..

# === Installation des dépendances Python supplémentaires ===
printf "\n[PROCESS] Installation of additional Python packages\t\t\n"
pip install ipykernel ipywidgets napari tysserand
pip install scipy==1.13

conda deactivate
echo "Complete installation"
echo "Activate your environment with : conda activate $ENV_NAME"
