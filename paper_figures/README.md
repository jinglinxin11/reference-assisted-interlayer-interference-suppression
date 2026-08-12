# End-to-end reproduction of the manuscript figures

This reviewer workflow starts from the four target microscopy images and four
reference images committed under `data/input/`. It runs all sixteen candidate
registrations once, writes the numerical diagnostic source data, and generates
Figure H plus Supplementary Figures 1–5 from that same in-memory result.

No manuscript score, transform, translation landscape, or sensitivity curve is
loaded from a frozen figure or hard-coded plotting array.

## One command

From the repository root:

```powershell
python paper_figures/run_all.py
```

The same command is used from Bash, zsh, or a POSIX shell:

```bash
python paper_figures/run_all.py
```

The launcher creates a disposable virtual environment in the operating
system's temporary directory, installs the pinned root requirements, safely
clears only `paper_figures/generated/`, runs the algorithm and all plots, and
removes the temporary environment automatically.

Custom input directories can be supplied without changing the code:

```powershell
python paper_figures/run_all.py `
  --targets path\to\four_targets `
  --references path\to\four_references
```

Each directory must contain exactly four readable JPG or PNG images. Target
images are ordered by filename; reference filename stems are used only as
display labels. Candidate selection is determined by the algorithm scores.

## End-to-end data flow

```text
data/input/target_images + data/input/reference_images
                         |
                         v
        four targets x four candidate registrations
                         |
                         v
      one PipelineRun containing all scores and transforms
                         |
          +--------------+------------------+
          |              |                  |
          v              v                  v
 algorithm_results/  diagnostics/      paper figures
```

Figure H uses the reproducible worked example `target_01 -> S`, matching the
approved post-revision panel sequence. Supplementary Figure 1 reports all four
targets, so no target is omitted from the processing evidence.

## Outputs

```text
paper_figures/generated/
  algorithm_results/
    results.json                      # selected labels and transforms
    presentation/                     # four target-derived presentation PNGs
    binary/                           # four strict matched-only PNGs

  diagnostics/
    pairwise_matches.csv              # all 16 scores, transforms, and components
    selected_matches.csv              # four selected/runner-up summaries
    translation_landscape.csv         # plotted local objective grid
    corridor_radius_sensitivity.csv   # plotted precision/recall/Dice values
    search_bound_sensitivity.csv      # independent reruns over diagnostic bounds
    diagnostics.json                  # input SHA-256 values and plot definitions

  figure_h/                           # 8 standalone 600 dpi RGB PNG panels
    panel_a_structural_response.png
    panel_b_foreground_skeleton.png
    panel_c_pairwise_internal_score_matrix.png
    panel_d_local_translation_landscape.png
    panel_e_registered_support_corridor.png
    panel_f_corridor_radius_sensitivity.png
    panel_g_strict_matched_only_output.png
    panel_h_target_derived_presentation.png

  supplementary/                     # 5 complete supplementary PNG figures
    supplementary_figure_1_casewise_evidence_flow.png
    supplementary_figure_2_pairwise_ranking_transforms.png
    supplementary_figure_3_registration_output_sensitivity.png
    supplementary_figure_4_candidate_references.png
    supplementary_figure_5_selection_diagnostics.png
    individual_panels/                # 42 standalone 600 dpi RGB PNG panels
```

These are the approved post-revision layouts: Figure H contains the score
matrix, local translation contour and corridor-radius sensitivity panels;
Supplementary Figures 2, 3 and 5 use aligned parenthesized panel labels and the
requested spacing. The supplementary single-panel counts are:

- Supplementary Figure 1: 20 panels, five data-derived stages for four targets.
- Supplementary Figure 2: 3 panels, pairwise scores, ranking margins, and transforms.
- Supplementary Figure 3: 3 panels, translation objective and corridor-radius sensitivity.
- Supplementary Figure 4: 8 panels, native and analysis views of all four references.
- Supplementary Figure 5: 8 panels, selected/runner-up components and stability diagnostics.

## Quantitative definitions

- Figure H-c is read directly from the sixteen final `UnifiedMatch.score`
  values produced in the current run.
- Figure H-d fixes the selected scale and rotation, then evaluates the same
  registration geometry objective over a 41 x 41 grid of relative x/y
  translations from -24 to +24 analysis pixels.
- Figure H-f evaluates corridor radii 2–30 pixels. Precision is target
  foreground inside the corridor divided by corridor pixels; recall is target
  foreground inside the corridor divided by all target foreground; Dice is
  twice the intersection divided by the sum of target-foreground and corridor
  pixels.
- The default displayed corridor radius is 12 analysis pixels.

Every plotted numeric value is also written under `generated/diagnostics/`.

The complete `generated/` directory is intentionally excluded from Git. A
release is defined by the committed inputs, algorithm, plotting code, and the
one-command reproduction entry point—not by cached raster outputs. Do not add
generated PNG files to a commit unless a clean end-to-end run has first passed
and the repository's publication policy is deliberately changed.

## Rendering contract

- Python/matplotlib is the exclusive plotting backend.
- Arial and Arial Bold are required. The run stops instead of silently
  substituting another font.
- Manuscript outputs are RGB PNG with 600 dpi metadata.
- Standalone microscopy-derived panels are exported at their native array
  dimensions, pixel for pixel. They are never cropped, stretched, padded,
  letterboxed, or given a synthetic border. Fixed 946 x 820 canvases are used
  only for mathematical charts such as the score matrix, contour map, and
  sensitivity curve.
- Supplementary composite figures may contain explicitly fitted copies for
  page assembly; the corresponding standalone panels remain the authoritative,
  geometry-preserving evidence images.
- The workflow does not create PDF, TIFF, SVG, ZIP, or Word files.
- The target/reference scale-bar physical length is explicitly defined as
  200 um by the matching pipeline; the program does not infer that text by OCR.

## Relevant code

```text
paper_figures/
  run_all.py                              isolated reviewer launcher
  generate_all.py                        one algorithm run and shared orchestration
  diagnostics.py                         data-derived images and numerical source data
  generate_figure_h_panels.py            Figure H renderer
  scripts/export_supplementary_figures.py supplementary renderer
```
