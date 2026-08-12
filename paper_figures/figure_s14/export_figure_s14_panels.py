"""Export the eight logical panels of Supplementary Figure S14 separately.

The standalone panels use the same committed source data, colours, profile
normalization, complete-pair rule and plotting helpers as ``plot_figure_s14.py``.
Panel e remains a 2 x 3 grid because the six ROI profiles jointly constitute
that logical panel in the submitted composite.

Run from the repository root::

    python paper_figures/figure_s14/export_figure_s14_panels.py
"""

from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

import plot_figure_s14 as s14


MM = 1.0 / 25.4
EXPORT_EXTENSIONS = (".pdf", ".svg", ".png", ".tif")


def save_panel(fig: mpl.figure.Figure, stem: Path) -> list[dict[str, str]]:
    """Write one logical panel in vector and 600 dpi raster formats."""
    stem.parent.mkdir(parents=True, exist_ok=True)
    paths = [stem.with_suffix(extension) for extension in EXPORT_EXTENSIONS]
    fig.savefig(paths[0], facecolor="white", transparent=False)
    fig.savefig(paths[1], facecolor="white", transparent=False)
    fig.savefig(paths[2], dpi=600, facecolor="white", transparent=False)
    fig.savefig(
        paths[3],
        dpi=600,
        facecolor="white",
        transparent=False,
        pil_kwargs={"compression": "tiff_lzw"},
    )
    plt.close(fig)
    return [{"path": str(path), "sha256": s14.sha256_file(path)} for path in paths]


def export_image_panel(
    image,
    coordinates,
    title: str,
    label: str,
    stem: Path,
) -> list[dict[str, str]]:
    """Export one registered optical-image panel with the frozen ROIs."""
    fig, ax = plt.subplots(figsize=(72 * MM, 88 * MM), layout="constrained")
    ax.imshow(image, interpolation="nearest")
    s14.overlay_rois(ax, coordinates)
    ax.set_title(title, fontsize=8.0, fontweight="bold", pad=2.5)
    ax.set_axis_off()
    s14.panel_label(ax, label, x=-0.03, y=1.02)
    return save_panel(fig, stem)


def export_exr_panel(
    values,
    title: str,
    label: str,
    vmin: float,
    vmax: float,
    stem: Path,
) -> list[dict[str, str]]:
    """Export one ExR map with the shared pooled P1-P99 colour limits."""
    fig, ax = plt.subplots(figsize=(80 * MM, 88 * MM), layout="constrained")
    cmap = mpl.colormaps["coolwarm"].with_extremes(bad="#777777")
    artist = ax.imshow(
        values,
        cmap=cmap,
        vmin=vmin,
        vmax=vmax,
        interpolation="nearest",
    )
    ax.set_title(title, fontsize=8.0, fontweight="bold", pad=2.5)
    ax.set_axis_off()
    s14.panel_label(ax, label, x=-0.03, y=1.02)
    colorbar = fig.colorbar(artist, ax=ax, location="right", fraction=0.055, pad=0.025)
    colorbar.set_label("ExR value", fontsize=7)
    colorbar.ax.tick_params(labelsize=6, length=2)
    colorbar.ax.text(
        0.5,
        1.025,
        "P1-P99",
        ha="center",
        va="bottom",
        transform=colorbar.ax.transAxes,
        fontsize=5.5,
    )
    return save_panel(fig, stem)


def export_profile_panel(stem: Path) -> list[dict[str, str]]:
    """Export logical panel e as its six-ROI profile grid."""
    fig = plt.figure(figsize=(180 * MM, 92 * MM), layout="constrained", facecolor="white")
    grid = fig.add_gridspec(2, 3, hspace=0.12, wspace=0.10)
    s14.populate_profile_grid(fig, grid, include_panel_label=True)
    return save_panel(fig, stem)


def export_metric_panel(
    metrics,
    metric: str,
    ylabel: str,
    label: str,
    ylim: tuple[float, float],
    stem: Path,
) -> tuple[list[dict[str, str]], int]:
    """Export one complete-pair ROI metric panel."""
    fig, ax = plt.subplots(figsize=(74 * MM, 70 * MM), layout="constrained")
    pair_count = s14.paired_metric_plot(ax, metrics, metric, ylabel, label, ylim)
    return save_panel(fig, stem), pair_count


def export_panels(output_dir: Path) -> dict:
    """Export panels a-h and a machine-readable reproduction manifest."""
    data = s14.load_figure_data()
    outputs: dict[str, list[dict[str, str]]] = {}

    outputs["a"] = export_image_panel(
        data["uv"],
        data["coordinates"],
        s14.UV_LABEL,
        "a",
        output_dir / "Figure_S14a_registered_UV",
    )
    outputs["b"] = export_image_panel(
        data["nir"],
        data["coordinates"],
        s14.NIR_LABEL,
        "b",
        output_dir / "Figure_S14b_NIR_reference",
    )
    outputs["c"] = export_exr_panel(
        data["exr_uv"],
        f"{s14.UV_LABEL} ExR",
        "c",
        data["vmin"],
        data["vmax"],
        output_dir / "Figure_S14c_UV_ExR",
    )
    outputs["d"] = export_exr_panel(
        data["exr_nir"],
        f"{s14.NIR_LABEL} ExR",
        "d",
        data["vmin"],
        data["vmax"],
        output_dir / "Figure_S14d_NIR_ExR",
    )
    outputs["e"] = export_profile_panel(output_dir / "Figure_S14e_edge_normal_profiles")

    outputs["f"], n_edge = export_metric_panel(
        data["metrics"],
        "edge_width",
        "10-90% edge width (pixels)",
        "f",
        (0, 14.2),
        output_dir / "Figure_S14f_edge_width",
    )
    outputs["g"], n_fwhm = export_metric_panel(
        data["metrics"],
        "FWHM",
        "Written-line FWHM (pixels)",
        "g",
        (0, 16.2),
        output_dir / "Figure_S14g_FWHM",
    )
    outputs["h"], n_decay = export_metric_panel(
        data["metrics"],
        "halo_decay_distance",
        "Red-signal decay distance (pixels)",
        "h",
        (0, 4.5),
        output_dir / "Figure_S14h_decay_distance",
    )

    manifest = {
        "figure": "Supplementary Figure S14 standalone panels",
        "scope": "deterministic standalone exports from the same archived figure-level source data used by the composite script",
        "font": "Arial",
        "shared_exr_display_limits": {
            "vmin": data["vmin"],
            "vmax": data["vmax"],
            "definition": "pooled P1-P99",
        },
        "paired_roi_counts": {
            "edge_width": n_edge,
            "FWHM": n_fwhm,
            "decay_distance": n_decay,
        },
        "determinism": "No stochastic operation is used by either Figure S14 plotting script.",
        "python": platform.python_version(),
        "outputs": outputs,
    }
    manifest_path = output_dir / "Figure_S14_individual_panels_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export the eight logical panels of Supplementary Figure S14."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=s14.GENERATED_ROOT / "individual_panels",
        help="Folder for standalone panels a-h and their manifest.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    s14.validate_source_data()
    s14.configure_matplotlib()
    report = export_panels(parse_args().output_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))
