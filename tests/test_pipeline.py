from pathlib import Path

import numpy as np

from microscopy_matching.pipeline import (
    DEFAULT_AUXILIARY_SCALE_BAR_UM,
    DEFAULT_TARGET_SCALE_BAR_UM,
    TARGET_REFERENCED_SEARCH,
    PipelineRun,
    SelectedMatch,
    minimal_results_payload,
)


def test_target_referenced_search_requires_the_physical_scale_window() -> None:
    assert DEFAULT_TARGET_SCALE_BAR_UM == 200.0
    assert DEFAULT_AUXILIARY_SCALE_BAR_UM == 500.0
    assert TARGET_REFERENCED_SEARCH.include_generic_scale_fallback
    assert TARGET_REFERENCED_SEARCH.physical_residual_scale_range == (0.60, 1.80)
    assert TARGET_REFERENCED_SEARCH.physical_residual_scale_count == 7
    assert TARGET_REFERENCED_SEARCH.fine_scale_half_width == 0.12
    assert TARGET_REFERENCED_SEARCH.physical_prior_weight == 0.08


def test_minimal_results_payload_contains_only_final_result_references() -> None:
    row = {
        "target_id": "target_01",
        "selected_label": "S",
        "selected_score": 0.5,
        "runner_up_label": "T",
        "margin": 0.1,
        "analysis_scale": 1.0,
        "analysis_angle_deg": 0.0,
        "analysis_dx": 1.0,
        "analysis_dy": 2.0,
        "physical_scale_mode": "target_200um_reference_500um_calibrated",
        "target_scale_bar_um": 200.0,
        "auxiliary_scale_bar_um": 500.0,
        "physical_scale_prior": 2.3,
        "physical_analysis_scale_residual": 1.1,
        "physical_scale_score": 0.9,
        "selected_native_bbox_xyxy": "1 2 3 4",
    }
    selection = SelectedMatch(
        target_index=0,
        candidate_index=0,
        target_path=Path("S.png"),
        candidate_path=Path("S.png"),
        target_original=np.zeros((1, 1, 3), dtype=np.uint8),
        target=None,  # type: ignore[arg-type]
        auxiliary=None,  # type: ignore[arg-type]
        match=None,  # type: ignore[arg-type]
        summary_row=row,
        rendered=np.zeros((1, 1, 3), dtype=np.uint8),
    )
    payload = minimal_results_payload(
        PipelineRun(Path("."), Path("."), (), (row,), (selection,))
    )

    assert payload["mode"] == "automatic_independent_target_200um_reference_500um_calibrated"
    assert payload["binary_rule"] == "target_foreground_and_registered_auxiliary_corridor"
    assert payload["results"] == [
        {
            "target_id": "target_01",
            "selected_label": "S",
            "selected_score": 0.5,
            "runner_up_label": "T",
            "margin": 0.1,
            "analysis_transform": {"scale": 1.0, "angle_deg": 0.0, "dx": 1.0, "dy": 2.0},
            "physical_scale": {
                "mode": "target_200um_reference_500um_calibrated",
                "target_scale_bar_um": 200.0,
                "auxiliary_scale_bar_um": 500.0,
                "analysis_prior": 2.3,
                "analysis_residual": 1.1,
                "score": 0.9,
            },
            "native_bbox_xyxy": "1 2 3 4",
            "presentation_file": "presentation/target_01_S.png",
            "binary_file": "binary/target_01_S.png",
        }
    ]
