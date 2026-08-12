# Reproducible image-analysis pipeline

## Source integrity and software

- Source TIFFs were read without overwriting or gamma/contrast/saturation modification.
- Software: Python 3.12.13; NumPy 2.5.1; SciPy 1.16.1; scikit-image 0.25.2; Matplotlib 3.10.5; pandas 3.0.1; tifffile 2025.6.11; Pillow 12.3.0.
- Fixed random seed: 20260808.
- Source bit depth: (8, 8, 8, 8) and (8, 8, 8, 8).

## Spatial comparability and registration

The before TIFF (314 × 390 px; DPI [329.997, 329.997]) and after TIFF (285 × 355 px; DPI [299.999, 299.999]) have different pixel dimensions. Their width/DPI and height/DPI ratios are nearly equal, consistent with the same exported canvas sampled at different pixel densities. DPI is a print/export descriptor and was not treated as a sample μm calibration. The higher-sampled before image was downsampled to the after-image grid using anti-aliasing, then rigidly registered by rotation and translation using Sobel-gradient phase correlation. Linear interpolation (order 1) was used; no sharpening interpolation was applied.

- Scale factors: x=0.90764331, y=0.91025641.
- Rotation: 1.500°.
- Translation: dx=-3.250 px, dy=1.300 px.
- Gradient-feature correlation: 0.1906 before rigid alignment and 0.2426 after alignment.

## Color conversion and channel choice

RGB was converted directly from the original 8-bit TIFF values. Three metrics were evaluated: R, ExR = 2R-G-B, and CIELAB a*. No display adjustment was used in calculations. The selected metric was **ExR**, chosen by a fixed score combining native positive red response, profile validity, median CNR, and edge-width stability to Gaussian smoothing.

- R: selection score 0.784, median CNR 5.961, native positive response 16.7%, valid profiles 83.3%, smoothing CV 5.62%
- ExR: selection score 5.228, median CNR 6.362, native positive response 83.3%, valid profiles 100.0%, smoothing CV 1.42%
- Lab_a: selection score 3.714, median CNR 6.042, native positive response 83.3%, valid profiles 75.0%, smoothing CV 1.67%

## ROI selection and profile construction

Six anatomically distributed, approximately straight segments were used: both outer upper arms, two lower forearm boundaries, and both lapel diagonals. Candidate positions were quality-screened only within these fixed anatomical bands using the minimum peak-to-noise across both conditions; the before-after effect size was not part of the score. The final coordinates were frozen in `analysis_config.json`. Each center was then refined only along its normal by at most ±6 px using the after-image a* response. This is a centering operation, not selection among alternative structures. The same registered coordinates were applied to both conditions. At each ROI, 11 parallel profiles at 1.0 px spacing were sampled along the edge normal. Coordinates are stored in `roi_coordinates.csv`.

## Background correction, smoothing, and metrics

For each profile, the background baseline was the median of the outer 18% at each end. Noise was the larger of robust MAD-derived SD and conventional SD. A fixed Gaussian sigma of 0.75 px was used only for crossing detection; raw and smoothed profiles are both retained. Profiles were normalized from local background (0) to the central line peak (1). The 10–90% widths were found independently on both sides of the peak by linear subpixel interpolation of the monotonic crossing envelope. FWHM was the distance between the two 50% crossings. The normalized maximum gradient, raw selected-channel contrast, and CNR were also computed. Halo decay distance was defined as the outward distance from x50 to background + 3 SD. A spillover-area ratio was not computed because no independent theoretical pattern boundary was available.

## Robustness and exclusions

- Smoothing sensitivity: sigma = 0.0, 0.5, 0.75, 1.0 px.
- Threshold sensitivity: background + 2.7, 3.0, 3.3 SD.
- No statistical outlier deletion was performed.
- A profile is flagged only if peak-to-noise is below 3.0 or if required crossings are absent. Flags are retained in the all-profile table.

## Statistics

Profiles were first averaged to the ROI level. Descriptive mean, SD, median, IQR, and a 10000-resample percentile bootstrap CI for the mean were then computed across the six spatial ROIs. These ROIs quantify within-image spatial variability and are not independent material replicates. No between-material hypothesis test or p-value was calculated.
