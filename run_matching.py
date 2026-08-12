"""Run auxiliary-guided microscopy matching and binary export."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from microscopy_matching.pipeline import (
    DEFAULT_AUXILIARY_SCALE_BAR_UM,
    DEFAULT_TARGET_SCALE_BAR_UM,
    run_pipeline,
    write_minimal_output,
)


DEFAULT_TARGETS = Path("data/input/target_images")
DEFAULT_REFERENCES = Path("data/input/reference_images")
DEFAULT_OUTDIR = Path("artifacts/matching_results")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets", type=Path, default=DEFAULT_TARGETS)
    parser.add_argument("--references", type=Path, default=DEFAULT_REFERENCES)
    parser.add_argument("--outdir", type=Path, default=DEFAULT_OUTDIR)
    parser.add_argument(
        "--target-scale-bar-um",
        type=float,
        default=DEFAULT_TARGET_SCALE_BAR_UM,
        help="Validated physical length of the target-image scale bar (default: 200).",
    )
    parser.add_argument(
        "--reference-scale-bar-um",
        type=float,
        default=DEFAULT_AUXILIARY_SCALE_BAR_UM,
        help="Validated physical length of the reference-image scale bar (default: 500).",
    )
    args = parser.parse_args()
    run = run_pipeline(
        args.targets,
        args.references,
        target_scale_bar_um=args.target_scale_bar_um,
        auxiliary_scale_bar_um=args.reference_scale_bar_um,
    )
    payload = write_minimal_output(run, args.outdir)
    print(json.dumps({"outdir": str(args.outdir.resolve()), "results": payload["results"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
