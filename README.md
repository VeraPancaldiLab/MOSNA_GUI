# Mosna_analysis

- [Installation](#installation)
- [Tool](#tool)
    - [Tool Architecture](#tool-architecture)
    - [GUI](#graphic-interface-to-control-your-using)
    - [Step 1](#step-1-pre-processing)
    - [Step 2](#step-2-draw-tysserand-spatial-networks)
    - [Step 3](#step-3-generate-assortativity)
    - [Step 4](#step-4-plot-niches-analysis)
    - [Step 5](#step-5-synthetic-spatial-network-generation-using-mrf-and-assortativity)
    - [Step 6](#step-6-remove-all-temporary-file-in-output_data-file)
- [Exemple of Using](#exemple-of-using)
    - [Tysserand Network](#tysserand-network)
    - [Assortativity](#assortativity)
    - [Niches Composition](#niches-composition)
    - [Network Generation](#synthetic-network-generation)

# Installation

First clone this repo :

    git clone https://github.com/AlexCoul/mosna.git

## To install only mosna lib and ohter dependancies you can make the following steps

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

## To install directly my env you can make the following steps

clone my repo and run this:

    chmod +x setup.sh
    ./setup.sh

# Tool

The purpose of this tool is to facilitate the using of MOSNA and Tysserand, two package made by PancaldiLAB to build spatial networks and to analyse them with statistics.
This tool provide a GUI to generate easily the networks and other spatial analyse.

  conda activate mosna
  python mosna_GUI.py

## Tool architecture 

You must follow this architecture provided to make it works:

![Mon Image](images/Tool_architecture.png)

## Graphic Interface to control your using

before to be able to obtain your tysserand network you must complete first all parameters for the different, this parameters will be explained right after:

![Mon Image](images/GUI.png)

## Step 1: Pre-processing

The pre-processing step is required to generate temp file needed for the following steps. 4 files will be created by type of data (IF's panel and IMC)

- cell_pos_pheno = Phenotypes and position are present in this file for each cell sort by sample and patient
- cell_pos = the same thing but without phenotypes
- sample_cell = patient and sample for each cell
- markers = all biomarkers for each cell sort by sample and patient

You must fill **General**, **IF_import** and **IMC_import** sections.

| Section     | Clé                   | Descripton        |
|-------------|-----------------------|-------------------|
|**General**  | silent                |                   |
|             | pheno_dir             |                   |
|             | phenograph            |                   |
|             | add_pheno             |                   |
|**IF_import**| present_in            |                   |
|             | directory_path        |                   |
|             | panel                 |                   |
|             | path_encoding_patient |                   |
|             | path_file_to_patient  |                   |
|             | columns_to_drop       |                   |
|             | layer_columns         |                   |
|             | patient_columns       |                   |
|             | marker_columns        |                   |
|             | cell_id_columns       |                   |
|             | spatial_columns       |                   |
|             | normalize_data        |                   |
|             | re_index              |                   |
|             | there_is_duplicata    |                   |
|**IMC_import**| present_in           |                   |
|             | directory_path        |                   |
|             | path_encoding_patient |                   |
|             | path_file_to_patient  |                   |
|             | columns_to_drop       |                   |
|             | layer_columns         |                   |
|             | patient_columns       |                   |
|             | marker_columns        |                   |
|             | cell_id_columns       |                   |
|             | spatial_columns       |                   |
|             | normalize_data        |                   |
|             | re_index              |                   |
|             | there_is_duplicata    |                   |

## Step 2: Draw Tysserand Spatial Networks

This step generate Tysserand networks for each patient/sample. You must fill **Tysserand** section.

| Clé                      | Description       |
|--------------------------|-------------------|
| IF_perform               |                   |
| panel                    |                   |
| IMC_perform              |                   |
| cpu                      |                   |
| k_neighbors_phenograph   |                   |
| primary_metric_phenograph|                   |
| method_tysserand         |                   |
| min_neighbors            |                   | 

## Step 3: Generate Assortativity

For this step you must fill **Assortativity** section. This step allow you to generate assortativity for each patient/sample networks and for an aggregate data of one type of data (all IF for one panel for exemple)

| Clé                   | Description       |
|-----------------------|-------------------|
|IF_perform             |                   |
|panel                  |                   |
|IMC_perform            |                   |
|perform_batch          |                   |
|perform_clr_transfo    |                   |

## Step 4: Plot Niches Analysis

In this step you must fill **NAS** section. This step will generate for you niches composition and all networks recolored by niche for each patient/sample and also the niche composition for aggregated nodes for all images of one type. 

| Clé                   | Description       |
|-----------------------|-------------------|
|method                 |                   |
|output_name_file       |                   |
|IMC_perform            |                   |
|IF_perform             |                   |
|panel                  |                   |
|node_aggregation       |                   | 
|perform_NAS_all_sample |                   |

And for each niche clustering and plotting (IF and IMC nodes aggregation, IF and IMC for each patient/sample):

**Niche clustering parameters:**

| Clé               | Description       |
|-------------------|-------------------|
| order             |                   |
| stat_funcs        |                   |
| stat_names        |                   |
| clusterer_type    |                   |
| n_clusters        |                   |
| reducer_type      |                   |
| metric            |                   |
| resolution        |                   |
| n_neighbors       |                   |
| min_dist          |                   |
| dim_clust         |                   |
| min_cluster_size  |                   |
| k_cluster         |                   |
| normalize         |                   |


## Step 5: Synthetic Spatial Network Generation using MRF and Assortativity

This repository implements a pipeline to generate **synthetic spatial tissue-like networks** representing cell phenotypes, using **assortativity constraints** and a **Markov Random Field (MRF)** model.

### 🧬 Overview

The pipeline creates a 2D tissue-like structure with cells (nodes), connected by spatial proximity (edges), and assigns phenotypes to each cell such that:

- **Phenotype-Phenotype assortativity** (given as Z-scores) is respected
- **Global phenotype proportions** are enforced with a tunable tolerance
- The final output includes:
  - A list of nodes with spatial coordinates and phenotypes
  - A list of spatial edges derived from Delaunay triangulation

### 🧩 Step-by-step Pipeline

### 1 - Generate Cell Positions

Cells are uniformly distributed in a 2D rectangular space

This simulates a homogeneous tissue environment.

### 2 - Build Spatial Edges via Delaunay Triangulation

Using **Delaunay**, edges are formed between spatial neighbors.

This provides biologically-plausible neighborhood relations.

### 3 - Initialize Cell Phenotypes

Each node is assigned a random phenotype from a predefined list of your choice

### 4 - Define the MRF Energy Function

The energy of the system is defined by the negative sum of Z-score interactions over edges:

```math
E = -\sum_{(i, j) \in \text{Edges}} Z_{y_i, y_j}
```

Where:
```math
- \( y_i \) and \( y_j \) are the phenotypes of neighboring cells
- \( Z_{y_i, y_j} \) is the Z-score measuring assortativity
```

### 5 - Gibbs Sampling to Minimize Energy

For each node, we re-sample its phenotype to minimize local energy:

For a candidate phenotype \( t \), we define:

```math
P(y_i = t) \propto \exp\left(-\sum_{j \in \mathcal{N}(i)} Z_{t, y_j}\right)
```

The sampling is repeated over `n_iter` iterations to reach equilibrium.

### 6 - Proportion Regularization

After convergence, we correct global proportions by inserting additional points (cells) with minimal impact on the energy:

For phenotype \( t \), the position \( x \) is selected to minimize:

```math
\Delta E(x, t) = -\sum_{j \in \mathcal{N}(x)} Z_{t, y_j}
```

A new cell is added if:

```python
abs(current_proportion[phenotype] - target_proportion[phenotype]) > tolerance_threshold
```

This step ensures final phenotype distributions match biological constraints.

## Step 6: Remove all temporary file in output_data file

## Exemple of using

In this part we will provide an example of this tool step by step

### Tysserand Network 

In this all part, different spatial networks plots are present

#### IMC tysserand network
![Mon Image](images/network/IMC_Tysserand_network_A_ROI_01.png)

#### IF first panel tysserand network
![Mon Image](images/network/IF_C1_Tysserand_network_C_layer_1.png)

#### IF second panel tysserand network
![Mon Image](images/network/IF_C2_Tysserand_network_B_layer_3.png)

### Assortativity

In this part, all different assortativity plots are present

#### IF assortativity for one patient/sample
![Mon Image](images/assort/assortativity_z-scored_patient-A_layer-1.png)

#### IMC assortativity for one patient/sample
![mon image](images/assort/assortativity_z-scored_patient-A_ROI-01.png)

#### IF assortativity aggregated by mean
![Mon Image](images/assort/assortativity_z-scored_IF_C1.png)
![Mon Image](images/assort/assortativity_z-scored_IF_C2.png)

#### IMC assortativity aggregated by mean
![Mon Image](images/assort/assortativity_z-scored_IMC.png)
In this image only the most important z-score (absolute values) are present to keep this plot visible

Here the real barplot with all tuples of phenotypes.
![Mon Image](images/assort/Mean_Std_Assortativity_z-scored_IMC.png)

### Niches composition

In this part, all different niche analysis plots are present

#### IF aggregated nodes
![Mon image](images/niche/IF_C2_niche_composition_niche.png)

#### IMC aggregated nodes
![Mon image](images/niche/IMC_niche_composition_niche.png)

#### IF for one patient/sample
![Mon image](images/niche/IFnicheG1C2.png)

and the associated network colored by niche:

![Mon image](images/niche/IF_netniche_G1C2.png)

#### IMC for one patient/sample
![Mon image](images/niche/IMCnicheA1.png)

and the associated network colored by niche: 

![Mon image](images/niche/IMC_netnicheA1.png)

### Synthetic Network Generation