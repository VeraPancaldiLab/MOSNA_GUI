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
| Nodes directory          | folder where you store all your spatial data |
| Patient column name      | Name of the first level of division for your file for example: 'patient' |
| Sample column name       | Name of the second level of division if it exists |
| Extension                | Extension of all files |
| X coordinates column     | Name of the column containing the X spatial coordinates |
| Y coordinates column     | Name of the column containing the Y spatial coordinates |
| Phenotype column         | Column defining the phenotype of each cell |
| Edges method             | Method used to compute edges | 
| Min neighbors            | Minimum number of neighbors for the KNN edges |
| CPU                      | Number of CPUs used for the parallelization process |

## Step 2: Generate Assortativity

For this step you must fill **Assortativity** section. This step allow you to generate assortativity for each patient/sample networks and for an aggregate data.

| Clé                   | Description       |
|-----------------------|-------------------|
| Network directory     | Folder where you store all your edges and nodes. Default if you run it after Tysserand Run |
| Phenotype column      | Name of the first level of division for your file for example: 'patient' |
| Patient column name   | Name of the second level of division if it exists |
| Sample column name    | Extension of all files |
| Extension             | Column defining the phenotype of each cell |
| Index                 | Name of the column for the cells reference |

## Step 3: Plot Niches Analysis

In this step you must fill **NAS** section. This step will generate for you niches composition and all networks recolored by niche for each patient/sample and also the niche composition for aggregated nodes for all images of one type. 

| Clé                   | Description       |
|-----------------------|-------------------|
| Network directory     | Folder where you store all your edges and nodes. Default if you run it after Tysserand Run |
| Saving directory       | Name of the saving folder to multiply the analysis | 
| Patient column name | Name of the first level of division for your file for example: 'patient' |
| Sample column name  | Name of the second level of division if it exists |
| Phenotype column | Column defining the phenotype of each cell |
| Processing method | Choose the method of processing (per sample (work in progress) or aggregation) |
| Niches method | Choose the method of niche analysis (NAS, SCAN-IT (work in progress)) |
| X coordinates column for niches    | X column if it exist to rebuild all networks with niches clustering |
| Y coordinates column for niches    | Y column if it exist to rebuild all networks with niches clustering |

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

