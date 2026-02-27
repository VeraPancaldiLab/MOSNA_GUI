#!/usr/bin/env bash
set -euo pipefail

source "$(conda info --base)/etc/profile.d/conda.sh"

conda create -y -n mosna-GUI -c conda-forge python=3.10 scanpy
conda activate mosna-GUI
conda install -y -c conda-forge "scipy==1.13" "lifelines<0.28" pyside6 pyyaml

conda install -y -c conda-forge ipykernel ipywidgets markdown

pushd mosna-package
pip install -e .
popd

