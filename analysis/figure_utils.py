"""Shared publication-figure utilities.

Every figure is emitted as a 600-dpi PNG for manuscript insertion and as an
editable SVG with live text. Figure typography is configured at a minimum of
10 pt. Arial is requested first; Arimo (a metrically compatible open font) is
the deterministic fallback used in this build environment.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib as mpl
import matplotlib.pyplot as plt

# Preserve text as text in SVG rather than converting glyphs to paths.
mpl.rcParams.update({
    "svg.fonttype": "none",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Arimo", "Liberation Sans", "DejaVu Sans"],
    "font.size": 10.0,
    "axes.titlesize": 12.0,
    "axes.labelsize": 10.5,
    "xtick.labelsize": 10.0,
    "ytick.labelsize": 10.0,
    "legend.fontsize": 10.0,
    "figure.titlesize": 12.0,
    "axes.linewidth": 0.8,
    "lines.linewidth": 1.5,
    "lines.markersize": 5.0,
    "errorbar.capsize": 3.0,
    "savefig.dpi": 600,
})


def prepare_figure_dirs(figure_root: Path) -> tuple[Path, Path]:
    png_dir = figure_root / "png"
    svg_dir = figure_root / "svg"
    png_dir.mkdir(parents=True, exist_ok=True)
    svg_dir.mkdir(parents=True, exist_ok=True)
    return png_dir, svg_dir


def save_figure(fig: Any, figure_root: Path, stem: str) -> None:
    """Save and close one Matplotlib figure in PNG and editable SVG formats."""
    png_dir, svg_dir = prepare_figure_dirs(figure_root)
    fig.savefig(
        png_dir / f"{stem}.png",
        dpi=600,
        bbox_inches="tight",
        facecolor="white",
    )
    fig.savefig(
        svg_dir / f"{stem}.svg",
        format="svg",
        bbox_inches="tight",
        facecolor="white",
    )
    plt.close(fig)
