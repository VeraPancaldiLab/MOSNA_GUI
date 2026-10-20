<h1 align="center">MOSNA GUI — a graphical interface for MOSNA and Tysserand</h1>

---

## Table of contents

- [Architecture](#architecture)
- [Quick start](#quick-start)
  - [Linux / macOS](#linux--macos)
  - [Windows](#windows)
- [Launching the app](#launching-the-app)
- [Requirements](#requirements)
- [Using the tool](#using-the-tool)
  - [Workflow](#workflow)
  - [Input data format](#input-data-format)
  - [Step 0 — Project setup](#step-0--project-setup)
  - [Step 1 — Tysserand spatial networks](#step-1--tysserand-spatial-networks)
  - [Step 2 — Assortativity](#step-2--assortativity)
  - [Step 3 — Niche Analysis](#step-3--niche-analysis-nas)
- [Figures](#figures)
- [CLI usage](#cli-usage)
- [Benchmark](#benchmark)

---

## Architecture

MOSNA GUI is a Rust interface over two Python tools from PancaldiLAB, which it
runs unchanged:

| Step | Done by | Started from |
|---|---|---|
| 1 — spatial networks | [Tysserand](https://github.com/PancaldiLab/tysserand) | `package/tysserand_network.py` |
| 2 — assortativity | [MOSNA]([https://github.com/PancaldiLab/MOSNA](https://github.com/AlexCoul/mosna) | `package/assortativity.py` |
| 3 — niche analysis | MOSNA | `package/niche_analysis.py` |

The interface (`crates/mosna-gui`) edits the configuration and starts each step
as a Python sub-process, so every step can also be run from a terminal without
it. MOSNA itself ships in `mosna-package/`; Tysserand is installed with it. The
analyses no longer draw their figures: each one describes them, and the
`mosna_xy` renderer in `python/` turns every description into a PNG and an
interactive chart.

```
MOSNA_GUI/
├── crates/
│   ├── mosna-gui/       ← the interface: panels, viewer, manual
│   ├── mosna-config/    ← configuration.yaml, read and written byte for byte
│   ├── mosna-io/        ← parquet / csv / tsv, and finding samples on disk
│   ├── mosna-paths/     ← where the config, the sources and Python live
│   └── mosna-setup/     ← INSTALLATION.exe and UNINSTALL.exe
├── package/             ← the step runners, calling Tysserand and MOSNA
├── mosna-package/       ← MOSNA Python package (unchanged)
├── python/mosna_xy/     ← the figure renderer
├── CONFIG/              ← configuration template
└── setup.sh             ← Linux/macOS installer
```

---

## Quick start

### Linux / macOS

> **Requirements:** [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
> or Anaconda, and the [Rust toolchain](https://rustup.rs).

Careful: accept all of conda's channel terms first — create a throw-away
environment and cancel before it proceeds — or the installer stops half way
through to ask a licensing question and leaves the environment incomplete.

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh   # once
```

```bash
git clone https://github.com/OwenGriere/MOSNA_GUI.git
cd MOSNA_GUI
bash setup.sh
```

Options:

| Flag | Effect |
|---|---|
| `--no-shortcut` | Skip desktop launcher creation |
| `--no-rust` | Build the conda environment only, do not compile the interface |
| `--dev` | Install `mosna-package` in editable mode |

The script will:
1. Create a `mosna-GUI` conda environment (Python 3.11)
2. Install all scientific dependencies via conda-forge
3. Install `mosna-package` and the `mosna_xy` renderer into the environment
4. Compile the interface with `cargo build --release`
5. Generate `MosnaGUI.sh` and a Desktop shortcut

### Windows

> **Requirements:** none — what is missing is installed.

1. Download the repository (**Code → Download ZIP**), then right-click the ZIP
   → **Extract all**. `INSTALLATION.exe` does not work from inside the ZIP.
2. Open the extracted folder and double-click **`INSTALLATION.exe`**.
3. Choose where to put the folder and whether you want a desktop shortcut,
   then **Installer**.

The window then installs, each only if it is missing: the Microsoft C++ build
tools (Rust links with them; Windows asks for administrator rights for this
step only), Rust, and Miniconda into `%USERPROFILE%\miniconda3`. It builds the
same `mosna-GUI` environment as `setup.sh` — Python 3.11 and the scientific
stack from conda-forge, `mosna-package` and the `mosna_xy` renderer — compiles
the interface, and writes `MosnaGUI.bat` with a shortcut to it in the Start
Menu and, if asked for, on the desktop. The first install takes 30 to 60
minutes. It cannot be closed while it runs; everything it prints is kept in
`%TEMP%\mosna-gui-install.log`.

**To update**, run the new version's `INSTALLATION.exe` and choose the folder
MOSNA GUI is already in: your configuration and results are kept.

**To uninstall**, double-click **`UNINSTALL.exe`** in the folder. It removes
the shortcuts, `MosnaGUI.bat`, the `mosna-GUI` environment and the build
(`target\`), and offers to remove:

* **Miniconda, Rust and the C++ build tools**, each one found on the machine.
  Those `INSTALLATION.exe` installed itself (it notes them in
  `.mosna-prerequisites`) are ticked; the others are not, since other software
  may use them.
* **the folder itself**, unticked: it holds your configuration and whatever
  results you put there.

Each installer deletes the other platform's files once it has installed:
`INSTALLATION.exe` removes `setup.sh`, and `setup.sh` removes
`INSTALLATION.exe` and `UNINSTALL.exe`.

---

## Launching the app

| Platform | Command |
|---|---|
| Linux / macOS | `bash MosnaGUI.sh` or double-click the Desktop shortcut |
| Windows | The **MOSNA GUI** shortcut, in the Start Menu or on the desktop (it runs `MosnaGUI.bat`) |

The launcher activates the conda environment before starting the interface,
which is what puts the analyses' interpreter first on `PATH`. Three environment
variables override what the interface finds on its own:

| Variable | Effect |
|---|---|
| `MOSNA_PYTHON` | The interpreter the analyses are run with |
| `MOSNA_GUI_ROOT` | The directory holding `package/` |
| `MOSNA_XY_PYTHON` | The interpreter the figures are drawn with, when it is not the one running the analyses |

---

## Requirements

| Dependency | Version |
|---|---|
| Rust | 1.82 or newer |
| Python | 3.11 — `xy` requires it, and the analyses and the renderer share one interpreter |
| scanpy | ≥ 1.9 |
| scipy | 1.13 |
| pandas | ≥ 2.0 |
| xy | 0.0.6 (pinned: it is alpha, and a patch release changes what the figures look like) |
| mosna | from `mosna-package/` |

The full list is what the installers build: the conda packages in `setup.sh`
(and `crates/mosna-setup/src/conda.rs` on Windows), then `mosna-package/` and
the renderer in `python/`, whose `pyproject.toml` pins `xy`.

---

## Using the tool

### Workflow

```
[Step 0]  Set working directory + data paths
    ↓
[Step 1]  Tysserand — Build spatial networks from cell coordinates
    ↓
[Step 2]  Assortativity — Compute mixing statistics per network
    ↓
[Step 3]  Niche Analysis — Cluster niches from aggregated neighborhoods
```

### Input data format

Your input files must be CSV or Parquet tables following this structure:

| CellID | patient | sample | X_position | Y_position | Phenotype |
|--------|---------|--------|------------|------------|-----------|
| c001   | pt-01   | s1     | 120.3      | 84.7       | CD8_T     |
| …      | …       | …      | …          | …          | …         |

`patient` and `sample` are not required, and you can add other attributes such
as marker intensities.

File naming convention expected by the tool:

```
nodes_patient-01_sample-s1.parquet
nodes_patient-02_sample-s1.parquet
```

---

### Step 0 — Project setup

| Parameter | Description |
|---|---|
| **Nodes directory** | Folder containing your spatial cell tables |
| **Network directory** | Folder with pre-built edges/nodes (default: auto-generated by Step 1) |
| **Patient column name** | Column used as the first grouping level (e.g. `patient`) |
| **Sample column name** | Optional second grouping level (e.g. `sample`) |
| **Extension** | File format: `csv`, `parquet`, or `tsv` |

---

### Step 1 — Tysserand spatial networks

| Parameter | Description |
|---|---|
| **X / Y coordinates column** | Spatial position columns |
| **Phenotype column** | Cell type or cluster column |
| **Edges method** | `delaunay` (triangulation) or `knn` (k-nearest neighbours) |
| **Min neighbors** | Minimum neighbours for KNN |
| **CPU** | Cores for parallel processing |

Step 1 writes no figure. Its only one was a picture of the network, and the
Viewer's **Network** tab draws the network itself — from the same files, at any
zoom, with every attribute still readable at the pointer.

---

### Step 2 — Assortativity

| Parameter | Description |
|---|---|
| **Phenotype column** | Column defining cell types |
| **Index** | Cell index column (`index` = DataFrame index) |
| **Number of shuffle** | Randomizations to build the null distribution |
| **Randomization diagnostic** | Estimate time cost for your shuffle count |

---

### Step 3 — Niche Analysis (NAS)

| Parameter | Description |
|---|---|
| **Saving directory** | Output subfolder name, under `Niche_Analysis/Aggregation` |
| **Processing method** | `Aggregated nodes`. `Per sample` appears in the menu but is greyed out — that path is not verified yet |
| **Niches method** | `NAS` (SCAN-IT is work in progress) |
| **Phenotype column** | Cell type column |
| **Column to aggregate** | Columns used in the aggregated network |
| **X / Y coordinates for niches** | Spatial columns to rebuild coloured networks |
| **CPU** | Cores for parallel processing |

**Clustering parameters:**

| Parameter | Description |
|---|---|
| `order` | Neighborhood order (1 = direct neighbors) |
| `stat_funcs` | Aggregation functions: `np.mean`, `np.std`, … |
| `clusterer_type` | `gmm`, `leiden`, `hdbscan`, `spectral`, `ecg` |
| `metric` | Distance metric: `euclidean`, `manhattan`, `cosine` |
| `normalize` | Feature normalization: `total`, `niche`, `obs`, `clr`, `all` |
| `reducer_type` | Dimensionality reduction: `umap`, or `none` |
| `n_neighbors` | Neighbors for graph/UMAP construction |
| `min_dist` | UMAP tightness (smaller = more compact) |
| `dim_clust` | Reduced dimensions used for clustering |
| `n_clusters` | Number of clusters (gmm, spectral) |
| `resolution` | Leiden resolution (higher = more clusters) |
| `min_cluster_size` | HDBSCAN minimum cluster size |

---

## Figures

The analyses no longer call matplotlib. Each one writes a *specification* per
figure — the values, the labels, the colours, the file to write — into
`<working dir>/.mosna-figures/`, and then runs `python -m mosna_xy render` over
the lot. Every figure comes out twice, as a `.png` and as a `.html` chart that
can be panned, zoomed and read values off.

The queue survives the process that wrote it, so a figure that came out wrong
can be redrawn from the exact input that produced it, without re-running an
analysis that took an hour:

```bash
python -m mosna_xy render /path/to/working_dir/.mosna-figures --formats png,html
```

A failed render keeps the queue and says so; a successful one removes it.

---

## CLI usage

The analyses are ordinary Python modules and can be run without the interface.

```bash
conda activate mosna-GUI
cd /path/to/MOSNA_GUI

python -m package.tysserand_network \
    --file CONFIG/configuration.yaml \
    --working_dir /path/to/output/

python -m package.assortativity \
    --file CONFIG/configuration.yaml \
    --working_dir /path/to/output/

python -m package.niche_analysis \
    --file CONFIG/configuration.yaml \
    --working_dir /path/to/output/
```

---

## Benchmark

*To come.*
