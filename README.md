# Microscopy Deghosting

This project performs label-free, independent matching between target
microscopy images and structural reference images. It registers each reference
to a target, retains only target evidence inside the selected corridor, and
exports both a natural-background presentation image and a non-fabricating
binary mask.

## Input Layout

```text
data/input/
  target_images/       # Four target JPG or PNG images, ordered by filename
  reference_images/    # Four reference PNG images; filenames supply labels
```

The committed targets are byte-identical copies of the four main-directory
JPEG images. The reference PNGs are byte-identical copies of the verified
auxiliary images.

## Run

```powershell
python -m pip install -r requirements.txt
python -B run_matching.py --targets data\input\target_images --references data\input\reference_images --outdir artifacts\matching_results
```

On Linux or macOS, use forward slashes:

```bash
python -m pip install -r requirements.txt
python -B run_matching.py --targets data/input/target_images --references data/input/reference_images --outdir artifacts/matching_results
```

The generated directory contains one `results.json`, four presentation PNGs,
and four matched-only binary PNGs. Generated artifacts are intentionally not
tracked by Git.

## Test

```powershell
python -B -m pytest -q tests
```

## Paper-figure code

The reviewer entry point under [`paper_figures/`](paper_figures/README.md)
runs the four-by-four matching algorithm directly from `data/input/`, writes
all plotted diagnostic values, and exports eight standalone Figure H PNG
panels, five complete supplementary figures, and all 42 constituent
supplementary panels from that same run:

```powershell
python paper_figures/run_all.py
```

It requires Arial and does not generate a ZIP, Word document, PDF, SVG, or
TIFF. No manuscript score or sensitivity curve is loaded from a frozen figure.

Generated manuscript figures are intentionally not tracked by Git. Reviewers
recreate them from the committed input images and current algorithm with the
single command above. This prevents stale or manually post-processed PNG files
from diverging from the published source code.
