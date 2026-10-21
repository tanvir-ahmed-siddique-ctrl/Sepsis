"""Unit tests that do not require the full PhysioNet download."""

from __future__ import annotations

import numpy as np
import pandas as pd

from predict_rx.data.splits import SplitConfig, assign_patient_splits
from predict_rx.eval.metrics import UtilityTable, patient_detection
from predict_rx.features import build_patient_features
from predict_rx.features.schema import LAB_COLS


def test_patient_splits_are_disjoint():
    ids = [f"p{i:03d}" for i in range(100)]
    mapping = assign_patient_splits(ids, SplitConfig(seed=0))
    by_split: dict[str, set[str]] = {"train": set(), "val": set(), "test": set()}
    for pid, split in mapping.items():
        by_split[split].add(pid)
    assert by_split["train"].isdisjoint(by_split["val"])
    assert by_split["train"].isdisjoint(by_split["test"])
    assert by_split["val"].isdisjoint(by_split["test"])
    assert len(mapping) == 100


def _patient(n: int = 8, **overrides) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "HR": np.linspace(80, 110, n),
            "O2Sat": 97.0,
            "Temp": 37.0,
            "SBP": np.linspace(120, 90, n),
            "MAP": 75.0,
            "DBP": 60.0,
            "Resp": 18.0,
            "EtCO2": np.nan,
            "Age": 65,
            "Gender": 1,
            "Unit1": 1,
            "Unit2": 0,
            "HospAdmTime": -10,
            "ICULOS": np.arange(1, n + 1),
            "SepsisLabel": 0,
            "patient_id": "demo",
        }
    )
    for col in LAB_COLS:
        df[col] = np.nan
    for k, v in overrides.items():
        df[k] = v
    return df


def test_features_never_use_future_rows():
    base = _patient()
    changed = base.copy()
    changed.loc[6:, "HR"] = 200.0  # alter only the future
    a = build_patient_features(base)
    b = build_patient_features(changed)
    cols = [c for c in a.columns if c not in ("patient_id",)]
    pd.testing.assert_frame_equal(a.loc[:5, cols], b.loc[:5, cols])


def test_build_patient_features_adds_missingness_and_derived():
    out = build_patient_features(_patient())
    assert "HR_missing" in out.columns and "HR_hours_since" in out.columns
    assert "shock_index" in out.columns
    assert out["Lactate_missing"].eq(1).all()


def test_clinical_scores_and_baseline():
    df = _patient(n=30, Platelets=40.0, Creatinine=2.5, Bilirubin_total=0.5)
    df.loc[:, "HR"] = 80.0
    df.loc[25:, "HR"] = 130.0
    out = build_patient_features(df)
    last = out.iloc[-1]
    assert last["sofa_coag"] == 3 and last["sofa_renal"] == 2 and last["sofa_liver"] == 0
    assert last["HR_dev_baseline"] == 50.0  # baseline frozen at first-24h median of 80
    assert last["tachycardia_hours_24h"] == 5
    assert last["Platelets_count_24h"] == 24


def test_explanations_map_new_features_to_variables():
    from predict_rx.explain import base_variable

    assert base_variable("HR_dev_baseline") == "HR"
    assert base_variable("Lactate_count_24h") == "Lactate"
    assert base_variable("fever_hours_12h") == "fever"
    assert base_variable("HR_hours_since") == "HR"


def _frame(labels_by_patient: dict[str, list[int]]) -> pd.DataFrame:
    rows = [(pid, lab) for pid, labs in labels_by_patient.items() for lab in labs]
    return pd.DataFrame(rows, columns=["patient_id", "SepsisLabel"])


def test_utility_perfect_and_inaction_bounds():
    # Septic patient: label turns on at index 10 → onset 16; non-septic patient.
    df = _frame({"s": [0] * 10 + [1] * 10, "n": [0] * 15})
    table = UtilityTable.from_frame(df)
    ids = df["patient_id"].to_numpy()
    idx = df.groupby("patient_id", sort=False).cumcount().to_numpy()
    perfect = (ids == "s") & (idx >= 4)  # [onset-12, onset+3] = [4, 19]
    assert np.isclose(table.normalized(perfect), 1.0)
    assert np.isclose(table.normalized(np.zeros(len(df), dtype=bool)), 0.0)
    assert table.normalized(np.ones(len(df), dtype=bool)) < 1.0


def test_false_alarms_on_non_septic_patient_lower_utility():
    df = _frame({"s": [0] * 10 + [1] * 10, "n": [0] * 20})
    table = UtilityTable.from_frame(df)
    ids = df["patient_id"].to_numpy()
    idx = df.groupby("patient_id", sort=False).cumcount().to_numpy()
    perfect = (ids == "s") & (idx >= 4)
    assert table.normalized(perfect | (ids == "n")) < table.normalized(perfect)


def test_patient_detection_warning_time():
    df = _frame({"s": [0] * 10 + [1] * 10})
    pred = np.zeros(20, dtype=bool)
    pred[12:] = True  # onset at 16 → 4 hours warning
    det = patient_detection(df, pred)
    assert det["septic_patients"] == 1
    assert det["median_warning_hours"] == 4
