# Reproducing Supplementary Figure S14

This directory contains the two reviewer-facing plotting entry points for the
248 nm UV versus 976 nm NIR spatial-confinement comparison:

- `plot_figure_s14.py` regenerates the complete eight-panel Figure S14.
- `export_figure_s14_panels.py` regenerates the eight logical panels as
  separate files. Panel e remains a 2 × 3 ROI-profile grid because those six
  ROI plots jointly form panel e in the submitted composite.

Both scripts read the same committed figure-level source data and use the same
plotting helpers. They do not modify the source files. Before plotting, each
script checks all 138 archived inputs against `source_data_manifest.json` and
stops if a file is missing or its SHA-256 digest has changed.

## Scope of the reproduction

The commands below reproduce the published plotting stage from the archived
registered images, frozen ROI coordinates, ROI-level metrics and profile
traces. They do not rerun image registration, ROI selection or metric
calculation. The upstream settings and analysis record are retained under
`source_data/analysis_config.json` and `source_data/analysis_pipeline.md` so
that the provenance and inference boundary remain explicit.

In the archived files, the condition labels map as follows:

| archived label | manuscript condition |
| --- | --- |
| `before` | 248 nm UV writing |
| `after` | 976 nm NIR writing |

## Requirements

- Python 3.12 is recommended; the submitted figure was generated with Python
  3.12.13.
- Arial must be installed. The scripts stop instead of silently substituting a
  different font.
- The exact plotting-package versions are pinned in this directory's
  `requirements.txt`.

From the repository root, create an isolated environment and install the
Figure S14 dependencies.

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r paper_figures\figure_s14\requirements.txt
```

Linux or macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r paper_figures/figure_s14/requirements.txt
```

## Reproduce the complete Figure S14

Windows PowerShell:

```powershell
.venv\Scripts\python paper_figures\figure_s14\plot_figure_s14.py
```

Linux or macOS:

```bash
.venv/bin/python paper_figures/figure_s14/plot_figure_s14.py
```

The default output folder is
`paper_figures/generated/figure_s14/composite/`. The script writes:

- `Figure_S14.pdf`
- `Figure_S14.svg`
- `Figure_S14.png` at 600 dpi
- `Figure_S14.tif` at 600 dpi with LZW compression
- `Figure_S14_manifest.json`, including source paths, software versions,
  paired-ROI counts, ExR display limits and output SHA-256 values

Use `--output-dir PATH` to select another output folder.

## Reproduce the eight standalone panels

Windows PowerShell:

```powershell
.venv\Scripts\python paper_figures\figure_s14\export_figure_s14_panels.py
```

Linux or macOS:

```bash
.venv/bin/python paper_figures/figure_s14/export_figure_s14_panels.py
```

The default output folder is
`paper_figures/generated/figure_s14/individual_panels/`. Each logical panel
from a through h is exported as PDF, SVG, 600 dpi PNG and 600 dpi
LZW-compressed TIFF. The folder also contains
`Figure_S14_individual_panels_manifest.json` with output hashes and the shared
display settings.

## Expected checks

A successful run should report:

- shared ExR display limits: pooled P1–P99, `vmin = 131.0` and `vmax = 222.0`;
- complete spatial ROI pairs: 6 for edge width, 6 for FWHM and 5 for decay
  distance;
- R03 excluded from both groups only in the paired decay-distance panel
  because the UV decay crossing is missing;
- no stochastic operation in either plotting script.

The 11 neighbouring traces within each ROI are spatial subsamples, not
independent material replicates. The outputs therefore reproduce descriptive
measurements from one registered image pair and do not add a between-material
hypothesis test.

## Committed source data

```text
source_data/
  uv_248nm_registered_common_grid.tif
  nir_976nm_reference.tif
  roi_coordinates.csv
  roi_level_metrics.csv
  profiles/                         132 profile CSV files
  analysis_config.json
  analysis_pipeline.md
```

Generated figures are intentionally excluded from Git. The reproducible
release is defined by the committed scripts, source data, checksum manifest
and an immutable Git commit identifier, rather than by cached local figures.
