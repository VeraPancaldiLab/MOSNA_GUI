
import matplotlib.pyplot as plt
import matplotlib as mpl

BG_COLOR      = "white"
TEXT_COLOR    = "#1a1a2e"
TICK_COLOR    = "#2d2d2d"
EDGE_COLOR    = "#cccccc"
GRID_COLOR    = "#e8e8e8"
CELL_BG_COLOR = "#f5f5f5"

RCPARAMS = {
    # Fond
    "figure.facecolor":   BG_COLOR,
    "axes.facecolor":     BG_COLOR,
    "savefig.facecolor":  BG_COLOR,
    "savefig.edgecolor":  BG_COLOR,

    # Bordures et ticks
    "axes.edgecolor":     EDGE_COLOR,
    "axes.linewidth":     0.8,
    "xtick.color":        TICK_COLOR,
    "ytick.color":        TICK_COLOR,
    "xtick.major.width":  0.6,
    "ytick.major.width":  0.6,
    "xtick.major.size":   3,
    "ytick.major.size":   3,

    # Texte
    "text.color":         TEXT_COLOR,
    "axes.labelcolor":    TEXT_COLOR,
    "font.family":        "sans-serif",
    "font.sans-serif":    ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size":          11,
    "axes.titlesize":     13,
    "axes.titleweight":   "bold",
    "axes.labelsize":     11,
    "xtick.labelsize":    10,
    "ytick.labelsize":    10,

    # Légende
    "legend.facecolor":   BG_COLOR,
    "legend.edgecolor":   EDGE_COLOR,
    "legend.fontsize":    10,
    "legend.framealpha":  1,
    "legend.borderpad":   0.6,

    # Lignes
    "lines.linewidth":    1.5,
    "lines.antialiased":  True,

    # Figure
    "figure.dpi":         150,
    "savefig.dpi":        300,
    "savefig.bbox":       "tight",
    "figure.constrained_layout.use": False,
}

def apply_style():
    plt.rcParams.update(RCPARAMS)