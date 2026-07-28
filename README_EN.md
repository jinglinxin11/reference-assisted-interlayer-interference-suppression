# Core Microscopy Pattern-Matching Algorithm

## 1. Purpose

This program independently matches four target microscopy images against four structural reference images. It estimates the scale, rotation, and translation that map each reference structure onto a target, then exports the selected label, a natural-background presentation image, and a matched-only binary evidence image.

The current candidate labels are `S`, `T`, `U`, and `Z`. Each target is ranked independently; no one-to-one batch assignment is used.

## 2. Directory Layout

```text
run_matching.py                    Command-line entry point
requirements.txt                  Python dependencies
microscopy_matching/
  image_processing.py             Dark response, foreground, skeleton, corridor
  scale_calibration.py             Scale-bar detection and pixel/um conversion
  registration.py                  Scale, rotation, and translation search
  topology_metrics.py              Endpoint, direction, and missing-stroke scores
  evidence_mask.py                 Evidence gating and binary export
  pipeline.py                      Pipeline orchestration and output writer
data/input/
  target_images/                   Four target images
  reference_images/                Four structural reference images
```

## 3. Requirements

- Python 3.10 or newer
- Windows, Linux, or macOS

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

## 4. Running the Algorithm

Run this command from the extracted project root:

```powershell
python -B run_matching.py
```

The input and output directories can also be provided explicitly:

```powershell
python -B run_matching.py `
  --targets data\input\target_images `
  --references data\input\reference_images `
  --outdir artifacts\matching_results
```

## 5. Outputs

```text
artifacts/matching_results/
  results.json
  presentation/
    target_01_S.png
    target_02_T.png
    target_03_U.png
    target_04_Z.png
  binary/
    target_01_S.png
    target_02_T.png
    target_03_U.png
    target_04_Z.png
```

`presentation` contains natural-background result images. `binary` contains only target-image evidence located inside the registered reference corridor. The algorithm does not synthesize or repair strokes in these binary outputs.

## 6. Matching Rules

1. Extract the dark response, foreground mask, and skeleton from every target and reference image.
2. Detect the target scale bar and use the explicitly supplied physical length of `200 um` to define the scale constraint.
3. Independently search every candidate reference for each target over scale, rotation, and translation.
4. Form one score from geometric distance, orientation agreement, skeleton coverage, endpoint coverage, and missing-stroke penalties.
5. Select the highest-scoring candidate independently for every target. File order does not force the selected label, and no one-to-one batch assignment is applied.
6. Export the binary result as `target foreground AND registered reference corridor`.

## 7. Decision Status

- `accepted`: the margin and structural checks satisfy automatic acceptance criteria.
- `review_required_low_margin`: the best and second-best scores are close; manual review is recommended.
- `review_required_topology`: critical-stroke or endpoint-coverage checks require review.
- Additional flags may report search-boundary or physical-scale audit conditions.

The review status does not replace the highest-scoring label. It communicates uncertainty in an auditable form.

## 8. Verified Result for the Included Inputs

This core package was tested after independent extraction. The highest-scoring labels for the included target images are:

```text
target_01 -> S
target_02 -> T
target_03 -> U
target_04 -> Z
```

## 9. Notes

- Reference filenames provide candidate labels but do not determine a target's selected result.
- Each input directory must contain exactly four readable JPG or PNG images.
- Verify the physical meaning of the scale bar when replacing inputs. The program does not infer the scale label through OCR.
- This core package excludes manuscript layout, PDF, SVG, animation, perspective-stack, and yellow-label export utilities.

