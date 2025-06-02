# Mosna_analysis

- [Installation](#installation)
- [Tool](#tool)
- [Tysserand Network](#tysserand-network)

The purpose of this tool is to facilitate the using of MOSNA and Tysserand, two package made by PancaldiLAB to build spatial networks and to analyse them with statistics.
This tool provide a GUI to generate easily the networks and other spatial analyse.   

## Installation

First clone this repo :

    git clone https://github.com/AlexCoul/mosna.git

### To install only mosna lib and ohter dependancies you can make the following steps :

To use mosna with GPU-compatible libraries, you can try:

    conda create --solver=libmamba -n mosna-gpu -c rapidsai -c conda-forge -c nvidia -c pytorch rapids=23.04.01 python=3.10 cuda-version=11.2 pytorch==1.12.1 torchvision==0.13.1 torchaudio==0.12.1 scanpy
    conda activate mosna-gpu

without GPU you can do:

    conda create --solver=libmamba -n mosna -c conda-forge python=3.10 scanpy
    conda activate mosna

then do:

    pip install ipykernel ipywidgets napari
    pip install tysserand

then cd /path/to/mosna_benchmark/

    pip install -e .
    pip install scipy==1.13

### To install directly my env you can make the following steps :

clone my repo and run this scrip : 

    cd Mosna_analysis
    conda env create -f mosna.yml -n mosna
    conda activate mosna
    cd mosna
    pip install -e .
    pip install scipy==1.13

### package installation for Ubuntu

    sudo apt install jq

## Tool

### Tool architecture 

You must follow this architecture provided to make it works.



before to be able to obtain your tysserand network you must complete first all parameters for the different, this parameters will be explained right after:

![Mon Image](images/GUI.png)

to have all tysserand networks of your IMC and IF csv files you must run this command:

    chmod u+x draw_tysserand.sh
    ./draw_tysserand.sh

## Tysserand Network

![Mon Image](images/IMC_Tysserand_network_A_ROI_01.png)

![Mon Image](images/IF_C1_Tysserand_network_C_layer_1.png)

![Mon Image](images/IF_C2_Tysserand_network_B_layer_3.png)