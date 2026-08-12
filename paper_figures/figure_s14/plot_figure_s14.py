"""Reproducible plotting script for Supplementary Figure S14.

This script generates the eight-panel comparison between 248 nm UV-written
and 976 nm NIR-written photochromic patterns. It is intentionally limited to
plotting Figure S14: image registration and metric calculation are performed
upstream by ``analyze_red_spreading.py``. The script reads the frozen
registered image, ROI table, ROI-level metrics and profile traces produced by
that analysis and does not alter those source data.

Figure content
--------------
(a,b) Registered optical images and matched ROI positions.
(c,d) Shared-scale excess-red maps (ExR = 2R - G - B).
(e) Six ROI-level edge-normal profiles and their spatial subsamples.
(f-h) Paired 10-90% edge width, FWHM and red-signal decay-distance metrics.

Usage
-----
From the repository root::

    python paper_figures/figure_s14/plot_figure_s14.py

Optional output folder::

    python paper_figures/figure_s14/plot_figure_s14.py --output-dir reproduced_S14

Outputs
-------
Figure_S14.png, Figure_S14.pdf, Figure_S14.svg, Figure_S14.tif and
Figure_S14_manifest.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import PIL
import scipy
from matplotlib import font_manager
from PIL import Image
from scipy import ndimage


# -----------------------------------------------------------------------------
# Project paths and publication-style constants
# -----------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
SOURCE_DATA = SCRIPT_DIR / "source_data"
PROFILES = SOURCE_DATA / "profiles"
SOURCE_MANIFEST = SCRIPT_DIR / "source_data_manifest.json"
GENERATED_ROOT = SCRIPT_DIR.parent / "generated" / "figure_s14"

UV_LABEL = "248 nm UV"
NIR_LABEL = "976 nm NIR"
UV_COLOR = "#D55E00"  # Okabe-Ito vermillion; square markers/dashed curves.
NIR_COLOR = "#0072B2"  # Okabe-Ito blue; circular markers/solid curves.
GRID_COLOR = "#D9D9D9"

ROI_ORDER = tuple(f"R{i:02d}" for i in range(1, 7))
FIGURE_SIZE_MM = (180, 225)
PROFILE_HALF_LENGTH_PX = 18.0
PROFILE_SMOOTHING_SIGMA_PX = 0.75


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of one file without loading it all at once."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_paths() -> dict[str, Path]:
    """Return the immutable figure-level inputs committed with this script."""
    return {
        "registered_uv_image": SOURCE_DATA / "uv_248nm_registered_common_grid.tif",
        "nir_image": SOURCE_DATA / "nir_976nm_reference.tif",
        "roi_coordinates": SOURCE_DATA / "roi_coordinates.csv",
        "roi_metrics": SOURCE_DATA / "roi_level_metrics.csv",
        "profile_directory": PROFILES,
        "analysis_config": SOURCE_DATA / "analysis_config.json",
        "analysis_pipeline": SOURCE_DATA / "analysis_pipeline.md",
    }


def validate_source_data() -> dict:
    """Fail before plotting if any committed source-data file is missing or changed."""
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    failures: list[str] = []
    for entry in manifest["files"]:
        path = SCRIPT_DIR / entry["path"]
        if not path.is_file():
            failures.append(f"missing: {entry['path']}")
            continue
        observed = sha256_file(path)
        if observed != entry["sha256"]:
            failures.append(
                f"SHA-256 mismatch: {entry['path']} (expected {entry['sha256']}, observed {observed})"
            )
    if failures:
        raise RuntimeError("Source-data validation failed:\n- " + "\n- ".join(failures))
    return manifest


def require_arial() -> None:
    """Require the manuscript font instead of silently substituting another font."""
    try:
        font_manager.findfont("Arial", fallback_to_default=False)
    except ValueError as error:
        raise RuntimeError(
            "Arial is required to reproduce the submitted Figure S14 layout. "
            "Install Arial and rerun the script."
        ) from error


def configure_matplotlib() -> None:
    """Set one scoped, reproducible visual style for the complete figure."""
    require_arial()
    mpl.rcParams.update(
        {
            "font.family": "Arial",
            "font.sans-serif": ["Arial"],
            "font.size": 7.0,
            "axes.labelsize": 7.0,
            "axes.titlesize": 7.5,
            "xtick.labelsize": 6.1,
            "ytick.labelsize": 6.1,
            "legend.fontsize": 6.2,
            "axes.linewidth": 0.75,
            "lines.linewidth": 1.1,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "savefig.facecolor": "white",
            "savefig.transparent": False,
        }
    )


def read_rgb(path: Path) -> np.ndarray:
    """Read an RGB image as a floating-point array scaled to [0, 1]."""
    with Image.open(path) as source:
        image = np.asarray(source.convert("RGB"), dtype=float)
    if image.max() > 1.5:
        image /= 255.0
    return np.clip(image, 0.0, 1.0)


def read_csv(path: Path) -> pd.DataFrame:
    """Read UTF-8 or UTF-8-with-BOM project tables consistently."""
    return pd.read_csv(path, encoding="utf-8-sig")


def panel_label(ax: mpl.axes.Axes, label: str, x: float, y: float) -> None:
    """Draw an unbolded parenthesized panel label outside an axes."""
    ax.text(
        x,
        y,
        f"({label})",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=9,
        fontweight="normal",
        color="black",
        clip_on=False,
    )


def style_axis(ax: mpl.axes.Axes, grid_axis: str = "y") -> None:
    """Apply the common minimal axis treatment to quantitative panels."""
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(direction="out", length=2.6, width=0.7, pad=2)
    if grid_axis:
        ax.grid(axis=grid_axis, color=GRID_COLOR, linewidth=0.55, zorder=0)


def overlay_rois(ax: mpl.axes.Axes, coordinates: pd.DataFrame) -> None:
    """Overlay frozen ROI centre lines and identifiers on registered images."""
    for row in coordinates.itertuples(index=False):
        angle = math.radians(float(row.normal_angle_deg))
        half_length = 13.0
        dx = half_length * math.cos(angle)
        dy = half_length * math.sin(angle)
        line = ax.plot(
            [row.center_x - dx, row.center_x + dx],
            [row.center_y - dy, row.center_y + dy],
            color="#00A6D6",
            linewidth=1.4,
            solid_capstyle="round",
            zorder=5,
        )[0]
        line.set_path_effects([pe.Stroke(linewidth=2.6, foreground="black"), pe.Normal()])
        ax.text(
            float(row.center_x) + 7,
            float(row.center_y) - 7,
            row.ROI_ID,
            fontsize=6.2,
            fontweight="bold",
            color="black",
            ha="left",
            va="bottom",
            zorder=6,
            bbox={
                "boxstyle": "round,pad=0.16",
                "facecolor": "white",
                "edgecolor": "black",
                "linewidth": 0.45,
                "alpha": 0.88,
            },
        )


def load_roi_profiles(
    roi_id: str,
    condition: str,
    sigma_px: float = PROFILE_SMOOTHING_SIGMA_PX,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return the normalized ROI mean and its 11 neighbouring profile traces.

    The profiles are read from the upstream analysis output. Smoothing is used
    only for the displayed traces, matching the analysis configuration; the
    function neither recomputes metrics nor edits raw profile values.
    """
    files = sorted(PROFILES.glob(f"{condition}_{roi_id}_P*.csv"))
    if len(files) != 11:
        raise RuntimeError(
            f"Expected 11 profile files for {condition}/{roi_id}; found {len(files)}."
        )

    frames = [read_csv(path) for path in files]
    distance = frames[0]["distance_pixel"].to_numpy(float)
    raw_stack = np.vstack(
        [frame["selected_raw_oriented"].to_numpy(float) for frame in frames]
    )
    mean_raw = raw_stack.mean(axis=0)
    step_px = float(np.median(np.diff(distance)))
    sigma_samples = sigma_px / step_px
    smooth_mean = ndimage.gaussian_filter1d(
        mean_raw, sigma=sigma_samples, mode="nearest"
    )

    n_background = max(5, int(0.18 * len(mean_raw)))
    background_samples = np.r_[mean_raw[:n_background], mean_raw[-n_background:]]
    baseline = float(np.median(background_samples))
    central_region = np.abs(distance) <= PROFILE_HALF_LENGTH_PX * 0.40
    peak = float(np.max(smooth_mean[central_region]))
    amplitude = peak - baseline
    if not np.isfinite(amplitude) or amplitude <= 0:
        raise RuntimeError(f"Non-positive profile amplitude for {condition}/{roi_id}.")

    smooth_stack = ndimage.gaussian_filter1d(
        raw_stack, sigma=sigma_samples, axis=1, mode="nearest"
    )
    return distance, (smooth_mean - baseline) / amplitude, (smooth_stack - baseline) / amplitude


def load_figure_data() -> dict:
    """Load and validate the shared image, table and ExR inputs for all exports."""
    paths = source_paths()
    uv = read_rgb(paths["registered_uv_image"])
    nir = read_rgb(paths["nir_image"])
    if uv.shape != nir.shape:
        raise RuntimeError(
            "The registered UV image and NIR reference grid do not have the same shape: "
            f"{uv.shape} versus {nir.shape}."
        )
    coordinates = read_csv(paths["roi_coordinates"])
    metrics = read_csv(paths["roi_metrics"])

    # ExR is calculated on the 0-255 RGB scale. Quantitative profiles come
    # from upstream raw ExR files; only map display uses P1-P99 clipping.
    exr_uv = 255.0 * (2.0 * uv[..., 0] - uv[..., 1] - uv[..., 2])
    exr_nir = 255.0 * (2.0 * nir[..., 0] - nir[..., 1] - nir[..., 2])
    pooled = np.concatenate([exr_uv.ravel(), exr_nir.ravel()])
    vmin, vmax = np.percentile(pooled[np.isfinite(pooled)], [1, 99])
    return {
        "paths": paths,
        "uv": uv,
        "nir": nir,
        "coordinates": coordinates,
        "metrics": metrics,
        "exr_uv": exr_uv,
        "exr_nir": exr_nir,
        "vmin": float(vmin),
        "vmax": float(vmax),
    }


def populate_profile_grid(
    fig: mpl.figure.Figure,
    profile_grid,
    include_panel_label: bool = True,
) -> list[mpl.axes.Axes]:
    """Draw the six ROI profile axes used in composite and standalone panel e."""
    profile_axes: list[mpl.axes.Axes] = []
    for index, roi_id in enumerate(ROI_ORDER):
        ax = fig.add_subplot(
            profile_grid[index // 3, index % 3],
            sharex=profile_axes[0] if profile_axes else None,
            sharey=profile_axes[0] if profile_axes else None,
        )
        profile_axes.append(ax)
        for condition, color, linestyle, label in [
            ("before", UV_COLOR, (0, (4, 2)), UV_LABEL),
            ("after", NIR_COLOR, "-", NIR_LABEL),
        ]:
            distance, mean_profile, subsamples = load_roi_profiles(roi_id, condition)
            for trace in subsamples:
                ax.plot(
                    distance,
                    trace,
                    color=color,
                    linewidth=0.28,
                    alpha=0.075,
                    zorder=1,
                )
            ax.plot(
                distance,
                mean_profile,
                color=color,
                linestyle=linestyle,
                linewidth=1.35,
                label=label,
                zorder=3,
            )
        ax.axhline(0.5, color="#777777", linestyle=":", linewidth=0.55, zorder=0)
        ax.set_title(roi_id, loc="left", fontsize=7, fontweight="bold", pad=1)
        ax.set(
            xlim=(-18, 18),
            ylim=(-1.15, 1.40),
            xticks=[-15, 0, 15],
            yticks=[0, 0.5, 1.0],
        )
        style_axis(ax)
        if index // 3 == 1:
            ax.set_xlabel("Distance (pixels)")
        if index % 3 == 0:
            ax.set_ylabel("Normalized ExR")
        if index == 0:
            ax.legend(
                frameon=False,
                fontsize=6.1,
                loc="lower right",
                handlelength=2.2,
                borderaxespad=0.2,
            )
    if include_panel_label:
        panel_label(profile_axes[0], "e", x=-0.16, y=1.08)
    return profile_axes


def paired_metric_plot(
    ax: mpl.axes.Axes,
    metrics: pd.DataFrame,
    metric: str,
    ylabel: str,
    panel: str,
    ylim: tuple[float, float],
) -> int:
    """Plot all complete UV/NIR ROI pairs plus descriptive boxplots."""
    paired = (
        metrics.pivot(index="ROI_ID", columns="condition", values=metric)
        .rename(columns={"before": "UV", "after": "NIR"})
        .dropna(subset=["UV", "NIR"])
        .reindex([roi for roi in ROI_ORDER if roi in metrics["ROI_ID"].unique()])
        .dropna(subset=["UV", "NIR"])
    )
    x_uv, x_nir = 0.0, 1.0
    for _, row in paired.iterrows():
        ax.plot(
            [x_uv, x_nir],
            [row.UV, row.NIR],
            color="#9A9A9A",
            linewidth=0.7,
            alpha=0.75,
            zorder=1,
        )

    boxes = ax.boxplot(
        [paired["UV"].to_numpy(), paired["NIR"].to_numpy()],
        positions=[x_uv, x_nir],
        widths=0.44,
        patch_artist=True,
        showfliers=False,
        whis=1.5,
        medianprops={"color": "black", "linewidth": 1.1},
        whiskerprops={"color": "#555555", "linewidth": 0.8},
        capprops={"color": "#555555", "linewidth": 0.8},
        boxprops={"edgecolor": "#555555", "linewidth": 0.8},
    )
    for box, color in zip(boxes["boxes"], [UV_COLOR, NIR_COLOR]):
        box.set_facecolor(color)
        box.set_alpha(0.13)

    ax.scatter(
        np.full(len(paired), x_uv),
        paired["UV"],
        s=23,
        marker="s",
        color=UV_COLOR,
        edgecolor="white",
        linewidth=0.55,
        zorder=3,
    )
    ax.scatter(
        np.full(len(paired), x_nir),
        paired["NIR"],
        s=25,
        marker="o",
        color=NIR_COLOR,
        edgecolor="white",
        linewidth=0.55,
        zorder=3,
    )
    ax.set_xticks([x_uv, x_nir], [UV_LABEL, NIR_LABEL])
    ax.set_ylabel(ylabel)
    ax.set_ylim(*ylim)
    ax.text(
        0.03,
        0.04,
        f"spatial ROI pairs: {len(paired)}",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=5.8,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.80, "pad": 1.0},
    )
    style_axis(ax)
    panel_label(ax, panel, x=-0.09, y=1.05)
    return len(paired)


def make_figure(output_dir: Path) -> dict:
    """Create and export Figure S14 using the frozen analysis artefacts."""
    data = load_figure_data()
    paths = data["paths"]
    uv, nir = data["uv"], data["nir"]
    coordinates, metrics = data["coordinates"], data["metrics"]
    exr_uv, exr_nir = data["exr_uv"], data["exr_nir"]
    vmin, vmax = data["vmin"], data["vmax"]

    mm = 1.0 / 25.4
    fig = plt.figure(
        figsize=(FIGURE_SIZE_MM[0] * mm, FIGURE_SIZE_MM[1] * mm),
        layout="constrained",
        facecolor="white",
    )
    grid = fig.add_gridspec(
        3, 4, height_ratios=[1.12, 1.46, 1.02], hspace=0.10, wspace=0.08
    )

    # Panels a-d: registered images and shared-scale excess-red maps.
    image_axes = [fig.add_subplot(grid[0, index]) for index in range(4)]
    for ax, image, title, label in [
        (image_axes[0], uv, UV_LABEL, "a"),
        (image_axes[1], nir, NIR_LABEL, "b"),
    ]:
        ax.imshow(image, interpolation="nearest")
        overlay_rois(ax, coordinates)
        ax.set_title(title, fontsize=7.7, fontweight="bold", pad=2.5)
        ax.set_axis_off()
        panel_label(ax, label, x=-0.04, y=1.03)

    cmap = mpl.colormaps["coolwarm"].with_extremes(bad="#777777")
    for ax, data, title, label in [
        (image_axes[2], exr_uv, f"{UV_LABEL} ExR", "c"),
        (image_axes[3], exr_nir, f"{NIR_LABEL} ExR", "d"),
    ]:
        artist = ax.imshow(
            data, cmap=cmap, vmin=vmin, vmax=vmax, interpolation="nearest"
        )
        ax.set_title(title, fontsize=7.7, fontweight="bold", pad=2.5)
        ax.set_axis_off()
        panel_label(ax, label, x=-0.04, y=1.03)

    colorbar = fig.colorbar(
        artist, ax=image_axes[2:4], location="right", fraction=0.045, pad=0.02
    )
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

    # Panel e: all six matched ROI profile sets.
    profile_grid = grid[1, :].subgridspec(2, 3, hspace=0.12, wspace=0.10)
    populate_profile_grid(fig, profile_grid, include_panel_label=True)

    # Panels f-h: matched pairs; the R03 UV decay value is missing, and the
    # paired-decay function consequently excludes R03 from both groups only in h.
    metric_grid = grid[2, :].subgridspec(1, 3, wspace=0.17)
    axes_fgh = [fig.add_subplot(metric_grid[0, index]) for index in range(3)]
    n_edge = paired_metric_plot(
        axes_fgh[0], metrics, "edge_width", "10-90% edge width (pixels)", "f", (0, 14.2)
    )
    n_fwhm = paired_metric_plot(
        axes_fgh[1], metrics, "FWHM", "Written-line FWHM (pixels)", "g", (0, 16.2)
    )
    n_decay = paired_metric_plot(
        axes_fgh[2], metrics, "halo_decay_distance", "Red-signal decay distance (pixels)", "h", (0, 4.5)
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = output_dir / "Figure_S14"
    fig.savefig(stem.with_suffix(".pdf"), facecolor="white", transparent=False)
    fig.savefig(stem.with_suffix(".svg"), facecolor="white", transparent=False)
    fig.savefig(stem.with_suffix(".png"), dpi=600, facecolor="white", transparent=False)
    fig.savefig(
        stem.with_suffix(".tif"),
        dpi=600,
        facecolor="white",
        transparent=False,
        pil_kwargs={"compression": "tiff_lzw"},
    )
    plt.close(fig)

    exported_paths = [stem.with_suffix(ext) for ext in (".pdf", ".svg", ".png", ".tif")]
    manifest = {
        "figure": "Supplementary Figure S14",
        "size_mm": list(FIGURE_SIZE_MM),
        "font": "Arial",
        "scope": "deterministic plotting from archived figure-level source data; upstream registration and ROI measurement are not rerun",
        "raw_and_processed_sources": {
            key: path.relative_to(REPO_ROOT).as_posix()
            for key, path in paths.items()
        },
        "transformations": [
            "No sharpening, deconvolution or local contrast enhancement is applied in this plotting script.",
            "ExR = 2R - G - B on the 0-255 RGB scale.",
            "ExR display only uses shared pooled P1-P99 colour limits; profile source values remain unclipped.",
            "The figure displays 11 neighbouring spatial profile subsamples per ROI; they are not independent material replicates.",
            "Panel h retains complete UV-NIR pairs only; R03 is absent from both boxplot groups because its UV decay crossing is missing.",
        ],
        "paired_roi_counts": {"edge_width": n_edge, "FWHM": n_fwhm, "decay_distance": n_decay},
        "exr_display_limits": {"vmin": float(vmin), "vmax": float(vmax), "definition": "pooled P1-P99"},
        "determinism": "No stochastic operation is used by either Figure S14 plotting script.",
        "software": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "matplotlib": mpl.__version__,
            "pillow": PIL.__version__,
            "platform": platform.platform(),
        },
        "source_data_manifest": SOURCE_MANIFEST.relative_to(REPO_ROOT).as_posix(),
        "exports": [
            {"path": str(path), "sha256": sha256_file(path)}
            for path in exported_paths
        ],
    }
    manifest_path = output_dir / "Figure_S14_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Supplementary Figure S14.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=GENERATED_ROOT / "composite",
        help="Folder for Figure_S14.pdf/.svg/.png/.tif and its manifest.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    validate_source_data()
    configure_matplotlib()
    report = make_figure(parse_args().output_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))
