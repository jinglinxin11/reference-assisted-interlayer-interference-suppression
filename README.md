# Microscopy Pattern Matching

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

The generated directory contains one `results.json`, four presentation PNGs,
and four matched-only binary PNGs. Generated artifacts are intentionally not
tracked by Git.

## Paper Figure H

Generate the submission-ready eight-panel algorithm workflow with Python:

```powershell
python -B paper_figures\generate_figure_h.py
```

The default output directory is `paper_figures/output/figure_h`. It contains
editable SVG, PDF, 300-dpi PNG, 600-dpi TIFF, the figure caption, score source
data, metadata, and a machine-readable QA report. Use `--target-code` to select
a different representative target while retaining the full S/Z/U/T score
matrix.

Generate only the reference-style middle eight panels in a snake layout:

```powershell
python -B paper_figures\generate_figure_h_middle_eight.py
```

Package the eight panels separately as 600-dpi PNG and RGB TIFF files:

```powershell
python -B paper_figures\package_figure_h_middle_panels.py
```

Generate the optional registration-landscape and corridor-sensitivity panels:

```powershell
python -B paper_figures\generate_optional_validation_figures.py
```

## Test

```powershell
python -B -m pytest -q -p no:cacheprovider tests\test_scale_calibration.py tests\test_topology_metrics.py tests\test_registration.py tests\test_evidence_mask.py tests\test_pipeline.py
```
