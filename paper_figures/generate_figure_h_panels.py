"""Render the approved post-revision eight-panel Figure H from one live run."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from microscopy_matching.pipeline import run_pipeline  # noqa: E402
from paper_figures.diagnostics import (  # noqa: E402
    CORRIDOR_RADIUS,
    DPI,
    PANEL_SIZE,
    PaperDiagnostics,
    build_paper_diagnostics,
    configure_arial,
    corridor_overlay_rgb,
    presentation_rgb,
    response_rgb,
    save_exact_rgb,
    skeleton_rgb,
    strict_mask_rgb,
    validate_png,
)


DEFAULT_TARGETS = REPO / "data" / "input" / "target_images"
DEFAULT_REFERENCES = REPO / "data" / "input" / "reference_images"
DEFAULT_OUTDIR = Path(__file__).resolve().parent / "generated" / "figure_h"

OUTPUT_NAMES = (
    "panel_a_structural_response.png",
    "panel_b_foreground_skeleton.png",
    "panel_c_pairwise_internal_score_matrix.png",
    "panel_d_local_translation_landscape.png",
    "panel_e_registered_support_corridor.png",
    "panel_f_corridor_radius_sensitivity.png",
    "panel_g_strict_matched_only_output.png",
    "panel_h_target_derived_presentation.png",
)

INK = "#132b35"
BORDER = "#9da8ad"
ACCENT = "#df654f"
ORANGE = "#c6812f"
TEAL = "#2c919b"
GRID = "#dce3e6"


def _brown_colormap() -> mpl.colors.Colormap:
    return mpl.colors.LinearSegmentedColormap.from_list(
        "brown_response",
        ("#fffaf1", "#f3cfaa", "#c47a55", "#6b342a", "#1b1110"),
    )


def _add_border(fig: plt.Figure) -> None:
    fig.add_artist(
        mpl.patches.Rectangle(
            (0.003, 0.003),
            0.994,
            0.994,
            transform=fig.transFigure,
            fill=False,
            edgecolor=BORDER,
            linewidth=0.65,
        )
    )


def _save_chart(fig: plt.Figure, destination: Path, expected_size: tuple[int, int]) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, format="png", dpi=DPI, facecolor="white")
    plt.close(fig)
    with Image.open(destination) as opened:
        image = opened.convert("RGB")
    if image.size != expected_size:
        raise RuntimeError(f"Unexpected chart size for {destination.name}: {image.size}")
    image.save(destination, format="PNG", dpi=(DPI, DPI), optimize=True)
    validate_png(destination, expected_size=expected_size)
    return destination


def _save_image(
    image_rgb: np.ndarray,
    destination: Path,
) -> Path:
    """Export one microscopy-derived panel with unchanged pixel geometry."""

    return save_exact_rgb(image_rgb, destination)


def save_response_panel(context: PaperDiagnostics, destination: Path) -> Path:
    target = context.run.target_structures[0]
    fig = plt.figure(figsize=(PANEL_SIZE[0] / DPI, PANEL_SIZE[1] / DPI), dpi=DPI)
    ax = fig.add_axes((0.07, 0.095, 0.81, 0.86))
    cax = fig.add_axes((0.91, 0.13, 0.026, 0.70))
    image = ax.imshow(target.response, cmap=_brown_colormap(), vmin=0.0, vmax=1.0)
    ax.axis("off")
    colorbar = fig.colorbar(image, cax=cax, ticks=(0.0, 1.0))
    colorbar.ax.tick_params(labelsize=6.2, width=0.7, length=2.0, pad=1.5)
    _add_border(fig)
    return _save_chart(fig, destination, PANEL_SIZE)


def save_score_matrix(context: PaperDiagnostics, destination: Path) -> Path:
    matrix = context.score_matrix
    lower = float(np.floor(matrix.min() * 20.0) / 20.0)
    upper = float(np.ceil(matrix.max() * 20.0) / 20.0)
    fig = plt.figure(figsize=(PANEL_SIZE[0] / DPI, PANEL_SIZE[1] / DPI), dpi=DPI)
    ax = fig.add_axes((0.20, 0.23, 0.56, 0.64))
    cax = fig.add_axes((0.79, 0.23, 0.028, 0.64))
    image = ax.imshow(matrix, cmap="cividis", vmin=lower, vmax=upper, aspect="equal")
    ax.set_xticks(range(4), context.reference_labels)
    ax.set_yticks(range(4), tuple(str(index) for index in range(1, 5)))
    ax.set_xlabel("Candidate reference", labelpad=2, fontsize=5.8)
    ax.set_ylabel("Target image", labelpad=3, fontsize=5.8)
    ax.tick_params(length=0, pad=1.5, labelsize=5.2)
    for row in range(4):
        for column in range(4):
            value = float(matrix[row, column])
            ax.text(
                column,
                row,
                f"{value:.3f}",
                ha="center",
                va="center",
                fontsize=5.0,
                color="white" if value < (lower + upper) / 2 else INK,
                fontweight="bold" if column == context.selected_indices[row] else "normal",
            )
            if column == context.selected_indices[row]:
                ax.add_patch(
                    mpl.patches.Rectangle(
                        (column - 0.5, row - 0.5),
                        1,
                        1,
                        fill=False,
                        edgecolor=ACCENT,
                        linewidth=1.15,
                    )
                )
    colorbar = fig.colorbar(image, cax=cax)
    colorbar.ax.tick_params(labelsize=5.0, width=0.7, length=1.8, pad=1.5)
    cax.set_title("F", color=INK, fontsize=5.6, pad=2)
    return _save_chart(fig, destination, PANEL_SIZE)


def save_translation_landscape(context: PaperDiagnostics, destination: Path) -> Path:
    offsets, scores = context.translation_offsets, context.translation_scores
    levels = np.linspace(float(scores.min()), float(scores.max()), 13)
    fig = plt.figure(figsize=(PANEL_SIZE[0] / DPI, PANEL_SIZE[1] / DPI), dpi=DPI)
    ax = fig.add_axes((0.22, 0.24, 0.54, 0.64))
    cax = fig.add_axes((0.79, 0.24, 0.028, 0.64))
    contour = ax.contourf(offsets, offsets, scores, levels=levels, cmap="cividis")
    ax.contour(offsets, offsets, scores, levels=levels[2::2], colors="white", linewidths=0.55)
    match = context.run.matches[0][context.selected_indices[0]]
    coarse_x, coarse_y = match.coarse_dx - match.dx, match.coarse_dy - match.dy
    if offsets.min() <= coarse_x <= offsets.max() and offsets.min() <= coarse_y <= offsets.max():
        ax.scatter([coarse_x], [coarse_y], s=30, facecolor="white", edgecolor=INK, linewidth=0.9, zorder=4)
    ax.scatter([0], [0], marker="*", s=58, color="#e8791c", edgecolor="white", linewidth=0.6, zorder=5)
    ax.set_xlabel("dₓ offset (analysis px)", labelpad=2, fontsize=5.8)
    ax.set_ylabel("dᵧ offset (analysis px)", labelpad=2, fontsize=5.8)
    ax.set_xticks((-24, -12, 0, 12, 24)); ax.set_yticks((-24, -12, 0, 12, 24))
    ax.tick_params(labelsize=5.2); ax.set_xlim(-25.5, 25.5); ax.set_ylim(-25.5, 25.5); ax.set_aspect("equal")
    colorbar = fig.colorbar(contour, cax=cax)
    colorbar.formatter = mpl.ticker.FormatStrFormatter("%.2f"); colorbar.update_ticks()
    colorbar.ax.tick_params(labelsize=5.0, width=0.7, length=1.8, pad=1.5)
    cax.set_title("Score", fontsize=5.2, pad=2)
    return _save_chart(fig, destination, PANEL_SIZE)


def _radius_arrays(context: PaperDiagnostics, attribute: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    all_values = np.asarray(
        [[getattr(record, attribute) for record in case] for case in context.radius_metrics_by_target],
        dtype=np.float64,
    )
    return np.median(all_values, axis=0), np.min(all_values, axis=0), np.max(all_values, axis=0)


def draw_radius_sensitivity(ax: plt.Axes, context: PaperDiagnostics) -> None:
    radii = np.asarray([record.radius_px for record in context.radius_metrics], dtype=float)
    series = (
        ("recall", ACCENT, "-", "$R$"),
        ("precision", ORANGE, "--", "$Q$"),
        ("dice", TEAL, "-", "$D$"),
    )
    for attribute, color, line_style, label in series:
        median, low, high = _radius_arrays(context, attribute)
        ax.fill_between(radii, low, high, color=color, alpha=0.10, linewidth=0)
        ax.plot(radii, median, color=color, lw=1.45, ls=line_style, label=label)
        selected = int(np.where(radii == CORRIDOR_RADIUS)[0][0])
        ax.scatter(
            [CORRIDOR_RADIUS],
            [median[selected]],
            s=26,
            color=color,
            edgecolor="white",
            linewidth=0.7,
            zorder=4,
        )
    ax.axvline(CORRIDOR_RADIUS, color=INK, lw=0.9, ls=(0, (3, 2)))
    ax.text(CORRIDOR_RADIUS + 0.5, 0.045, "$r = 12$", ha="left", va="bottom", fontsize=7.0)
    ax.set_xlim(2, 30)
    ax.set_ylim(0.0, 1.06)
    ax.set_xticks((2, 12, 20, 30))
    ax.set_yticks((0.0, 0.5, 1.0))
    ax.set_xlabel("Radius, $r$ (px)")
    ax.set_ylabel("Metric")
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.legend(loc="upper right", ncol=3, frameon=False, handlelength=1.2, columnspacing=0.7)


def save_radius_sensitivity(context: PaperDiagnostics, destination: Path) -> Path:
    fig = plt.figure(figsize=(PANEL_SIZE[0] / DPI, PANEL_SIZE[1] / DPI), dpi=DPI)
    # Keep extra lower margin so the standalone 600-dpi x-axis title is never clipped.
    ax = fig.add_axes((0.17, 0.25, 0.80, 0.69))
    draw_radius_sensitivity(ax, context)
    _add_border(fig)
    return _save_chart(fig, destination, PANEL_SIZE)


def generate_figure_h(
    context: PaperDiagnostics,
    outdir: Path,
    *,
    font_path: Path | None = None,
) -> list[Path]:
    """Generate the approved post-revision Figure H sequence from current calculations."""

    outdir.mkdir(parents=True, exist_ok=True)
    font_path = font_path or configure_arial()
    target_index = 0
    candidate_index = context.selected_indices[target_index]
    target = context.run.target_structures[target_index]
    auxiliary = context.run.reference_structures[candidate_index]
    match = context.run.matches[target_index][candidate_index]
    paths = [outdir / name for name in OUTPUT_NAMES]

    save_response_panel(context, paths[0])
    _save_image(skeleton_rgb(target), paths[1])
    save_score_matrix(context, paths[2])
    save_translation_landscape(context, paths[3])
    _save_image(corridor_overlay_rgb(target, auxiliary, match), paths[4])
    save_radius_sensitivity(context, paths[5])
    _save_image(strict_mask_rgb(target, auxiliary, match), paths[6])
    _save_image(presentation_rgb(context, target_index), paths[7])

    # Mathematical charts have a fixed publication canvas.  Microscopy-derived
    # panels deliberately retain their native array dimensions so that no
    # hidden crop, stretch, letterbox, or synthetic border can enter Figure H.
    chart_indices = {0, 2, 3, 5}
    for index, path in enumerate(paths):
        validate_png(path, expected_size=PANEL_SIZE if index in chart_indices else None)
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run matching and render the approved post-revision Figure H panels.")
    parser.add_argument("--targets", type=Path, default=DEFAULT_TARGETS)
    parser.add_argument("--references", type=Path, default=DEFAULT_REFERENCES)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    font = configure_arial()
    run = run_pipeline(args.targets, args.references)
    context = build_paper_diagnostics(run)
    for path in generate_figure_h(context, args.outdir.resolve(), font_path=font):
        print(path)


if __name__ == "__main__":
    main()
