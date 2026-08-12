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

## Physical-scale convention

The two input sets do not use the same acquisition annotation:

| image set | validated native scale-bar length | role in the workflow |
| --- | ---: | --- |
| target images | 200 µm | defines the manuscript display coordinate system |
| reference images | 500 µm | calibrates reference pixels before registration |

The program detects the scale-bar graphic but does not infer its text by OCR.
The validated lengths above are explicit defaults and are recorded in the
generated JSON/CSV provenance. Reference images are calibrated at 500 µm for
the numerical registration; any reference view exported for the manuscript is
then isotropically resampled to target-referenced sampling and labelled with a
200 µm bar. A common physical canvas is formed with background-only padding,
so the composite uses the same pixels-per-micrometre for every candidate. The
committed native inputs remain unchanged for audit. No specimen crop or
content-dependent zoom is used in this conversion.

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

This is the reviewer command recommended in the Supplementary Information. It
creates an isolated temporary environment, reruns all 16 target–reference
registrations, and regenerates every Figure H and Supplementary Figure panel
from the committed inputs. The scale assumptions can be stated explicitly,
without editing code:

```powershell
python paper_figures/run_all.py --target-scale-bar-um 200 --reference-scale-bar-um 500
```

It requires Arial and does not generate a ZIP, Word document, PDF, SVG, or
TIFF. No manuscript score or sensitivity curve is loaded from a frozen figure.

Generated manuscript figures are intentionally not tracked by Git. Reviewers
recreate them from the committed input images and current algorithm with the
single command above. This prevents stale or manually post-processed PNG files
from diverging from the published source code.

Detailed file definitions, numerical formulas, output counts, and the
scale-conversion audit are documented in
[`paper_figures/README.md`](paper_figures/README.md). The manuscript may cite
the repository root and this reviewer entry point instead of enumerating local
Windows paths or every generated filename.

## Supplementary Figure S14 reproduction

The UV-versus-NIR spatial-confinement analysis has two additional plotting
entry points under
[`paper_figures/figure_s14/`](paper_figures/figure_s14/README.md). The first
regenerates the complete eight-panel Figure S14; the second exports its eight
logical panels separately:

```powershell
python paper_figures/figure_s14/plot_figure_s14.py
python paper_figures/figure_s14/export_figure_s14_panels.py
```

The directory includes pinned plotting dependencies, 138 checksum-protected
figure-level source-data files and detailed reviewer instructions. These two
commands reproduce the plotting stage from archived registered images and
ROI-level outputs; they do not rerun the upstream registration or ROI
measurement workflow.
