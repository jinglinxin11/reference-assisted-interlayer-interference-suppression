from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from paper_figures.diagnostics import save_exact_rgb


REPO = Path(__file__).resolve().parents[1]


def test_standalone_rgb_export_preserves_every_pixel_and_dimension(tmp_path: Path) -> None:
    image = np.zeros((37, 53, 3), dtype=np.uint8)
    image[..., 0] = np.arange(53, dtype=np.uint8)[None, :]
    image[..., 1] = np.arange(37, dtype=np.uint8)[:, None]
    image[0, 0] = (1, 2, 3)
    image[-1, -1] = (253, 254, 255)
    output = tmp_path / "exact.png"

    save_exact_rgb(image, output)

    with Image.open(output) as opened:
        exported = np.array(opened.convert("RGB"), copy=True)
        assert opened.size == (53, 37)
    assert np.array_equal(exported, image)


def test_current_plotting_source_contains_no_frozen_manuscript_values() -> None:
    plotting_sources = (
        REPO / "paper_figures" / "diagnostics.py",
        REPO / "paper_figures" / "generate_figure_h_panels.py",
        REPO / "paper_figures" / "scripts" / "export_supplementary_figures.py",
    )
    forbidden = (
        "PAIRWISE_SCORES",
        "0.45394",
        "0.43013",
        "0.46251",
        "0.44853",
        "0.72131",
        "frozen transform",
    )

    for source in plotting_sources:
        text = source.read_text(encoding="utf-8")
        for value in forbidden:
            assert value not in text, f"{value!r} must not be frozen in {source.name}"


def test_figure_h_does_not_use_fixed_canvas_fitting_for_image_panels() -> None:
    source = (
        REPO / "paper_figures" / "generate_figure_h_panels.py"
    ).read_text(encoding="utf-8")

    assert "fit_panel" not in source
    assert "save_exact_rgb" in source
