# Mosna_analysis

- [Installation](#installation)
- [Tool](#tool)

Using mosna to analyse IMC picture with niches analysis         ( WORK IN PROGRESS )

## Installation

First clone this repo :

    git clone https://github.com/AlexCoul/mosna.git

To use mosna with GPU-compatible libraries, you can try:

    conda create --solver=libmamba -n mosna-gpu -c rapidsai -c conda-forge -c nvidia -c pytorch rapids=23.04.01 python=3.10 cuda-version=11.2 pytorch==1.12.1 torchvision==0.13.1 torchaudio==0.12.1 scanpy
    conda activate mosna-gpu

without GPU you can do:

    conda create --solver=libmamba -n mosna -c conda-forge python=3.10 scanpy
    conda activate mosna

then do:

    pip install ipykernel ipywidgets
    pip install tysserand

then cd /path/to/mosna_benchmark/

    pip install -e .
    pip install scipy==1.13

## Tool

