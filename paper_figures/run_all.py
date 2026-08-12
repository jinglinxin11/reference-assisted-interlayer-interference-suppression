"""Single reviewer entry point: raw images -> algorithm -> all paper figures."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PAPER = REPO / "paper_figures"
REQUIREMENTS = REPO / "requirements.txt"
GENERATED = PAPER / "generated"
DEFAULT_TARGETS = REPO / "data" / "input" / "target_images"
DEFAULT_REFERENCES = REPO / "data" / "input" / "reference_images"


def environment_python(environment: Path) -> Path:
    if sys.platform == "win32":
        return environment / "Scripts" / "python.exe"
    return environment / "bin" / "python"


def clean_generated_directory() -> None:
    generated = GENERATED.resolve()
    paper = PAPER.resolve()
    if generated == paper or paper not in generated.parents:
        raise RuntimeError(f"Refusing to clean unsafe path: {generated}")
    if generated.exists():
        shutil.rmtree(generated)
    generated.mkdir(parents=True, exist_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create an isolated environment, run matching from four target and "
            "four reference images, and generate every manuscript figure."
        )
    )
    parser.add_argument("--targets", type=Path, default=DEFAULT_TARGETS)
    parser.add_argument("--references", type=Path, default=DEFAULT_REFERENCES)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    targets = args.targets.resolve()
    references = args.references.resolve()
    if not targets.is_dir() or not references.is_dir():
        raise FileNotFoundError("Both --targets and --references must be existing directories.")

    clean_generated_directory()
    with tempfile.TemporaryDirectory(prefix="microscopy-paper-reproduction-") as temp_dir:
        environment = Path(temp_dir) / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment_python(environment)
        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "-r",
                str(REQUIREMENTS),
            ],
            cwd=REPO,
            check=True,
        )
        subprocess.run(
            [
                str(python),
                "-B",
                "-m",
                "paper_figures.generate_all",
                "--targets",
                str(targets),
                "--references",
                str(references),
                "--outdir",
                str(GENERATED),
            ],
            cwd=REPO,
            check=True,
        )


if __name__ == "__main__":
    main()

