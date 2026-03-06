# Mosna_analysis

- [Installation](#installation)
- [Tool](#tool)
    - [Tool Architecture](#tool-architecture)
    - [GUI Workflow](#tool-workflow)
    - [Step 2](#step-1-draw-tysserand-spatial-networks)
    - [Step 3](#step-2-generate-assortativity)
    - [Step 4](#step-3-plot-niches-analysis)

# Installation

clone my repo and run this:

    chmod +x setup.sh
    ./setup.sh

# Tool

The purpose of this tool is to facilitate the using of MOSNA and Tysserand, two package made by PancaldiLAB to build spatial networks and to analyse them with statistics.
This tool provide a GUI to generate easily the networks and other spatial analyse.

but you can also use it directly in terminal by using those command:

    conda activate mosna-GUI

    python -m package.tysserand_network --file CONFIG/configuration.yaml --working_dir ~/Desktop/
    python -m package.assortativity --file CONFIG/configuration.yaml --working_dir ~/Desktop/
    python -m package.niche_analysis --file CONFIG/configuration.yaml --working_dir ~/Desktop/

## Tool architecture 

![Mon Image](DOC/images/architecture.png)


## Tool Workflow

![Mon Image](DOC/images/workflow.png)


### ❗You can directly use Tysserand tool of my own tool instead of run pre-processing if you respect this the following format of your data:

❗ You must respect few things: 

- file could be Pandas DataFrame so table with .csv or .parquet extension

Tab for the following file format:
- .csv or .parquet

| Index  | CellID  | patient | Sample | X_position | Y_position | Phenotypes |
|--------|---------|---------|--------|------------|------------|------------|
| Cell 1 |    ...     |    ...     |     ...   |     ...       |   ...         |    ...        |
|  ...   |    ...     |      ...   |     ...   |     ...       |   ...         |     ...       |
| Cell N |    ...     |     ...    |    ...    |    ...        |     ...       |    ...        |



## Step 1: Draw Tysserand Spatial Networks

This step generate Tysserand networks for each patient/sample. You must fill **Tysserand** section.

| Clé                      | Description       |
|--------------------------|-------------------|
| Nodes directory          |                   |
| Patient column name      |                   |
| Sample column name       |                   |
| Extension                |                   |
| X coordinates column     |                   |
| Y coordinates column     |                   |
| Phenotype column         |                   |
| Edges method             |                   | 
| Min neighbors            |                   |
| CPU                      |                   |

## Step 2: Generate Assortativity

For this step you must fill **Assortativity** section. This step allow you to generate assortativity for each patient/sample networks and for an aggregate data.

| Clé                   | Description       |
|-----------------------|-------------------|
| Network directory     |                   |
| Phenotype column      |                   |
| Patient column name   |                   |
| Sample column name    |                   |
| Extension             |                   |
| Index                 |                   |

## Step 3: Plot Niches Analysis

In this step you must fill **NAS** section. This step will generate for you niches composition and all networks recolored by niche for each patient/sample and also the niche composition for aggregated nodes for all images of one type. 

| Clé                   | Description       |
|-----------------------|-------------------|
| method                 |                   |
| output_name_file       |                   |
| IMC_perform            |                   |
| IF_perform             |                   |
| panel                  |                   |
| node_aggregation       |                   | 
| perform_NAS_all_sample |                   |
| X coordinates column for niches    |                   |
| Y coordinates column for niches    |                   |

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

