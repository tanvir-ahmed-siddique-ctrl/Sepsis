import numpy as np
import pandas as pd

from predict_rx.residual_hazard.features import (
    HealthyResidualProjector,
    OrthoBioProjector,
    sparse_dynamics,
)
from predict_rx.residual_hazard.compare_setb import apply_external_rule
from predict_rx.residual_hazard.models import (
    HealthyResidualModel,
    apply_policy,
    hazard_meta_features,
    smooth_ema,
    stateful_policy,
)


def _frame(n=16):
    patient = np.repeat(["a", "b"], n // 2)
    hour = np.tile(np.arange(n // 2), 2)
    frame = pd.DataFrame({
        "patient_id": patient,
        "SepsisLabel": np.zeros(n, dtype=int),
        "HR": 70 + hour,
        "SBP": 120 - hour,
        "MAP": 80 - 0.5 * hour,
        "Resp": 15 + 0.2 * hour,
        "O2Sat": 98 - 0.1 * hour,
        "Temp": 37 + 0.01 * hour,
        "Lactate": 1 + 0.1 * hour,
        "Creatinine": 0.8 + 0.01 * hour,
        "BUN": 12 + hour,
        "Platelets": 200 - hour,
        "WBC": 7 + 0.1 * hour,
        "Bilirubin_total": 0.5 + 0.01 * hour,
        "Age": 60,
        "Gender": 1,
        "ICULOS": hour + 1,
        "HospAdmTime": -10,
        "Unit1": 1,
        "Unit2": 0,
        "labs_measured_24h": hour,
    })
    for variable in (
        "HR", "SBP", "MAP", "Resp", "O2Sat", "Temp", "Lactate", "Creatinine",
        "BUN", "Platelets", "WBC", "Bilirubin_total",
    ):
        frame[f"{variable}_missing"] = 0
        frame[f"{variable}_hours_since"] = 0
        frame[f"{variable}_count_24h"] = hour + 1
    return frame


def test_sparse_dynamics_is_causal_and_counts_synchronised_pairs():
    frame = _frame()
    config = {
        "variables": ["HR", "SBP", "MAP", "Resp", "O2Sat"],
        "windows": [8],
        "minimum_synchronised_pairs": 3,
    }
    before = sparse_dynamics(frame, config)
    changed = frame.copy()
    changed.loc[6:7, ["HR", "SBP", "MAP", "Resp", "O2Sat"]] = 999
    after = sparse_dynamics(changed, config)
    pd.testing.assert_frame_equal(before.iloc[:6], after.iloc[:6])
    assert before.loc[7, "dyn_sbp_to_hr_8h_pairs"] == 7


def test_missing_measurements_are_not_treated_as_synchronised():
    frame = _frame()
    frame.loc[[2, 4], "SBP_missing"] = 1
    config = {
        "variables": ["HR", "SBP"],
        "windows": [8],
        "minimum_synchronised_pairs": 3,
    }
    features = sparse_dynamics(frame, config)
    assert features.loc[7, "dyn_sbp_to_hr_8h_pairs"] == 5


def test_healthy_residual_projector_uses_prior_hour_and_preserves_missing_target():
    frame = _frame()
    projector = HealthyResidualProjector(
        targets=["HR"], predictors=["HR", "Age", "ICULOS"],
        alpha=1.0, minimum_observations=4, windows=[3],
    ).fit(frame)
    changed = frame.copy()
    changed.loc[7, "HR"] = 500
    result = projector.transform(changed)
    assert result.loc[7, "healthy_ref_HR_z"] > result.loc[6, "healthy_ref_HR_z"]
    changed.loc[7, "HR_missing"] = 1
    assert np.isnan(projector.transform(changed).loc[7, "healthy_ref_HR_z"])


def test_orthobio_is_fitted_and_deterministic():
    frame = _frame()
    config = {
        "bio": ["HR", "SBP"],
        "care_suffixes": ["_missing", "_hours_since", "_count_24h"],
        "care_context": ["ICULOS", "Unit1"],
        "ridge_alpha": 10.0,
    }
    projector = OrthoBioProjector.from_config(config).fit(frame.iloc[:12])
    first = projector.transform(frame.iloc[12:])
    second = projector.transform(frame.iloc[12:])
    pd.testing.assert_frame_equal(first, second)
    assert list(first) == ["orthobio_HR_residual", "orthobio_SBP_residual"]


def test_hazard_meta_features_have_expected_shape():
    reference = np.array([0.1, 0.2])
    hazards = np.array([[0.01, 0.02, 0.03, 0.04], [0.1, 0.2, 0.3, 0.4]])
    assert hazard_meta_features(reference, hazards).shape == (2, 8)


def test_stateful_policies_reset_between_patients_and_are_causal():
    ids = np.array(["a", "a", "a", "b", "b"])
    probability = np.array([0.1, 0.2, 0.01, 0.01, 0.2])
    ema = smooth_ema(probability, ids, 0.5)
    assert ema[3] == probability[3]
    decision = stateful_policy(
        probability, ids, high=0.15, low_ratio=0.5, persistence=2, acute_delta=np.inf
    )
    assert decision.tolist() == [False, False, False, False, False]
    _, raw = apply_policy({"kind": "raw", "threshold": 0.15}, probability, ids)
    assert raw.tolist() == [False, True, False, False, True]


def test_healthy_residual_model_derives_features_before_scoring():
    class DummyModel:
        def predict_proba(self, values):
            assert list(values) == ["healthy_ref_HR_z"]
            z = np.clip(values.iloc[:, 0].fillna(0).to_numpy(), -20, 20)
            p = 1 / (1 + np.exp(-z))
            return np.column_stack([1 - p, p])

    frame = _frame()
    projector = HealthyResidualProjector(
        targets=["HR"],
        predictors=["HR", "Age", "ICULOS"],
        alpha=1.0,
        minimum_observations=4,
        windows=[3],
    ).fit(frame)
    model = HealthyResidualModel(
        DummyModel(), projector, ["healthy_ref_HR_z"]
    )
    probability = model.predict_proba(frame)
    assert probability.shape == (len(frame), 2)
    np.testing.assert_allclose(probability.sum(axis=1), 1)


def test_external_rule_requires_every_safety_check():
    rule = {
        "require_any_paired_95ci_lower_above_zero": ["normalized_utility", "auprc"],
        "require_high_risk_utility_point_not_worse": True,
        "maximum_auroc_point_drop": 0.005,
        "maximum_sensitivity_point_drop": 0.02,
        "maximum_false_alert_increase_per_100h": 0.05,
    }
    paired = {
        "normalized_utility": {"lower": 0.001, "upper": 0.02},
        "auprc": {"lower": -0.001, "upper": 0.01},
    }
    reports = {
        "candidate_system": {
            "ranking": {"auroc": 0.81},
            "high_risk": {
                "normalized_utility": 0.25,
                "sensitivity": 0.31,
                "false_alerts_per_100_patient_hours": 0.20,
            },
        },
        "run4": {
            "ranking": {"auroc": 0.808},
            "high_risk": {
                "normalized_utility": 0.238,
                "sensitivity": 0.314,
                "false_alerts_per_100_patient_hours": 0.19,
            },
        },
    }
    assert apply_external_rule(rule, paired, reports)["promote_candidate"]
    reports["candidate_system"]["high_risk"]["normalized_utility"] = 0.23
    assert not apply_external_rule(rule, paired, reports)["promote_candidate"]

