# Public replay cohort

These 24 PSV files are real, de-identified patient records selected from the
PhysioNet/Computing in Cardiology Challenge 2019 Dataset A internal **test**
split. They were never used for training, calibration, or threshold selection.

- License/source: PhysioNet Challenge 2019, CC BY 4.0.
- Selection: deterministic rules recorded in `manifest.json` and
  `ml/src/predict_rx/demo/export.py` (8 typical detections, one missed
  detection, one false alert, 14 stable non-sepsis encounters).
- Presentation: pseudonymous bed IDs only; never describe them as current
  hospital patients.
- Runtime: replay can be reset and repeated indefinitely; records do not get
  consumed or expire.

Synthetic commissioning beds are a separate opt-in path controlled by
`PUBLIC_SIMULATION_ENABLED`. The public demo image defaults it to `false`.
