"""Clinically aligned incident-onset targets kept separate from SepsisLabel."""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

DEFAULT_HORIZONS = (1, 3, 6, 12)


def incident_target_manifest(horizons: Iterable[int] = DEFAULT_HORIZONS) -> dict[str, object]:
    return {
        "version": "incident-onset-v1",
        "source_label": "PhysioNet Challenge 2019 SepsisLabel",
        "derived_onset": "first positive SepsisLabel row position + 6 hours",
        "prediction_time_information": "current and past rows only",
        "at_risk_definition": (
            "All rows strictly before derived onset for septic stays and every eligible row "
            "for non-septic stays."
        ),
        "onset_hour_included_as_predictor": False,
        "post_onset_policy": "Censored, represented as null target values.",
        "positive_definition": {
            f"incident_onset_within_{h}h": f"Derived onset occurs 1 through {h} hours after prediction time."
            for h in horizons
        },
        "official_target_preserved": True,
    }


def build_incident_targets(
    frame: pd.DataFrame,
    horizons: Iterable[int] = DEFAULT_HORIZONS,
    *,
    patient_col: str = "patient_id",
    label_col: str = "SepsisLabel",
) -> pd.DataFrame:
    """Return nullable incident targets aligned to ``frame.index``.

    The current/onset hour is excluded: a target is positive only when onset is
    at least one hour in the future. Post-onset and onset rows are censored.
    """
    horizons = tuple(sorted(set(int(h) for h in horizons)))
    if not horizons or horizons[0] < 1:
        raise ValueError("Incident horizons must be positive integers.")
    missing = {patient_col, label_col} - set(frame.columns)
    if missing:
        raise ValueError(f"Missing target columns: {sorted(missing)}")

    labels = frame[label_col].fillna(0).to_numpy(dtype=int)
    positions = frame.groupby(patient_col, sort=False).cumcount()
    first_positive = positions[labels == 1].groupby(frame.loc[labels == 1, patient_col], sort=False).min()
    onset_by_patient = first_positive + 6
    onset = frame[patient_col].map(onset_by_patient).astype("Float64")
    lead = onset - positions
    at_risk = onset.isna() | lead.gt(0)

    out = pd.DataFrame(index=frame.index)
    out["incident_at_risk"] = at_risk.astype(bool)
    out["incident_hours_to_onset"] = lead.where(onset.notna()).astype("Float64")
    out["derived_onset_position"] = onset.astype("Float64")
    for horizon in horizons:
        values = pd.Series(pd.NA, index=frame.index, dtype="Int8")
        values.loc[at_risk] = (
            onset.notna() & lead.ge(1) & lead.le(horizon)
        ).loc[at_risk].astype("int8")
        out[f"incident_onset_within_{horizon}h"] = values
    return out
