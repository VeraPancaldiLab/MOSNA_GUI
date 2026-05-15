

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.colors as mcolors
import matplotlib.cm as cm
from matplotlib.colors import SymLogNorm
import re

def assort_figures_mean_std_across_samples(net_stat, save_dir, homo_pair=False):

    assort_cols = net_stat.columns[net_stat.columns.str.endswith(" Z")]
    assort_cols = [col for col in assort_cols if col != "assort Z"]

    cmap = plt.cm.RdBu_r.copy()
    
    if not homo_pair:
        col_to_remove = []
        for col in assort_cols:
            pheno1, pheno2 = col.split(' - ', maxsplit=1)
            pheno2 = pheno2[:-2]
            if pheno1 == pheno2:
                col_to_remove.append(col)
        assort_cols = [col for col in assort_cols if col not in col_to_remove]
        cmap.set_bad(color="black")

    assort = net_stat[assort_cols].copy()
    assort = assort.replace([np.inf, -np.inf], np.nan)
    assort = assort.dropna(axis=1, how='all')
    assort = assort.loc[:, assort.std() > 0]

    mean_assort = assort.mean(axis=0)
    sem_assort  = assort.sem(axis=0)

    celltypes = sorted(set(
        ct
        for col in mean_assort.index
        for m in [re.match(r'^(.+?) - (.+?) Z$', col)]
        if m
        for ct in [m.group(1).strip(), m.group(2).strip()]
    ))

    n = len(celltypes)
    matrix_mean = pd.DataFrame(np.nan, index=celltypes, columns=celltypes)
    matrix_sem  = pd.DataFrame(np.nan, index=celltypes, columns=celltypes)

    for col in mean_assort.index:
        m = re.match(r'^(.+?) - (.+?) Z$', col)
        if not m:
            continue
        ct1, ct2 = m.group(1).strip(), m.group(2).strip()
        if ct1 not in celltypes or ct2 not in celltypes:
            continue
        matrix_mean.loc[ct1, ct2] = mean_assort[col]
        matrix_mean.loc[ct2, ct1] = mean_assort[col]
        matrix_sem.loc[ct1, ct2]  = sem_assort[col]
        matrix_sem.loc[ct2, ct1]  = sem_assort[col]

    if matrix_mean.notna().sum().sum() == 0:
        raise ValueError("matrix_mean est entièrement vide.")

    zlim = np.nanmax(np.abs(matrix_mean.values))
    linthresh = max(0.1, zlim * 0.05)

    norm = SymLogNorm(linthresh=linthresh, linscale=1, vmin=-zlim, vmax=zlim, base=10)

    sem_vals = matrix_sem.values.flatten()
    sem_vals = sem_vals[~np.isnan(sem_vals)]
    sem_min, sem_max = sem_vals.min(), sem_vals.max()

    SIZE_MAX = 0.85
    SIZE_MIN = 0.15

    def sem_to_size(s):
        if np.isnan(s):
            return 0
        if sem_max == sem_min:
            return SIZE_MAX
        norm_s = (s - sem_min) / (sem_max - sem_min)
        return SIZE_MAX - norm_s * (SIZE_MAX - SIZE_MIN)

    fig = plt.figure(figsize=(n * 0.7 + 5, n * 0.7 + 2))
    ax = fig.add_axes([0.08, 0.08, 0.72, 0.82])
    ax.set_xlim(0, n)
    ax.set_ylim(0, n)
    ax.set_aspect('equal')
    ax.invert_yaxis()
    ax.invert_xaxis()

    for i in range(n):
        for j in range(n):
            ax.add_patch(patches.Rectangle((j, i), 1, 1,
                        facecolor='#f0f0f0', edgecolor='white',
                        linewidth=0.5, zorder=1))

    for i, ct1 in enumerate(celltypes):
        for j, ct2 in enumerate(celltypes):
            mean_val = matrix_mean.loc[ct1, ct2]
            sem_val  = matrix_sem.loc[ct1, ct2]
            if np.isnan(mean_val):
                continue
            size   = sem_to_size(sem_val)
            offset = (1 - size) / 2
            ax.add_patch(patches.Rectangle(
                (j + offset, i + offset), size, size,
                facecolor=cmap(norm(mean_val)), edgecolor='none', zorder=2
            ))

    ax.set_xticks(np.arange(n) + 0.5)
    ax.set_yticks(np.arange(n) + 0.5)
    ax.set_xticklabels(celltypes, rotation=45, ha='right', fontsize=20)
    ax.set_yticklabels(celltypes, fontsize=20)
    ax.tick_params(length=0)
    ax.set_title('Mean assortativity + std accross samples', fontsize=25, pad=14)

    cbar_ax = fig.add_axes([0.83, 0.38, 0.03, 0.52])
    sm = cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, cax=cbar_ax)
    cbar.set_label('Mean assortativity Z (SymLogNorm scale)', fontsize=20)
    cbar.ax.tick_params(labelsize=12)

    tick_candidates = []
    for exp in range(0, int(np.log10(max(zlim, 1))) + 2):
        tick_candidates += [10**exp, -10**exp]
    tick_candidates += [linthresh, -linthresh, 0]
    ticks = sorted(set([t for t in tick_candidates if -zlim <= t <= zlim]))
    cbar.set_ticks(ticks)
    cbar.set_ticklabels([f'{t:.2g}' for t in ticks])

    legend_ax = fig.add_axes([0.83, 0.08, 0.13, 0.25])
    legend_ax.set_xlim(0, 1)
    legend_ax.set_ylim(0, 1)
    legend_ax.axis('off')

    legend_ax.text(0.5, 0.97, 'SEM', fontsize=20, fontweight='bold',
                ha='center', va='top', transform=legend_ax.transAxes)

    fig_width, fig_height = fig.get_size_inches()
    leg_pos = legend_ax.get_position()
    leg_w_inch = leg_pos.width  * fig_width
    leg_h_inch = leg_pos.height * fig_height

    examples = [
        (sem_max,                           f'SEM élevée\n({sem_max:.2f})\n→ incertain'),
        (sem_min + (sem_max - sem_min) / 2, f'SEM moy.\n({(sem_min+sem_max)/2:.2f})'),
        (sem_min,                           f'SEM faible\n({sem_min:.2f})\n→ fiable'),
    ]

    for k, (sv, label) in enumerate(examples):
        y_ax = 0.78 - k * 0.33

        size = sem_to_size(sv)
        sq   = size * 0.18   

        x0 = 0.18 - sq / 2
        y0 = y_ax - sq / 2

        ratio = (leg_h_inch / leg_w_inch)
        sq_x  = sq * ratio     
        x0    = 0.18 - sq_x / 2

        legend_ax.add_patch(patches.FancyBboxPatch(
            (x0, y0), sq_x, sq,
            boxstyle='square,pad=0',
            facecolor='#555555', edgecolor='white', linewidth=0.8,
            transform=legend_ax.transAxes, zorder=3
        ))
        legend_ax.text(0.42, y_ax, label, fontsize=15,
                    va='center', ha='left',
                    transform=legend_ax.transAxes,
                    color='#222222', linespacing=1.3)

    plt.tight_layout()
    if homo_pair:
        plt.savefig(save_dir / "Assortativity_heatmap_across_patient.png", dpi=300)
    else:
        plt.savefig(save_dir / "Assortativity_heatmap_across_patient_without_auto_paired_pheno.png", dpi=300)
    plt.close()
    return