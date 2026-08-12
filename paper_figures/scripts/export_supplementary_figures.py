"""Render the approved post-revision supplementary figures from one live run."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from PIL import Image, ImageDraw, ImageFont, ImageOps

REPO = Path(__file__).resolve().parents[2]
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
    native_reference_rgb,
    pair_row_for,
    presentation_rgb,
    registration_diagnostic_rgb,
    response_rgb,
    save_exact_rgb,
    skeleton_rgb,
    strict_mask_rgb,
    validate_png,
)


DEFAULT_TARGETS = REPO / "data" / "input" / "target_images"
DEFAULT_REFERENCES = REPO / "data" / "input" / "reference_images"
DEFAULT_OUTDIR = REPO / "paper_figures" / "generated" / "supplementary"

COMPOSITE_NAMES = (
    "supplementary_figure_1_casewise_evidence_flow.png",
    "supplementary_figure_2_pairwise_ranking_transforms.png",
    "supplementary_figure_3_registration_output_sensitivity.png",
    "supplementary_figure_4_candidate_references.png",
    "supplementary_figure_5_selection_diagnostics.png",
)
COMPOSITE_SIZES = ((4322, 3236), (4322, 1889), (4322, 1889), (4322, 2220), (4322, 3236))

INK = "#132b35"
MUTED = "#71838c"
GRID = "#d7e0e4"
TARGET_FOREGROUND = "#aeb9be"
TARGET_SKELETON = "#55a9d4"
REGISTERED_REFERENCE = "#e6a000"
S_COLOR = "#0b78b4"
T_COLOR = "#d65f00"
U_COLOR = "#009e73"
Z_COLOR = "#cc79a7"
REFERENCE_COLORS = (S_COLOR, T_COLOR, U_COLOR, Z_COLOR)
COMPONENTS = ("G", "T", "S", "C_f", "C_r", "O")
COMPONENT_KEYS = (
    "geometry_score",
    "topology_score",
    "support",
    "forward_similarity",
    "reverse_similarity",
    "orientation",
)


def _font(font_path: Path, size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidate = font_path.with_name("arialbd.ttf") if bold else font_path
    if not candidate.is_file():
        candidate = font_path
    return ImageFont.truetype(str(candidate), size=size)


def _save_figure(fig: plt.Figure, destination: Path, expected_size: tuple[int, int]) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(destination, format="png", dpi=DPI, facecolor="white")
    plt.close(fig)
    with Image.open(destination) as opened:
        image = opened.convert("RGB")
    if image.size != expected_size:
        raise RuntimeError(f"Unexpected figure size for {destination.name}: {image.size}")
    image.save(destination, format="PNG", dpi=(DPI, DPI), optimize=True)
    validate_png(destination, expected_size=expected_size)
    return destination


def _save_rgb_panel(
    image_rgb: np.ndarray,
    destination: Path,
) -> Path:
    """Save a standalone evidence panel without geometric modification."""

    return save_exact_rgb(image_rgb, destination)


def _panel_label(ax: plt.Axes, letter: str) -> None:
    ax.text(
        -0.13,
        1.08,
        f"({letter})",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=7.4,
        color=INK,
        clip_on=False,
    )


def _figure_label(fig: plt.Figure, letter: str, x: float, y: float) -> None:
    fig.text(x, y, f"({letter})", ha="left", va="bottom", fontsize=7.4, color=INK)


def _fit_into_box(
    image_rgb: np.ndarray,
    box: tuple[int, int, int, int],
    *,
    background: tuple[int, int, int],
) -> Image.Image:
    x0, y0, x1, y1 = box
    target_size = (x1 - x0, y1 - y0)
    image = Image.fromarray(np.asarray(image_rgb, dtype=np.uint8), mode="RGB")
    contained = ImageOps.contain(image, target_size, Image.Resampling.LANCZOS)
    panel = Image.new("RGB", target_size, background)
    panel.paste(contained, ((target_size[0] - contained.width) // 2, (target_size[1] - contained.height) // 2))
    return panel


def _save_composite_image(image: Image.Image, destination: Path, expected_size: tuple[int, int]) -> Path:
    if image.mode != "RGB" or image.size != expected_size:
        raise RuntimeError(f"Invalid composite canvas for {destination.name}: {image.mode}, {image.size}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, format="PNG", dpi=(DPI, DPI), optimize=True)
    validate_png(destination, expected_size=expected_size)
    return destination


def _stage_images(context: PaperDiagnostics, target_index: int) -> tuple[np.ndarray, ...]:
    candidate_index = context.selected_indices[target_index]
    target = context.run.target_structures[target_index]
    auxiliary = context.run.reference_structures[candidate_index]
    match = context.run.matches[target_index][candidate_index]
    return (
        response_rgb(target),
        skeleton_rgb(target),
        corridor_overlay_rgb(target, auxiliary, match),
        strict_mask_rgb(target, auxiliary, match),
        presentation_rgb(context, target_index),
    )


def _draw_tile_label(draw: ImageDraw.ImageDraw, x: int, y: int, letter: str, font_path: Path) -> None:
    draw.rectangle((x, y, x + 230, y + 82), fill=(239, 243, 244))
    draw.text((x + 24, y + 13), letter, fill=INK, font=_font(font_path, 42, bold=True))


def build_figure1(context: PaperDiagnostics, font_path: Path) -> Image.Image:
    canvas = Image.new("RGB", COMPOSITE_SIZES[0], "white")
    draw = ImageDraw.Draw(canvas)
    x_boxes = ((322, 1100), (1123, 1901), (1924, 2702), (2725, 3502), (3525, 4303))
    y_boxes = ((285, 895), (1032, 1642), (1778, 2389), (2525, 3136))
    titles = ("Structural response", "Foreground and skeleton", "Registered support corridor", "Strict matched-only mask", "Target-derived presentation")
    backgrounds = ((255, 250, 241), (12, 26, 32), (12, 26, 32), (0, 0, 0), (183, 168, 33))
    title_font = _font(font_path, 42)
    row_font = _font(font_path, 43, bold=True)
    labels = tuple(chr(97 + index) for index in range(5))
    for column, ((x0, x1), title) in enumerate(zip(x_boxes, titles)):
        box = draw.textbbox((0, 0), title, font=title_font)
        draw.text((x0 + (x1 - x0 - (box[2] - box[0])) / 2, 205), title, fill=INK, font=title_font)
    for row, (y0, y1) in enumerate(y_boxes):
        selected = context.reference_labels[context.selected_indices[row]]
        row_text = f"target_{row + 1:02d} → {selected}"
        text_box = draw.textbbox((0, 0), row_text, font=row_font)
        label_img = Image.new("RGBA", (text_box[2] - text_box[0] + 10, text_box[3] - text_box[1] + 10), (255, 255, 255, 0))
        ImageDraw.Draw(label_img).text((5, 5), row_text, fill=REFERENCE_COLORS[context.selected_indices[row]], font=row_font)
        rotated = label_img.transpose(Image.Transpose.ROTATE_90)
        canvas.paste(rotated, (70, y0 + (y1 - y0 - rotated.height) // 2), rotated)
        for column, ((x0, x1), image_rgb, background, letter) in enumerate(zip(x_boxes, _stage_images(context, row), backgrounds, labels)):
            box = (x0, y0, x1, y1)
            canvas.paste(_fit_into_box(image_rgb, box, background=background), (x0, y0))
            _draw_tile_label(draw, x0, y0, letter, font_path)
    return canvas


def save_figure1_individuals(context: PaperDiagnostics, panel_dir: Path) -> list[Path]:
    saved: list[Path] = []
    stages = ("a_structural_response", "b_foreground_skeleton", "c_registered_corridor", "d_strict_matched_mask", "e_target_presentation")
    for target_index in range(4):
        for stage, image_rgb in zip(stages, _stage_images(context, target_index)):
            path = panel_dir / f"suppfig1_target_{target_index + 1:02d}_{stage}.png"
            _save_rgb_panel(image_rgb, path)
            saved.append(path)
    return saved


def pairwise_matrix_panel(ax: plt.Axes, cax: plt.Axes, context: PaperDiagnostics, *, compact: bool = False) -> None:
    matrix = context.score_matrix
    image = ax.imshow(matrix, cmap="cividis", vmin=0.30, vmax=max(0.52, float(matrix.max())))
    ax.set_xticks(range(4), context.reference_labels)
    ax.set_yticks(range(4), tuple(str(index) for index in range(1, 5)) if compact else context.target_labels)
    ax.set_xlabel("Candidate" if compact else "Candidate reference")
    if compact:
        ax.set_ylabel("Target")
        ax.tick_params(labelsize=5.3)
    for row in range(4):
        for column in range(4):
            value = float(matrix[row, column])
            ax.text(column, row, f"{value:.3f}", ha="center", va="center", color=INK if value >= 0.43 else "white", fontsize=5.0 if compact else 6.6, fontweight="bold" if column == context.selected_indices[row] else "normal")
            if column == context.selected_indices[row]:
                ax.add_patch(mpl.patches.Rectangle((column - 0.5, row - 0.5), 1, 1, fill=False, edgecolor=T_COLOR, linewidth=1.2))
    colorbar = ax.figure.colorbar(image, cax=cax)
    colorbar.ax.tick_params(labelsize=5.2 if compact else 6.0)
    cax.set_title("F", pad=3.0, color=INK, fontsize=5.8 if compact else 7.2)


def pairwise_ranking_panel(ax: plt.Axes, context: PaperDiagnostics, *, compact: bool = False) -> None:
    x = np.arange(4)
    for index in range(4):
        selected = context.selected_indices[index]
        runner = context.runner_up_indices[index]
        high = context.score_matrix[index, selected]
        low = context.score_matrix[index, runner]
        color = REFERENCE_COLORS[selected]
        ax.plot((x[index], x[index]), (low, high), color=color, lw=1.3)
        ax.scatter(x[index], high, s=28, color=color, edgecolor="white", linewidth=0.5, zorder=3)
        ax.scatter(x[index], low, s=28, facecolor="white", edgecolor=color, linewidth=1.0, zorder=3)
        text_x = x[index] + (0.06 if index < 3 else -0.06)
        ax.text(
            text_x,
            (high + low) / 2,
            f"Δ={high - low:.3f}",
            ha="left" if index < 3 else "right",
            va="center",
            fontsize=5.4 if compact else 6.2,
            color=INK,
        )
    if compact:
        ax.set_xticks(x, tuple(f"{i + 1}→{context.reference_labels[context.selected_indices[i]]}" for i in range(4)))
        ax.set_xlabel("Target → selected reference", fontsize=5.8)
        ax.tick_params(labelsize=5.3)
    else:
        ax.set_xticks(x, tuple(f"{context.target_labels[i]}\n→ {context.reference_labels[context.selected_indices[i]]}" for i in range(4)))
    low_limit = float(context.score_matrix[np.arange(4), np.asarray(context.runner_up_indices)].min() - 0.04)
    high_limit = float(context.score_matrix[np.arange(4), np.asarray(context.selected_indices)].max() + 0.02)
    ax.set_ylim(low_limit, high_limit)
    ax.set_ylabel("Internal score, F")
    ax.grid(axis="y", color=GRID, lw=0.6)
    legend = (
        Line2D([0], [0], marker="o", color="none", markerfacecolor=MUTED, markeredgecolor="white", markersize=4.6, label="best"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor="white", markeredgecolor=MUTED, markersize=4.6, label="runner-up"),
    )
    ax.legend(handles=legend, loc="lower left", ncols=2, columnspacing=1.0, fontsize=5.2 if compact else 6.0)


def transform_panel(ax: plt.Axes, context: PaperDiagnostics, *, compact: bool = False) -> None:
    matches = [context.run.matches[i][context.selected_indices[i]] for i in range(4)]
    scales = np.asarray([match.scale for match in matches])
    angles = np.asarray([match.angle_deg for match in matches])
    magnitudes = np.asarray([np.hypot(match.dx, match.dy) for match in matches])
    # Bubble *area* is proportional to translation magnitude.  The previous
    # squared mapping made the largest, nearly coincident Z bubble obscure T
    # and U even though all three coordinates were scientifically distinct.
    sizes = 90.0 * np.maximum(magnitudes / 50.0, 0.16)

    # Draw large bubbles first and small bubbles last.  Transparent faces and
    # dark outlines reveal genuine overlap without moving any data coordinate.
    for index in np.argsort(sizes)[::-1]:
        scale, angle, size = scales[index], angles[index], sizes[index]
        candidate = context.selected_indices[index]
        color = REFERENCE_COLORS[candidate]
        ax.scatter(
            scale,
            angle,
            s=size,
            color=color,
            alpha=0.78,
            edgecolor=INK,
            linewidth=0.45,
            zorder=3,
        )

    # Labels are positioned independently from marker draw order so that the
    # close T/U/Z transforms remain readable at the true calculated positions.
    for index, (scale, angle) in enumerate(zip(scales, angles)):
        candidate = context.selected_indices[index]
        label = context.reference_labels[candidate]
        # The selected T/U/Z transforms are close.  Deterministic upper-right
        # offsets keep every label readable while preserving its bubble link.
        label_offsets = {"S": (7, 7), "Z": (8, 15), "U": (18, 9), "T": (28, 3)}
        offset_x, offset_y = label_offsets.get(label, (8, 8))
        ax.annotate(
            label,
            (scale, angle),
            xytext=(offset_x, offset_y),
            textcoords="offset points",
            ha="left",
            va="bottom",
            fontsize=5.6 if compact else 6.7,
            color=INK,
            annotation_clip=False,
            arrowprops={"arrowstyle": "-", "color": INK, "lw": 0.45},
        )
    ax.set_xlim(min(1.05, float(scales.min() - 0.12)), max(1.75, float(scales.max() + 0.12)))
    ax.set_ylim(min(-2.1, float(angles.min() - 0.35)), max(2.05, float(angles.max() + 0.35)))
    ax.set_xlabel("Scale" if compact else "Analysis scale")
    ax.set_ylabel("Angle (°)" if compact else "In-plane angle (°)")
    if compact:
        ax.tick_params(labelsize=5.3)
    ax.grid(color=GRID, lw=0.6)
    legend_label = "50 px translation" if compact else "Translation magnitude = 50 px"
    ax.scatter([], [], s=90.0, facecolor="white", edgecolor=MUTED, linewidth=0.8, label=legend_label)
    ax.legend(loc="lower left", handletextpad=0.6, fontsize=5.2 if compact else 6.0)


def build_figure2(context: PaperDiagnostics) -> plt.Figure:
    fig = plt.figure(figsize=(COMPOSITE_SIZES[1][0] / DPI, COMPOSITE_SIZES[1][1] / DPI), dpi=DPI)
    ax_a = fig.add_axes((0.070, 0.220, 0.255, 0.660))
    cax = fig.add_axes((0.335, 0.220, 0.014, 0.660))
    ax_b = fig.add_axes((0.405, 0.200, 0.255, 0.690))
    ax_c = fig.add_axes((0.745, 0.200, 0.235, 0.690))
    pairwise_matrix_panel(ax_a, cax, context, compact=True)
    pairwise_ranking_panel(ax_b, context, compact=True)
    transform_panel(ax_c, context, compact=True)
    for letter, axis in (("a", ax_a), ("b", ax_b), ("c", ax_c)):
        _figure_label(fig, letter, axis.get_position().x0 - 0.020, 0.955)
    fig.text(0.5, 0.055, "Scores are internal ranking measures, not calibrated probabilities.", ha="center", color=MUTED, fontsize=6.0)
    return fig


def _single_chart_axes() -> tuple[plt.Figure, plt.Axes]:
    fig = plt.figure(figsize=(PANEL_SIZE[0] / DPI, PANEL_SIZE[1] / DPI), dpi=DPI)
    return fig, fig.add_axes((0.20, 0.23, 0.73, 0.69))


def save_figure2_individuals(context: PaperDiagnostics, panel_dir: Path) -> list[Path]:
    paths = [panel_dir / "suppfig2_a_pairwise_score_matrix.png", panel_dir / "suppfig2_b_selected_runner_up_scores.png", panel_dir / "suppfig2_c_transform_scale_rotation.png"]
    fig = plt.figure(figsize=(PANEL_SIZE[0] / DPI, PANEL_SIZE[1] / DPI), dpi=DPI)
    ax, cax = fig.add_axes((0.22, 0.24, 0.58, 0.67)), fig.add_axes((0.84, 0.24, 0.03, 0.67))
    pairwise_matrix_panel(ax, cax, context, compact=True)
    _save_figure(fig, paths[0], PANEL_SIZE)
    fig = plt.figure(figsize=(PANEL_SIZE[0] / DPI, PANEL_SIZE[1] / DPI), dpi=DPI); ax = fig.add_axes((0.26, 0.25, 0.67, 0.66)); pairwise_ranking_panel(ax, context, compact=True); _save_figure(fig, paths[1], PANEL_SIZE)
    fig = plt.figure(figsize=(PANEL_SIZE[0] / DPI, PANEL_SIZE[1] / DPI), dpi=DPI); ax = fig.add_axes((0.22, 0.23, 0.71, 0.69)); transform_panel(ax, context, compact=True); _save_figure(fig, paths[2], PANEL_SIZE)
    return paths


def translation_landscape_panel(ax: plt.Axes, cax: plt.Axes, context: PaperDiagnostics, *, compact: bool = False) -> None:
    offsets, scores = context.translation_offsets, context.translation_scores
    levels = np.linspace(float(scores.min()), float(scores.max()), 13)
    contour = ax.contourf(offsets, offsets, scores, levels=levels, cmap="cividis")
    ax.contour(offsets, offsets, scores, levels=levels[2::2], colors="white", linewidths=0.55)
    match = context.run.matches[0][context.selected_indices[0]]
    coarse_x, coarse_y = match.coarse_dx - match.dx, match.coarse_dy - match.dy
    if offsets.min() <= coarse_x <= offsets.max() and offsets.min() <= coarse_y <= offsets.max():
        ax.scatter([coarse_x], [coarse_y], s=30, facecolor="white", edgecolor=INK, linewidth=0.9, zorder=4)
    ax.scatter([0], [0], marker="*", s=58, color="#e8791c", edgecolor="white", linewidth=0.6, zorder=5)
    ax.set_xlabel("dₓ offset (px)" if compact else "Relative translation, dₓ (analysis px)")
    ax.set_ylabel("dᵧ offset (px)" if compact else "Relative translation, dᵧ (analysis px)")
    ax.set_xticks((-24, -12, 0, 12, 24)); ax.set_yticks((-24, -12, 0, 12, 24))
    ax.set_aspect("equal"); ax.set_xlim(-25.5, 25.5); ax.set_ylim(-25.5, 25.5)
    colorbar = ax.figure.colorbar(contour, cax=cax)
    colorbar.ax.tick_params(labelsize=5.2 if compact else 6.0)
    cax.set_ylabel("G" if compact else "Geometry objective, G", labelpad=3 if compact else 4, fontsize=5.8 if compact else 7.2)


def _radius_data(context: PaperDiagnostics, attribute: str) -> np.ndarray:
    return np.asarray([[getattr(record, attribute) for record in case] for case in context.radius_metrics_by_target], dtype=float)


def radius_panel(ax: plt.Axes, context: PaperDiagnostics, *, compact: bool = False) -> None:
    radii = np.asarray([record.radius_px for record in context.radius_metrics])
    series = (("recall", T_COLOR, "-", "R" if compact else "R: target retention"), ("precision", "#e69500", "--", "Q" if compact else "Q: corridor density"), ("dice", S_COLOR, "-", "D" if compact else "D: spatial overlap"))
    for attribute, color, style, label in series:
        values = _radius_data(context, attribute)
        median = np.median(values, axis=0)
        ax.fill_between(radii, values.min(axis=0), values.max(axis=0), color=color, alpha=0.10, linewidth=0)
        ax.plot(radii, median, color=color, ls=style, lw=1.3, label=label)
    ax.axvline(CORRIDOR_RADIUS, color=INK, lw=0.9, ls=(0, (3, 2)))
    ax.text(CORRIDOR_RADIUS + 0.5, 0.04, "$r = 12$", ha="left", va="bottom", fontsize=5.6 if compact else 6.5)
    ax.set_xlim(2, 30); ax.set_ylim(0, 1.05); ax.set_xticks((2, 12, 20, 30))
    ax.set_xlabel("Radius, r (px)" if compact else "Corridor radius, r (analysis px)")
    ax.set_ylabel("Metric value")
    if compact:
        ax.tick_params(labelsize=5.3)
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.legend(loc="upper right", ncols=3 if compact else 1, fontsize=5.2 if compact else 6.0, columnspacing=0.8, handlelength=1.4)


def metrics_panel(ax: plt.Axes, context: PaperDiagnostics, *, compact: bool = False) -> None:
    metric_names = ("recall", "precision", "dice")
    labels = ("R", "Q", "D")
    x = np.arange(3, dtype=float)
    jitter = np.asarray((-0.12, -0.04, 0.04, 0.12))
    selected_radius = int(np.where(np.asarray([r.radius_px for r in context.radius_metrics]) == CORRIDOR_RADIUS)[0][0])
    for target_index in range(4):
        values = [getattr(context.radius_metrics_by_target[target_index][selected_radius], name) for name in metric_names]
        color = REFERENCE_COLORS[context.selected_indices[target_index]]
        ax.scatter(x + jitter[target_index], values, s=22, color=color, edgecolor="white", linewidth=0.5, label=context.reference_labels[context.selected_indices[target_index]])
    for metric_index, name in enumerate(metric_names):
        values = [getattr(context.radius_metrics_by_target[target][selected_radius], name) for target in range(4)]
        ax.hlines(np.median(values), metric_index - 0.18, metric_index + 0.18, color=INK, lw=1.2)
    ax.set_xticks(x, labels); ax.set_ylim(0, 1.0); ax.set_ylabel("Metric at r = 12" if compact else "Metric value at r = 12")
    if compact:
        ax.tick_params(labelsize=5.3)
    ax.grid(axis="y", color=GRID, lw=0.6); ax.legend(loc="upper right", ncols=2, fontsize=5.2 if compact else 6.0)
    ax.text(0.02, 0.04, "n=4 selected pairs", transform=ax.transAxes, color=MUTED, fontsize=5.3 if compact else 6.0)


def build_figure3(context: PaperDiagnostics) -> plt.Figure:
    fig = plt.figure(figsize=(COMPOSITE_SIZES[2][0] / DPI, COMPOSITE_SIZES[2][1] / DPI), dpi=DPI)
    # Explicit axes leave protected whitespace around the colorbar and all y-axis
    # titles.  This avoids the former overlap between panels (a) and (b).
    ax_a = fig.add_axes((0.055, 0.245, 0.260, 0.595))
    cax = fig.add_axes((0.326, 0.245, 0.016, 0.595))
    ax_b = fig.add_axes((0.425, 0.200, 0.300, 0.690))
    ax_c = fig.add_axes((0.805, 0.200, 0.175, 0.690))
    translation_landscape_panel(ax_a, cax, context, compact=True); radius_panel(ax_b, context, compact=True); metrics_panel(ax_c, context, compact=True)
    for letter, axis in (("a", ax_a), ("b", ax_b), ("c", ax_c)):
        _figure_label(fig, letter, axis.get_position().x0 - 0.020, 0.955)
    fig.text(0.5, 0.055, "Fixed-transform sensitivity only; these quantities are not ground-truth accuracy.", ha="center", color=MUTED, fontsize=6.0)
    return fig


def save_figure3_individuals(context: PaperDiagnostics, panel_dir: Path) -> list[Path]:
    paths = [panel_dir / "suppfig3_a_translation_landscape.png", panel_dir / "suppfig3_b_corridor_radius_sensitivity.png", panel_dir / "suppfig3_c_metrics_at_radius_12.png"]
    fig = plt.figure(figsize=(PANEL_SIZE[0] / DPI, PANEL_SIZE[1] / DPI), dpi=DPI); ax, cax = fig.add_axes((0.24, 0.25, 0.48, 0.60)), fig.add_axes((0.77, 0.25, 0.028, 0.60)); translation_landscape_panel(ax, cax, context, compact=True); _save_figure(fig, paths[0], PANEL_SIZE)
    fig = plt.figure(figsize=(PANEL_SIZE[0] / DPI, PANEL_SIZE[1] / DPI), dpi=DPI); ax = fig.add_axes((0.20, 0.24, 0.73, 0.68)); radius_panel(ax, context, compact=True); _save_figure(fig, paths[1], PANEL_SIZE)
    fig = plt.figure(figsize=(PANEL_SIZE[0] / DPI, PANEL_SIZE[1] / DPI), dpi=DPI); ax = fig.add_axes((0.26, 0.23, 0.68, 0.69)); metrics_panel(ax, context, compact=True); _save_figure(fig, paths[2], PANEL_SIZE)
    return paths


def _reference_analysis_rgb(context: PaperDiagnostics, candidate_index: int) -> np.ndarray:
    structure = context.run.reference_structures[candidate_index]
    image = np.full((*structure.mask.shape, 3), (12, 26, 32), dtype=np.uint8)
    image[structure.mask] = (207, 221, 224)
    image[structure.skeleton] = (85, 190, 210)
    return image


def build_figure4(context: PaperDiagnostics, font_path: Path) -> Image.Image:
    canvas = Image.new("RGB", COMPOSITE_SIZES[3], "white"); draw = ImageDraw.Draw(canvas)
    x_boxes = ((257, 1247), (1276, 2266), (2296, 3285), (3315, 4304))
    y_boxes = ((160, 1000), (1130, 2025))
    title_font, label_font, caption_font = _font(font_path, 45, bold=True), _font(font_path, 42, bold=True), _font(font_path, 34)
    for candidate_index, (x0, x1) in enumerate(x_boxes):
        title = f"Candidate {context.reference_labels[candidate_index]}"; box = draw.textbbox((0, 0), title, font=title_font); draw.text((x0 + (x1 - x0 - (box[2] - box[0])) / 2, 65), title, fill=INK, font=title_font)
        native_box=(x0,y_boxes[0][0],x1,y_boxes[0][1]); analysis_box=(x0,y_boxes[1][0],x1,y_boxes[1][1])
        canvas.paste(_fit_into_box(native_reference_rgb(context, candidate_index), native_box, background=(188, 174, 42)), (x0,y_boxes[0][0]))
        canvas.paste(_fit_into_box(_reference_analysis_rgb(context, candidate_index), analysis_box, background=(12,26,32)), (x0,y_boxes[1][0]))
        _draw_tile_label(draw,x0,y_boxes[0][0],chr(97+candidate_index),font_path); _draw_tile_label(draw,x0,y_boxes[1][0],chr(101+candidate_index),font_path)
        caption="Binary support + skeleton"; cb=draw.textbbox((0,0),caption,font=caption_font); draw.text((x0+(x1-x0-(cb[2]-cb[0]))/2,2045),caption,fill=INK,font=caption_font)
    for text, y in (("Native reference image", 500), ("Analysis representation", 1450)):
        box=draw.textbbox((0,0),text,font=label_font); img=Image.new("RGBA",(box[2]-box[0]+10,box[3]-box[1]+10),(255,255,255,0)); ImageDraw.Draw(img).text((5,5),text,fill=INK,font=label_font); rot=img.transpose(Image.Transpose.ROTATE_90); canvas.paste(rot,(70,y),rot)
    note="Native reference display (500 µm annotations); not the 200 µm target-referenced field used in Supplementary Fig. 1."
    nb=draw.textbbox((0,0),note,font=caption_font); draw.text(((4322-(nb[2]-nb[0]))/2,2155),note,fill=MUTED,font=caption_font)
    return canvas


def save_figure4_individuals(context: PaperDiagnostics, panel_dir: Path) -> list[Path]:
    saved=[]
    for i,label in enumerate(context.reference_labels):
        p=panel_dir/f"suppfig4_{chr(97+i)}_candidate_{label}_native.png"; _save_rgb_panel(native_reference_rgb(context,i),p); saved.append(p)
    for i,label in enumerate(context.reference_labels):
        p=panel_dir/f"suppfig4_{chr(101+i)}_candidate_{label}_analysis.png"; _save_rgb_panel(_reference_analysis_rgb(context,i),p); saved.append(p)
    return saved


def _clean_image_axis(ax: plt.Axes) -> None:
    ax.set_xticks([]); ax.set_yticks([])
    for spine in ax.spines.values(): spine.set_visible(False)


def image_panel(ax: plt.Axes, image_rgb: np.ndarray, title: str, score: float) -> None:
    ax.imshow(image_rgb); _clean_image_axis(ax); ax.set_title(f"{title}\nF={score:.5f}", pad=4.5, color=INK, linespacing=1.12)


def component_panel(ax: plt.Axes, context: PaperDiagnostics, target_index: int, *, compact: bool = False) -> None:
    selected=context.selected_indices[target_index]; runner=context.runner_up_indices[target_index]
    selected_row=pair_row_for(context,target_index,selected); runner_row=pair_row_for(context,target_index,runner)
    selected_values=np.asarray([float(selected_row[key] or 0.0) for key in COMPONENT_KEYS]); runner_values=np.asarray([float(runner_row[key] or 0.0) for key in COMPONENT_KEYS])
    y=np.arange(len(COMPONENTS)); height=0.28
    selected_name=context.reference_labels[selected]; runner_name=context.reference_labels[runner]
    ax.barh(y-height/2,selected_values,height=height,color=REFERENCE_COLORS[selected],edgecolor=INK,linewidth=0.55,label=f"selected {selected_name}")
    ax.barh(y+height/2,runner_values,height=height,facecolor="white",edgecolor=REFERENCE_COLORS[runner],linewidth=0.9,hatch="//",label=f"runner-up {runner_name}")
    ax.set_yticks(y,COMPONENTS); ax.invert_yaxis(); ax.set_xlim(0,1); ax.set_xlabel("Component value" if compact else "Component value [0, 1]")
    delta=float(selected_row["final_score"])-float(runner_row["final_score"])
    title=(f"{context.target_labels[target_index]}: {selected_name} vs {runner_name}; ΔF={delta:.5f}" if compact else f"{context.target_labels[target_index]} component comparison; ΔF={delta:.5f}")
    ax.set_title(title,pad=4,fontsize=5.6 if compact else 7.2)
    if compact:
        ax.tick_params(labelsize=5.3)
    ax.grid(axis="x",color=GRID,lw=0.6); ax.legend(loc="center left",bbox_to_anchor=(0.62 if compact else 0.67,0.50),handlelength=1.15 if compact else 1.35,labelspacing=0.55 if compact else 0.65,borderaxespad=0,frameon=False,fontsize=5.0 if compact else 6.0)


def bound_panel(ax: plt.Axes, context: PaperDiagnostics, *, compact: bool = False) -> None:
    for candidate_index,label in enumerate(context.reference_labels):
        ax.plot(context.search_bound_values,context.search_bound_scores[:,candidate_index],color=REFERENCE_COLORS[candidate_index],marker="o",markersize=3.4,lw=1.0,label=label)
    ax.set_xlim(1.585,1.915); ax.set_xticks(context.search_bound_values); ax.set_xlabel("Scale upper bound" if compact else "Diagnostic scale upper bound"); ax.set_ylabel("Score, F" if compact else "Internal score, F")
    ax.set_title("target_03 bound sensitivity" if compact else "target_03 search-bound expansion (separate sensitivity run)",pad=4,fontsize=5.8 if compact else 7.2); ax.grid(color=GRID,lw=0.55)
    winners=np.argmax(context.search_bound_scores,axis=1)
    if np.all(winners==winners[0]):
        message=(f"Selected {context.reference_labels[int(winners[0])]} in all reruns" if compact else f"Selected {context.reference_labels[int(winners[0])]} throughout current reruns")
    else:
        message="Selected candidate changes" if compact else "Selected candidate changes across tested bounds"
    if compact:
        ax.tick_params(labelsize=5.3)
    ax.text(0.02,0.79 if compact else 0.93,message,transform=ax.transAxes,color=MUTED,fontsize=5.2 if compact else 6.0,va="top"); ax.legend(loc="center",ncols=4,bbox_to_anchor=(0.54,0.53),fontsize=5.2 if compact else 6.0,columnspacing=0.8,handlelength=1.2)


def topology_panel(ax: plt.Axes, context: PaperDiagnostics, *, compact: bool = False) -> None:
    match = context.run.matches[0][context.selected_indices[0]]
    values = (match.topology.endpoint_coverage, match.topology.missing_stroke_penalty)
    labels = ("Endpoint E", "Missing M")
    y = np.arange(2)

    bars = ax.barh(
        y,
        values,
        color=(S_COLOR, T_COLOR),
        edgecolor=INK,
        linewidth=0.55,
        height=0.48,
        zorder=3,
    )
    for bar, value in zip(bars, values):
        ax.text(
            value + 0.022,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.5f}",
            va="center",
            fontsize=5.3 if compact else 6.2,
            color=INK,
            clip_on=False,
            zorder=4,
        )

    # Each threshold belongs to only one diagnostic row.  Short row-specific
    # lines avoid the misleading half-orange/half-blue background blocks.
    ax.vlines(0.65, -0.30, 0.30, color=S_COLOR, lw=1.4, zorder=4)
    ax.vlines(0.35, 0.70, 1.30, color=T_COLOR, lw=1.4, zorder=4)
    ax.text(
        1.045,
        -0.49,
        "E < 0.65: flag" if compact else "Endpoint threshold = 0.65; flag if E < 0.65",
        ha="right",
        va="center",
        color=S_COLOR,
        fontsize=5.1 if compact else 5.7,
    )
    ax.text(
        1.045,
        1.49,
        "M > 0.35: flag" if compact else "Missing threshold = 0.35; flag if M > 0.35",
        ha="right",
        va="center",
        color=T_COLOR,
        fontsize=5.1 if compact else 5.7,
    )
    ax.set_yticks(y, labels)
    ax.tick_params(axis="y", pad=6 if compact else 8, labelsize=5.3 if compact else 6.4)
    ax.set_xlim(0, 1.08)
    ax.set_ylim(-0.72, 1.72)
    ax.set_xlabel("Topology [0, 1]" if compact else "Topology diagnostic [0, 1]")
    ax.set_title(
        "target_01 topology" if compact else "target_01 topology diagnostics",
        pad=5,
        fontsize=5.8 if compact else 7.2,
    )
    ax.set_axisbelow(True)
    ax.grid(axis="x", color=GRID, lw=0.55)


def _figure5_images(context: PaperDiagnostics) -> tuple[tuple[int,int,np.ndarray], ...]:
    specifications=[]
    for target_index in (1,3):
        for candidate_index in (context.selected_indices[target_index],context.runner_up_indices[target_index]):
            image=registration_diagnostic_rgb(context.run.target_structures[target_index],context.run.reference_structures[candidate_index],context.run.matches[target_index][candidate_index]); specifications.append((target_index,candidate_index,image))
    return tuple(specifications)


def build_figure5(context: PaperDiagnostics) -> plt.Figure:
    images=_figure5_images(context); fig=plt.figure(figsize=(COMPOSITE_SIZES[4][0]/DPI,COMPOSITE_SIZES[4][1]/DPI),dpi=DPI)
    outer=fig.add_gridspec(3,4,left=0.055,right=0.985,bottom=0.105,top=0.875,wspace=0.72,hspace=0.66,height_ratios=(1.05,1.05,0.86))
    ax_a,ax_b,ax_c=fig.add_subplot(outer[0,0]),fig.add_subplot(outer[0,1]),fig.add_subplot(outer[0,2:]); ax_d,ax_e,ax_f=fig.add_subplot(outer[1,0]),fig.add_subplot(outer[1,1]),fig.add_subplot(outer[1,2:]); bottom=outer[2,:].subgridspec(1,2,wspace=0.38); ax_g,ax_h=fig.add_subplot(bottom[0,0]),fig.add_subplot(bottom[0,1])
    for ax,(target_index,candidate_index,image) in zip((ax_a,ax_b,ax_d,ax_e),images): image_panel(ax,image,f"{context.target_labels[target_index]}: {'selected' if candidate_index==context.selected_indices[target_index] else 'runner-up'} {context.reference_labels[candidate_index]}",context.score_matrix[target_index,candidate_index])
    component_panel(ax_c,context,1); component_panel(ax_f,context,3); bound_panel(ax_g,context); topology_panel(ax_h,context)
    top_y=outer[0,0].get_position(fig).y1+0.026; middle_y=outer[1,0].get_position(fig).y1+0.026; bottom_y=outer[2,0].get_position(fig).y1+0.026; left_x=outer[0,0].get_position(fig).x0-0.030; middle_x=outer[0,1].get_position(fig).x0-0.030; right_x=outer[0,2:].get_position(fig).x0-0.038
    for letter,x,y in (("a",left_x,top_y),("b",middle_x,top_y),("c",right_x,top_y),("d",left_x,middle_y),("e",middle_x,middle_y),("f",right_x,middle_y),("g",left_x,bottom_y),("h",right_x,bottom_y)): _figure_label(fig,letter,x,y)
    handles=(Patch(facecolor=TARGET_FOREGROUND,edgecolor="none",label="target foreground"),Line2D([0],[0],color=TARGET_SKELETON,lw=2,label="target skeleton"),Line2D([0],[0],color=REGISTERED_REFERENCE,lw=2,label="registered reference")); fig.legend(handles=handles,loc="upper center",ncols=3,bbox_to_anchor=(0.5,0.992)); fig.text(0.5,0.025,"Diagnostic sensitivity; not independent accuracy validation.",ha="center",color=MUTED,fontsize=6.0)
    return fig


def save_figure5_individuals(context: PaperDiagnostics, panel_dir: Path) -> list[Path]:
    saved=[]
    for letter,(target_index,candidate_index,image) in zip(("a","b","d","e"),_figure5_images(context)):
        p=panel_dir/f"suppfig5_{letter}_{context.target_labels[target_index]}_{context.reference_labels[candidate_index]}.png"; _save_rgb_panel(image,p); saved.append(p)
    for letter,target_index in (("c",1),("f",3)):
        p=panel_dir/f"suppfig5_{letter}_{context.target_labels[target_index]}_component_comparison.png"; fig=plt.figure(figsize=(PANEL_SIZE[0]/DPI,PANEL_SIZE[1]/DPI),dpi=DPI); ax=fig.add_axes((0.18,0.22,0.76,0.67)); component_panel(ax,context,target_index,compact=True); _save_figure(fig,p,PANEL_SIZE); saved.append(p)
    p=panel_dir/"suppfig5_g_target_03_search_bound_sensitivity.png"; fig=plt.figure(figsize=(PANEL_SIZE[0]/DPI,PANEL_SIZE[1]/DPI),dpi=DPI); ax=fig.add_axes((0.20,0.23,0.73,0.66)); bound_panel(ax,context,compact=True); _save_figure(fig,p,PANEL_SIZE); saved.append(p)
    p=panel_dir/"suppfig5_h_target_01_topology_diagnostics.png"; fig=plt.figure(figsize=(PANEL_SIZE[0]/DPI,PANEL_SIZE[1]/DPI),dpi=DPI); ax=fig.add_axes((0.26,0.23,0.68,0.66)); topology_panel(ax,context,compact=True); _save_figure(fig,p,PANEL_SIZE); saved.append(p)
    return saved


def generate_supplementary(context: PaperDiagnostics, outdir: Path, *, font_path: Path) -> tuple[list[Path], list[Path]]:
    outdir.mkdir(parents=True,exist_ok=True); panel_dir=outdir/"individual_panels"; panel_dir.mkdir(parents=True,exist_ok=True)
    composites=[outdir/name for name in COMPOSITE_NAMES]
    _save_composite_image(build_figure1(context,font_path),composites[0],COMPOSITE_SIZES[0]); _save_figure(build_figure2(context),composites[1],COMPOSITE_SIZES[1]); _save_figure(build_figure3(context),composites[2],COMPOSITE_SIZES[2]); _save_composite_image(build_figure4(context,font_path),composites[3],COMPOSITE_SIZES[3]); _save_figure(build_figure5(context),composites[4],COMPOSITE_SIZES[4])
    individuals=[]; individuals.extend(save_figure1_individuals(context,panel_dir)); individuals.extend(save_figure2_individuals(context,panel_dir)); individuals.extend(save_figure3_individuals(context,panel_dir)); individuals.extend(save_figure4_individuals(context,panel_dir)); individuals.extend(save_figure5_individuals(context,panel_dir))
    if len(individuals)!=42: raise RuntimeError(f"Expected 42 individual panels, generated {len(individuals)}")
    for path in composites: validate_png(path,expected_size=COMPOSITE_SIZES[composites.index(path)])
    for path in individuals: validate_png(path)
    return composites,individuals


def parse_args() -> argparse.Namespace:
    parser=argparse.ArgumentParser(description="Run matching and render the approved post-revision supplementary figures."); parser.add_argument("--targets",type=Path,default=DEFAULT_TARGETS); parser.add_argument("--references",type=Path,default=DEFAULT_REFERENCES); parser.add_argument("--outdir",type=Path,default=DEFAULT_OUTDIR); return parser.parse_args()


def main() -> None:
    args=parse_args(); font_path=configure_arial(); run=run_pipeline(args.targets,args.references); context=build_paper_diagnostics(run); composites,individuals=generate_supplementary(context,args.outdir.resolve(),font_path=font_path)
    for path in (*composites,*individuals): print(path)


if __name__=="__main__": main()
