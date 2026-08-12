"""Data-derived diagnostics shared by all manuscript figures.

Every array in this module is computed from one :class:`PipelineRun`.  No
manuscript score, transform, sensitivity curve, or microscopy crop is stored as
a plotting constant.
"""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path

import cv2
import matplotlib as mpl
import numpy as np
from PIL import Image, ImageDraw

from microscopy_matching.image_processing import Structure, corridor_from_points
from microscopy_matching.pipeline import PipelineRun, TARGET_REFERENCED_SEARCH
from microscopy_matching.registration import (
    UnifiedMatch,
    refine_candidate,
    transform_points,
    translation_score_landscape,
    warp_auxiliary_skeleton,
)


DPI = 600
PANEL_SIZE = (946, 820)
CORRIDOR_RADIUS = 12
TARGET_DISPLAY_SCALE_BAR_UM = 200.0
TRANSLATION_OFFSETS = np.linspace(-24.0, 24.0, 41)
RADIUS_VALUES = np.arange(2, 31, dtype=int)
SEARCH_BOUND_VALUES = np.asarray((1.60, 1.75, 1.90), dtype=np.float64)


def configure_arial() -> Path:
    candidates = (
        (Path("C:/Windows/Fonts/arial.ttf"), Path("C:/Windows/Fonts/arialbd.ttf")),
        (
            Path("/usr/share/fonts/truetype/msttcorefonts/Arial.ttf"),
            Path("/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf"),
        ),
        (
            Path("/usr/share/fonts/truetype/msttcorefonts/arial.ttf"),
            Path("/usr/share/fonts/truetype/msttcorefonts/arialbd.ttf"),
        ),
    )
    selected = next(
        ((regular, bold) for regular, bold in candidates if regular.is_file() and bold.is_file()),
        None,
    )
    if selected is None:
        raise RuntimeError("Arial and Arial Bold are required to render the manuscript figures.")
    regular, bold = selected
    mpl.font_manager.fontManager.addfont(str(regular))
    mpl.font_manager.fontManager.addfont(str(bold))
    mpl.rcParams.update(
        {
            "font.family": "Arial",
            "font.sans-serif": ["Arial"],
            "font.size": 7.0,
            "axes.labelsize": 7.2,
            "axes.titlesize": 7.2,
            "xtick.labelsize": 6.4,
            "ytick.labelsize": 6.4,
            "legend.fontsize": 6.0,
            "axes.linewidth": 0.75,
            "xtick.major.width": 0.75,
            "ytick.major.width": 0.75,
            "xtick.major.size": 2.5,
            "ytick.major.size": 2.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "savefig.facecolor": "white",
            "figure.facecolor": "white",
            "pdf.fonttype": 42,
            "svg.fonttype": "none",
        }
    )
    return regular


def validate_png(path: Path, *, expected_size: tuple[int, int] | None = None) -> None:
    with Image.open(path) as image:
        if image.format != "PNG" or image.mode != "RGB":
            raise RuntimeError(f"Expected RGB PNG output: {path}")
        if expected_size is not None and image.size != expected_size:
            raise RuntimeError(f"Unexpected PNG size for {path.name}: {image.size}")
        dpi = image.info.get("dpi", (0.0, 0.0))
        if any(abs(float(value) - DPI) > 1.0 for value in dpi):
            raise RuntimeError(f"Unexpected PNG resolution for {path.name}: {dpi}")


@dataclass(frozen=True)
class RadiusMetric:
    radius_px: int
    precision: float
    recall: float
    dice: float


@dataclass(frozen=True)
class PaperDiagnostics:
    run: PipelineRun
    score_matrix: np.ndarray
    selected_indices: tuple[int, ...]
    runner_up_indices: tuple[int, ...]
    representative_index: int
    translation_offsets: np.ndarray
    translation_scores: np.ndarray
    radius_metrics: tuple[RadiusMetric, ...]
    radius_metrics_by_target: tuple[tuple[RadiusMetric, ...], ...]
    search_bound_values: np.ndarray
    search_bound_scores: np.ndarray

    @property
    def target_labels(self) -> tuple[str, ...]:
        return tuple(path.stem for path in self.run.target_paths)

    @property
    def reference_labels(self) -> tuple[str, ...]:
        return tuple(path.stem for path in self.run.reference_paths)


def _require_full_run(run: PipelineRun) -> None:
    collections = (
        run.target_paths,
        run.reference_paths,
        run.target_images,
        run.reference_images,
        run.target_structures,
        run.reference_structures,
        run.target_calibrations,
        run.reference_calibrations,
        run.matches,
    )
    if any(len(collection) != 4 for collection in collections):
        raise RuntimeError("Paper diagnostics require a complete four-by-four PipelineRun.")
    if any(len(row) != 4 for row in run.matches):
        raise RuntimeError("Paper diagnostics require all sixteen candidate matches.")


def build_paper_diagnostics(run: PipelineRun) -> PaperDiagnostics:
    """Build all numerical diagnostics from one algorithm run."""

    _require_full_run(run)
    scores = np.asarray(
        [[match.score for match in target_matches] for target_matches in run.matches],
        dtype=np.float64,
    )
    ranked = np.argsort(scores, axis=1)[:, ::-1]
    selected = tuple(int(value) for value in ranked[:, 0])
    runners = tuple(int(value) for value in ranked[:, 1])
    # The original manuscript figures use target_01 -> S as the worked example.
    # Preserve that scientific panel contract while recomputing every value from
    # the current raw inputs and algorithm.
    representative = 0

    representative_match = run.matches[representative][selected[representative]]
    prior_confidence = float(
        min(
            run.target_calibrations[representative].confidence,
            run.reference_calibrations[selected[representative]].confidence,
        )
    )
    landscape = translation_score_landscape(
        run.target_structures[representative],
        run.reference_structures[selected[representative]],
        representative_match,
        TRANSLATION_OFFSETS,
        TRANSLATION_OFFSETS,
        physical_prior_confidence=prior_confidence,
    )
    radius_by_target = tuple(
        corridor_radius_metrics(
            run.target_structures[target_index],
            run.reference_structures[selected[target_index]],
            run.matches[target_index][selected[target_index]],
            RADIUS_VALUES,
        )
        for target_index in range(4)
    )
    radius_metrics = tuple(
        RadiusMetric(
            radius_px=int(radius),
            precision=float(np.median([case[index].precision for case in radius_by_target])),
            recall=float(np.median([case[index].recall for case in radius_by_target])),
            dice=float(np.median([case[index].dice for case in radius_by_target])),
        )
        for index, radius in enumerate(RADIUS_VALUES)
    )

    # Recreate the original target_03 scale-bound sensitivity panel by actually
    # rerunning the current physical-scale-constrained search at each bound.
    sensitivity_target = 2
    search_scores = np.empty((len(SEARCH_BOUND_VALUES), 4), dtype=np.float64)
    for bound_index, upper_bound in enumerate(SEARCH_BOUND_VALUES):
        config = replace(
            TARGET_REFERENCED_SEARCH,
            physical_residual_scale_range=(0.60, float(upper_bound)),
        )
        for candidate_index in range(4):
            base_match = run.matches[sensitivity_target][candidate_index]
            confidence = float(
                min(
                    run.target_calibrations[sensitivity_target].confidence,
                    run.reference_calibrations[candidate_index].confidence,
                )
            )
            rerun = refine_candidate(
                run.target_structures[sensitivity_target],
                run.reference_structures[candidate_index],
                physical_scale_prior=base_match.physical_scale_prior,
                physical_prior_confidence=confidence,
                physical_scale_available=base_match.physical_scale_available,
                config=config,
            )
            search_scores[bound_index, candidate_index] = rerun.score
    return PaperDiagnostics(
        run=run,
        score_matrix=scores,
        selected_indices=selected,
        runner_up_indices=runners,
        representative_index=representative,
        translation_offsets=TRANSLATION_OFFSETS.copy(),
        translation_scores=landscape,
        radius_metrics=radius_metrics,
        radius_metrics_by_target=radius_by_target,
        search_bound_values=SEARCH_BOUND_VALUES.copy(),
        search_bound_scores=search_scores,
    )


def transformed_reference_points(auxiliary: Structure, match: UnifiedMatch) -> np.ndarray:
    points = np.argwhere(auxiliary.skeleton)[:, ::-1].astype(np.float32)
    return transform_points(
        points,
        auxiliary.bbox,
        match.scale,
        match.angle_deg,
        match.dx,
        match.dy,
    )


def corridor_radius_metrics(
    target: Structure,
    auxiliary: Structure,
    match: UnifiedMatch,
    radii: np.ndarray,
) -> tuple[RadiusMetric, ...]:
    """Return target/corridor precision, recall, and Dice for each radius."""

    points = transformed_reference_points(auxiliary, match)
    target_count = max(1, int(np.count_nonzero(target.mask)))
    records: list[RadiusMetric] = []
    for radius in np.asarray(radii, dtype=int):
        if radius < 1:
            raise ValueError("Corridor radii must be positive integers.")
        corridor = corridor_from_points(target.mask.shape, points, radius=int(radius))
        corridor_count = max(1, int(np.count_nonzero(corridor)))
        intersection = int(np.count_nonzero(target.mask & corridor))
        precision = intersection / corridor_count
        recall = intersection / target_count
        dice = 2.0 * intersection / max(1, target_count + corridor_count)
        records.append(
            RadiusMetric(
                radius_px=int(radius),
                precision=float(precision),
                recall=float(recall),
                dice=float(dice),
            )
        )
    return tuple(records)


def match_for(context: PaperDiagnostics, target_index: int, candidate_index: int) -> UnifiedMatch:
    return context.run.matches[target_index][candidate_index]


def pair_row_for(
    context: PaperDiagnostics,
    target_index: int,
    candidate_index: int,
) -> dict[str, object]:
    target_id = f"target_{target_index + 1:02d}"
    candidate_id = f"candidate_{candidate_index + 1:02d}"
    return next(
        row
        for row in context.run.pair_rows
        if row["target_id"] == target_id and row["candidate_id"] == candidate_id
    )


def response_rgb(structure: Structure) -> np.ndarray:
    brown_response = mpl.colors.LinearSegmentedColormap.from_list(
        "brown_response",
        ("#fffaf1", "#f3cfaa", "#c47a55", "#6b342a", "#1b1110"),
    )
    rgba = brown_response(np.clip(structure.response, 0.0, 1.0))
    return np.asarray(np.rint(rgba[..., :3] * 255.0), dtype=np.uint8)


def skeleton_rgb(structure: Structure) -> np.ndarray:
    image = np.full((*structure.mask.shape, 3), (12, 26, 32), dtype=np.uint8)
    image[structure.mask] = (236, 194, 119)
    image[structure.skeleton] = (43, 184, 207)
    return image


def corridor_overlay_rgb(
    target: Structure,
    auxiliary: Structure,
    match: UnifiedMatch,
    *,
    radius: int = CORRIDOR_RADIUS,
) -> np.ndarray:
    base = np.full((*target.mask.shape, 3), (12, 26, 32), dtype=np.uint8)
    points = transformed_reference_points(auxiliary, match)
    corridor = corridor_from_points(target.mask.shape, points, radius=radius)
    aligned = warp_auxiliary_skeleton(
        auxiliary,
        target.mask.shape,
        scale=match.scale,
        angle_deg=match.angle_deg,
        dx=match.dx,
        dy=match.dy,
    )
    base[corridor] = (18, 63, 68)
    base[target.mask] = (143, 157, 163)
    base[target.mask & corridor] = (232, 107, 82)
    base[aligned] = (112, 222, 229)
    return base


def strict_mask_rgb(
    target: Structure,
    auxiliary: Structure,
    match: UnifiedMatch,
    *,
    radius: int = CORRIDOR_RADIUS,
) -> np.ndarray:
    corridor = corridor_from_points(
        target.mask.shape,
        transformed_reference_points(auxiliary, match),
        radius=radius,
    )
    strict = target.mask & corridor
    image = np.zeros((*strict.shape, 3), dtype=np.uint8)
    image[strict] = (255, 255, 255)
    return image


def registration_diagnostic_rgb(
    target: Structure,
    auxiliary: Structure,
    match: UnifiedMatch,
) -> np.ndarray:
    """Original supplementary diagnostic colours on the current registration."""

    aligned = warp_auxiliary_skeleton(
        auxiliary,
        target.mask.shape,
        scale=match.scale,
        angle_deg=match.angle_deg,
        dx=match.dx,
        dy=match.dy,
    )
    image = np.full((*target.mask.shape, 3), (12, 26, 32), dtype=np.uint8)
    image[target.mask] = (174, 185, 190)
    image[target.skeleton] = (85, 169, 212)
    image[aligned] = (230, 160, 0)
    return image


def presentation_rgb(context: PaperDiagnostics, target_index: int) -> np.ndarray:
    return cv2.cvtColor(context.run.selections[target_index].rendered, cv2.COLOR_BGR2RGB)


def native_reference_rgb(context: PaperDiagnostics, candidate_index: int) -> np.ndarray:
    return cv2.cvtColor(context.run.reference_images[candidate_index], cv2.COLOR_BGR2RGB)


def _analysis_pixels_per_um(
    image: np.ndarray,
    structure: Structure,
    pixels_per_um: float | None,
) -> float:
    if pixels_per_um is None or pixels_per_um <= 0.0:
        raise RuntimeError("A successful scale-bar calibration is required for manuscript display.")
    resize_x = structure.image.shape[1] / float(image.shape[1])
    resize_y = structure.image.shape[0] / float(image.shape[0])
    if not np.isclose(resize_x, resize_y, rtol=0.02, atol=1e-6):
        raise RuntimeError("Analysis resize is not isotropic; physical display would be ambiguous.")
    return float(pixels_per_um) * float((resize_x + resize_y) * 0.5)


def target_analysis_pixels_per_um(
    context: PaperDiagnostics,
    target_index: int = 0,
) -> float:
    """Return the target-referenced analysis sampling used by manuscript images."""

    return _analysis_pixels_per_um(
        context.run.target_images[target_index],
        context.run.target_structures[target_index],
        context.run.target_calibrations[target_index].pixels_per_um,
    )


def _remove_detected_scale_annotation(
    image_rgb: np.ndarray,
    native_shape: tuple[int, int],
    bbox_xyxy: tuple[int, int, int, int] | None,
) -> np.ndarray:
    """Remove only the detected acquisition annotation before relabelling the view."""

    cleaned = np.asarray(image_rgb, dtype=np.uint8).copy()
    if bbox_xyxy is None:
        raise RuntimeError("The native reference scale annotation was not localized.")
    native_height, native_width = native_shape
    x0, y0, x1, y1 = bbox_xyxy
    scale_x = cleaned.shape[1] / float(native_width)
    scale_y = cleaned.shape[0] / float(native_height)
    x0 = max(0, int(np.floor(x0 * scale_x)) - 4)
    y0 = max(0, int(np.floor(y0 * scale_y)) - 4)
    x1 = min(cleaned.shape[1], int(np.ceil(x1 * scale_x)) + 4)
    y1 = min(cleaned.shape[0], int(np.ceil(y1 * scale_y)) + 4)
    if x1 <= x0 or y1 <= y0:
        raise RuntimeError("Detected scale annotation maps outside the analysis image.")

    ring = 10
    rx0, ry0 = max(0, x0 - ring), max(0, y0 - ring)
    rx1, ry1 = min(cleaned.shape[1], x1 + ring), min(cleaned.shape[0], y1 + ring)
    surround = cleaned[ry0:ry1, rx0:rx1].reshape(-1, 3)
    fill = np.asarray(np.median(surround, axis=0), dtype=np.uint8)
    cleaned[y0:y1, x0:x1] = fill
    return cleaned


def target_referenced_reference_rgb(
    context: PaperDiagnostics,
    candidate_index: int,
    *,
    representation: str = "image",
    target_index: int = 0,
) -> np.ndarray:
    """Resample one native-500-um reference to target-referenced analysis sampling.

    The full reference field is retained.  Only the acquisition scale annotation
    is removed before the image is resampled; a 200-um manuscript annotation is
    added later by the renderer.  No content-dependent crop or zoom is applied.
    """

    structure = context.run.reference_structures[candidate_index]
    calibration = context.run.reference_calibrations[candidate_index]
    reference_ppu = _analysis_pixels_per_um(
        context.run.reference_images[candidate_index],
        structure,
        calibration.pixels_per_um,
    )
    target_ppu = target_analysis_pixels_per_um(context, target_index)
    scale = target_ppu / reference_ppu
    if not np.isfinite(scale) or scale <= 0.0:
        raise RuntimeError("Invalid target/reference physical resampling factor.")

    if representation == "image":
        source = cv2.cvtColor(structure.image, cv2.COLOR_BGR2RGB)
        source = _remove_detected_scale_annotation(
            source,
            context.run.reference_images[candidate_index].shape[:2],
            calibration.bar_bbox_xyxy,
        )
        interpolation = cv2.INTER_LANCZOS4
    elif representation == "analysis":
        source = np.full((*structure.mask.shape, 3), (12, 26, 32), dtype=np.uint8)
        source[structure.mask] = (207, 221, 224)
        source[structure.skeleton] = (85, 190, 210)
        interpolation = cv2.INTER_NEAREST
    else:
        raise ValueError("representation must be 'image' or 'analysis'")

    output_width = max(1, int(round(source.shape[1] * scale)))
    output_height = max(1, int(round(source.shape[0] * scale)))
    return cv2.resize(source, (output_width, output_height), interpolation=interpolation)


def fit_panel(
    image_rgb: np.ndarray,
    *,
    size: tuple[int, int] = PANEL_SIZE,
    background: tuple[int, int, int] = (255, 255, 255),
    margin: int = 26,
    border: bool = True,
) -> Image.Image:
    """Fit one image into a fixed, non-cropping manuscript panel."""

    array = np.asarray(image_rgb, dtype=np.uint8)
    image = Image.fromarray(array, mode="RGB")
    image.thumbnail((size[0] - 2 * margin, size[1] - 2 * margin), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, background)
    x = (size[0] - image.width) // 2
    y = (size[1] - image.height) // 2
    canvas.paste(image, (x, y))
    if border:
        ImageDraw.Draw(canvas).rectangle(
            (1, 1, size[0] - 2, size[1] - 2),
            outline=(165, 176, 181),
            width=2,
        )
    return canvas


def save_exact_rgb(image_rgb: np.ndarray, destination: Path) -> Path:
    """Save an RGB array without cropping, resizing, padding, or adding a border.

    This is the only valid export path for standalone microscopy-derived
    panels.  Fixed-size manuscript composition belongs in a later assembly
    step; it must never modify the underlying single-panel evidence image.
    """

    array = np.asarray(image_rgb)
    if array.ndim != 3 or array.shape[2] != 3:
        raise ValueError(f"Expected an H x W x 3 RGB array, received {array.shape}")
    if array.dtype != np.uint8:
        if not np.isfinite(array).all():
            raise ValueError("RGB image contains non-finite values")
        array = np.asarray(np.clip(np.rint(array), 0, 255), dtype=np.uint8)

    destination.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(array, mode="RGB").save(
        destination,
        format="PNG",
        dpi=(DPI, DPI),
        optimize=True,
    )
    validate_png(destination, expected_size=(array.shape[1], array.shape[0]))
    return destination


def save_panel_image(image_rgb: np.ndarray, destination: Path) -> Path:
    """Backward-compatible alias for a geometry-preserving RGB export."""

    return save_exact_rgb(image_rgb, destination)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_diagnostic_tables(context: PaperDiagnostics, outdir: Path) -> list[Path]:
    """Write reviewer-readable numerical provenance for every plotted result."""

    outdir.mkdir(parents=True, exist_ok=True)
    pair_path = outdir / "pairwise_matches.csv"
    with pair_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(context.run.pair_rows[0].keys()))
        writer.writeheader()
        writer.writerows(context.run.pair_rows)

    summary_path = outdir / "selected_matches.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(context.run.summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(context.run.summary_rows)

    radius_path = outdir / "corridor_radius_sensitivity.csv"
    with radius_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("target_id", "selected_reference", "radius_px", "precision", "recall", "dice"),
        )
        writer.writeheader()
        for target_index, records in enumerate(context.radius_metrics_by_target):
            for record in records:
                writer.writerow(
                    {
                        "target_id": context.target_labels[target_index],
                        "selected_reference": context.reference_labels[context.selected_indices[target_index]],
                        **record.__dict__,
                    }
                )
        for record in context.radius_metrics:
            writer.writerow(
                {
                    "target_id": "median",
                    "selected_reference": "all_selected_pairs",
                    **record.__dict__,
                }
            )

    landscape_path = outdir / "translation_landscape.csv"
    with landscape_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("dy_offset_px\\dx_offset_px", *context.translation_offsets.tolist()))
        for offset, scores in zip(context.translation_offsets, context.translation_scores):
            writer.writerow((float(offset), *scores.tolist()))

    bound_path = outdir / "search_bound_sensitivity.csv"
    with bound_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("physical_residual_scale_upper_bound", *context.reference_labels))
        for bound, scores in zip(context.search_bound_values, context.search_bound_scores):
            writer.writerow((float(bound), *scores.tolist()))

    manifest = {
        "physical_scale_convention": {
            "target_native_scale_bar_um": TARGET_DISPLAY_SCALE_BAR_UM,
            "reference_native_scale_bar_um": 500.0,
            "manuscript_display_scale_bar_um": TARGET_DISPLAY_SCALE_BAR_UM,
            "reference_display_transform": (
                "full-field isotropic resampling from the native 500-um reference "
                "calibration to target_01 analysis pixels per micrometre; the detected "
                "native annotation is removed, candidates are placed on one common "
                "physical canvas with background-only padding, and a 200-um display "
                "annotation is added"
            ),
            "target_analysis_pixels_per_um": target_analysis_pixels_per_um(context),
            "target_calibrations": [
                {
                    "file": path.name,
                    "pixels_per_um": calibration.pixels_per_um,
                    "confidence": calibration.confidence,
                    "source": calibration.source,
                }
                for path, calibration in zip(
                    context.run.target_paths,
                    context.run.target_calibrations,
                )
            ],
            "reference_calibrations": [
                {
                    "file": path.name,
                    "pixels_per_um": calibration.pixels_per_um,
                    "confidence": calibration.confidence,
                    "source": calibration.source,
                }
                for path, calibration in zip(
                    context.run.reference_paths,
                    context.run.reference_calibrations,
                )
            ],
        },
        "input_files": {
            "targets": [
                {"name": path.name, "sha256": _sha256(path)}
                for path in context.run.target_paths
            ],
            "references": [
                {"name": path.name, "sha256": _sha256(path)}
                for path in context.run.reference_paths
            ],
        },
        "representative_target": context.target_labels[context.representative_index],
        "representative_selection": context.reference_labels[
            context.selected_indices[context.representative_index]
        ],
        "translation_landscape": {
            "definition": "registration geometry objective at fixed selected scale and rotation",
            "offset_min_px": float(context.translation_offsets.min()),
            "offset_max_px": float(context.translation_offsets.max()),
            "samples_per_axis": int(len(context.translation_offsets)),
        },
        "corridor_sensitivity": {
            "precision": "target foreground inside corridor / corridor pixels",
            "recall": "target foreground inside corridor / all target foreground",
            "dice": "2 * intersection / (target foreground pixels + corridor pixels)",
            "selected_radius_px": CORRIDOR_RADIUS,
        },
        "search_bound_sensitivity": {
            "target": context.target_labels[2],
            "definition": "current registration rerun with physical residual scale upper bound varied",
            "upper_bounds": context.search_bound_values.tolist(),
            "scores": context.search_bound_scores.tolist(),
        },
        "pairwise_matches": list(context.run.pair_rows),
        "selected_matches": list(context.run.summary_rows),
    }
    manifest_path = outdir / "diagnostics.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return [pair_path, summary_path, radius_path, landscape_path, bound_path, manifest_path]
