# Mosna_analysis

- [Installation](#installation)
- [Tool](#tool)
    - [Step 1](#step-1-pre-processing)
    - [Step 2](#step-2-draw-tysserand-spatial-networks)
    - [Step 3](#step-3-generate-assortativity)
    - [Step 4](#step-4-plot-niches-analysis)
- [Exemple of Using](#exemple-of-using)
    - [Tysserand Network](#tysserand-network)
    - [Assortativity](#assortativity)
    - [Niches Composition](#niches-composition)

The purpose of this tool is to facilitate the using of MOSNA and Tysserand, two package made by PancaldiLAB to build spatial networks and to analyse them with statistics.
This tool provide a GUI to generate easily the networks and other spatial analyse.   

# Installation

First clone this repo :

    git clone https://github.com/AlexCoul/mosna.git

## To install only mosna lib and ohter dependancies you can make the following steps :

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

## To install directly my env you can make the following steps :

clone my repo and run this scrip : 

    cd Mosna_analysis
    conda env create -f mosna.yml -n mosna
    conda activate mosna
    cd mosna
    pip install -e .
    pip install scipy==1.13

## package installation for Ubuntu

    sudo apt install jq

# Tool

## Tool architecture 

You must follow this architecture provided to make it works.

## Graphic Interface to control your using

before to be able to obtain your tysserand network you must complete first all parameters for the different, this parameters will be explained right after:

![Mon Image](images/GUI.png)

### Step 1: Pre-processing

The pre-processing step is required to generate temp file needed for the following steps. 4 files will be created by type of data (IF's panel and IMC)

- cell_pos_pheno = Phenotypes and position are present in this file for each cell sort by sample and patient
- cell_pos = the same thing but without phenotypes
- sample_cell = patient and sample for each cell
- markers = all biomarkers for each cell sort by sample and patient

### Step 2: Draw Tysserand Spatial Networks

This step generate Tysserand networks for each patient/sample

### Step 3: Generate Assortativity



### Step 4: Plot Niches Analysis

# Exemple of using

In this part we will provide an example of this tool step by step

## Tysserand Network 

In this all part, different spatial networks plots are present

### IMC tysserand network
![Mon Image](images/network/IMC_Tysserand_network_A_ROI_01.png)

### IF first panel tysserand network
![Mon Image](images/network/IF_C1_Tysserand_network_C_layer_1.png)

### IF second panel tysserand network
![Mon Image](images/network/IF_C2_Tysserand_network_B_layer_3.png)

## Assortativity

In this part, all different assortativity plots are present

### IF assortativity for one patient/sample
![Mon Image](images/assort/assortativity_z-scored_patient-A_layer-1.png)

### IMC assortativity for one patient/sample
![mon image](images/assort/assortativity_z-scored_patient-A_ROI-01.png)

### IF assortativity aggregated by mean
![Mon Image](images/assort/assortativity_z-scored_IF_C1.png)
![Mon Image](images/assort/assortativity_z-scored_IF_C2.png)

### IMC assortativity aggregated by mean
![Mon Image](images/assort/assortativity_z-scored_IMC.png)
In this image only the most important z-score (absolute values) are present to keep this plot visible

Here the real barplot with all tuples of phenotypes.
![Mon Image](images/assort/Mean_Std_Assortativity_z-scored_IMC.png)

## Niches composition

In this part, all different niche analysis plots are present

### IF aggregated nodes
![Mon image](images/niche/IF_C2_niche_composition_niche.png)

### IMC aggregated nodes
![Mon image](images/niche/IMC_niche_composition_niche.png)

### IF for one patient/sample
![Mon image](images/niche/IF_netniche_G1C2.png)

and the associated network colored by niche
![Mon image](images/niche/IF_netniche_G1C2.png)

### IMC for one patient/sample
![Mon image](images/niche/IMCnicheA1.png)

and the associated network colored by niche
![Mon image](images/niche/IMC_netnicheA1.png)
