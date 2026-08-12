"""Run the matching algorithm once and generate every manuscript figure."""

from __future__ import annotations

import argparse
from pathlib import Path

from microscopy_matching.pipeline import run_pipeline, write_minimal_output
from paper_figures.diagnostics import (
    build_paper_diagnostics,
    configure_arial,
    write_diagnostic_tables,
)
from paper_figures.generate_figure_h_panels import generate_figure_h
from paper_figures.scripts.export_supplementary_figures import generate_supplementary


REPO = Path(__file__).resolve().parents[1]
DEFAULT_TARGETS = REPO / "data" / "input" / "target_images"
DEFAULT_REFERENCES = REPO / "data" / "input" / "reference_images"
DEFAULT_OUTDIR = Path(__file__).resolve().parent / "generated"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run four-by-four microscopy matching and generate Figure H, "
            "all supplementary figures, and numerical source data."
        )
    )
    parser.add_argument("--targets", type=Path, default=DEFAULT_TARGETS)
    parser.add_argument("--references", type=Path, default=DEFAULT_REFERENCES)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    targets = args.targets.resolve()
    references = args.references.resolve()
    outdir = args.outdir.resolve()
    outdir.mkdir(parents=True, exist_ok=True)

    font_path = configure_arial()
    print(f"Arial resolved for all manuscript figures: {font_path}")
    print(f"Running matching from targets: {targets}")
    print(f"Running matching from references: {references}")
    run = run_pipeline(targets, references)
    context = build_paper_diagnostics(run)

    algorithm_dir = outdir / "algorithm_results"
    diagnostics_dir = outdir / "diagnostics"
    figure_h_dir = outdir / "figure_h"
    supplementary_dir = outdir / "supplementary"

    write_minimal_output(run, algorithm_dir)
    diagnostic_paths = write_diagnostic_tables(context, diagnostics_dir)
    figure_h_paths = generate_figure_h(context, figure_h_dir, font_path=font_path)
    composite_paths, individual_paths = generate_supplementary(
        context,
        supplementary_dir,
        font_path=font_path,
    )

    print(
        "Generated "
        f"{len(figure_h_paths)} Figure H panels, "
        f"{len(composite_paths)} supplementary composites, "
        f"{len(individual_paths)} supplementary panels, and "
        f"{len(diagnostic_paths)} diagnostic tables."
    )
    print(f"Representative target: {context.target_labels[context.representative_index]}")
    print(
        "Representative reference: "
        f"{context.reference_labels[context.selected_indices[context.representative_index]]}"
    )


if __name__ == "__main__":
    main()
