"""Model and policy helpers for the preregistered residual-hazard experiment."""

from __future__ import annotations

import inspect

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from predict_rx.eval.metrics import UtilityTable, best_utility_threshold, candidate_thresholds
from predict_rx.residual_hazard.features import HealthyResidualProjector
from predict_rx.train.challenger import patient_time_weights

_HAS_EVAL_X = "eval_X" in inspect.signature(lgb.LGBMClassifier.fit).parameters


class HealthyResidualModel:
    """Serializable risk model that derives its selected residual features."""

    def __init__(
        self,
        model: lgb.LGBMClassifier,
        projector: HealthyResidualProjector,
        feature_columns: list[str],
        calibrator: IsotonicRegression | None = None,
    ) -> None:
        self.model = model
        self.projector = projector
        self.feature_columns = feature_columns
        self.calibrator = calibrator

    def augment(self, frame: pd.DataFrame) -> pd.DataFrame:
        residuals = self.projector.transform(frame)
        return pd.concat([frame, residuals], axis=1)

    def raw_score(self, frame: pd.DataFrame) -> np.ndarray:
        augmented = self.augment(frame)
        return self.model.predict_proba(augmented[self.feature_columns])[:, 1]

    def predict_proba(self, frame: pd.DataFrame) -> np.ndarray:
        probability = self.raw_score(frame)
        if self.calibrator is not None:
            probability = self.calibrator.predict(probability)
        return np.column_stack([1 - probability, probability])


def fit_lgbm(
    fit: pd.DataFrame,
    stop: pd.DataFrame,
    columns: list[str],
    params: dict,
    seed: int,
    *,
    target: str = "SepsisLabel",
    at_risk: str | None = None,
) -> lgb.LGBMClassifier:
    fit_use = np.ones(len(fit), dtype=bool) if at_risk is None else fit[at_risk].fillna(False).to_numpy(bool)
    stop_use = np.ones(len(stop), dtype=bool) if at_risk is None else stop[at_risk].fillna(False).to_numpy(bool)
    train = fit.loc[fit_use]
    validation = stop.loc[stop_use]
    if train[target].nunique() < 2 or validation[target].nunique() < 2:
        raise ValueError(f"{target} needs both classes in fit and early-stopping frames.")
    if target == "SepsisLabel":
        train_weight = patient_time_weights(train)
        stop_weight = patient_time_weights(validation)
    else:
        train_weight = 1 / train.groupby("patient_id")["patient_id"].transform("size").to_numpy(float)
        stop_weight = 1 / validation.groupby("patient_id")["patient_id"].transform("size").to_numpy(float)
        train_weight *= np.where(train[target].to_numpy(int) == 1, 1.5, 1.0)
        stop_weight *= np.where(validation[target].to_numpy(int) == 1, 1.5, 1.0)
        train_weight /= train_weight.mean()
        stop_weight /= stop_weight.mean()
    model = lgb.LGBMClassifier(
        objective="binary", random_state=seed, n_jobs=-1, verbosity=-1, **params
    )
    eval_kwargs = (
        {"eval_X": (validation[columns],), "eval_y": (validation[target],)}
        if _HAS_EVAL_X
        else {"eval_set": [(validation[columns], validation[target])]}
    )
    model.fit(
        train[columns],
        train[target],
        sample_weight=train_weight,
        eval_sample_weight=[stop_weight],
        eval_metric="average_precision",
        callbacks=[lgb.early_stopping(100, verbose=False)],
        **eval_kwargs,
    )
    return model


def calibrate_and_threshold(
    calibration: pd.DataFrame,
    raw: np.ndarray,
    eligible: np.ndarray,
    *,
    minimum_specificity: float | None = None,
) -> tuple[IsotonicRegression, np.ndarray, float]:
    calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(
        raw[eligible], calibration["SepsisLabel"].to_numpy()[eligible]
    )
    probability = calibrator.predict(raw)
    threshold, _ = best_utility_threshold(
        UtilityTable.from_frame(calibration),
        probability,
        eligible,
        calibration["SepsisLabel"].to_numpy(),
        minimum_specificity,
    )
    return calibrator, probability, threshold


def logit(probability: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(probability, dtype=float), 1e-5, 1 - 1e-5)
    return np.log(p / (1 - p))


def hazard_meta_features(reference: np.ndarray, hazards: np.ndarray) -> np.ndarray:
    h = logit(hazards)
    return np.column_stack([logit(reference), h, np.diff(h, axis=1)])


def fit_meta(x: np.ndarray, y: np.ndarray, eligible: np.ndarray, c: float) -> LogisticRegression:
    return LogisticRegression(C=c, max_iter=2000, class_weight=None).fit(x[eligible], y[eligible])


def smooth_ema(probability: np.ndarray, patient_ids: np.ndarray, alpha: float) -> np.ndarray:
    out = np.empty_like(probability, dtype=float)
    previous_id, state = None, 0.0
    for i, (patient, value) in enumerate(zip(patient_ids, probability)):
        if patient != previous_id:
            state, previous_id = float(value), patient
        else:
            state = alpha * float(value) + (1 - alpha) * state
        out[i] = state
    return out


def stateful_policy(
    probability: np.ndarray,
    patient_ids: np.ndarray,
    *,
    high: float,
    low_ratio: float = 1.0,
    persistence: int = 1,
    acute_delta: float = np.inf,
) -> np.ndarray:
    """Causal hysteresis/persistence policy with an evaluated acute bypass."""
    decision = np.zeros(len(probability), dtype=bool)
    previous_id, active, history, previous = None, False, [], 0.0
    for i, (patient, value) in enumerate(zip(patient_ids, probability)):
        value = float(value)
        if patient != previous_id:
            previous_id, active, history, previous = patient, False, [], value
        history.append(value >= high)
        history = history[-persistence:]
        surge = value - previous >= acute_delta and value >= high * low_ratio
        if surge or (len(history) == persistence and all(history)):
            active = True
        elif value <= high * low_ratio:
            active = False
        decision[i] = active
        previous = value
    return decision


def select_stateful_policy(
    frame: pd.DataFrame,
    probability: np.ndarray,
    eligible: np.ndarray,
    config: dict,
) -> dict:
    """Select only on calibration patients, with the preregistered specificity floor."""
    table = UtilityTable.from_frame(frame)
    y = frame["SepsisLabel"].to_numpy()
    ids = frame["patient_id"].to_numpy()
    negatives = eligible & (y == 0)
    candidates = []
    for threshold in candidate_thresholds(
        probability[eligible], n=int(config.get("threshold_candidates", 60))
    ):
        raw = (probability >= threshold) & eligible
        specificity = 1 - raw[negatives].mean()
        if specificity >= float(config["minimum_specificity"]):
            candidates.append({
                "kind": "raw", "threshold": float(threshold),
                "utility": float(table.normalized(raw)),
            })
        for low_ratio in map(float, config["hysteresis_low_ratio"]):
            for surge in map(float, config["acute_surge_delta"]):
                pred = stateful_policy(
                    probability, ids, high=float(threshold), low_ratio=low_ratio,
                    acute_delta=surge,
                ) & eligible
                if 1 - pred[negatives].mean() >= float(config["minimum_specificity"]):
                    candidates.append({
                        "kind": "hysteresis", "threshold": float(threshold),
                        "low_ratio": low_ratio, "acute_delta": surge,
                        "utility": float(table.normalized(pred)),
                    })
        for hours in map(int, config["persistence_hours"]):
            for surge in map(float, config["acute_surge_delta"]):
                pred = stateful_policy(
                    probability, ids, high=float(threshold), persistence=hours,
                    acute_delta=surge,
                ) & eligible
                if 1 - pred[negatives].mean() >= float(config["minimum_specificity"]):
                    candidates.append({
                        "kind": "persistence", "threshold": float(threshold),
                        "persistence": hours, "acute_delta": surge,
                        "utility": float(table.normalized(pred)),
                    })
    for alpha in map(float, config["ema_alpha"]):
        smoothed = smooth_ema(probability, ids, alpha)
        threshold, utility = best_utility_threshold(
            table, smoothed, eligible, y, float(config["minimum_specificity"])
        )
        candidates.append({
            "kind": "ema", "threshold": threshold, "alpha": alpha, "utility": utility,
        })
    return max(candidates, key=lambda item: item["utility"])


def apply_policy(spec: dict, probability: np.ndarray, patient_ids: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return policy score and binary action. Scores are descriptive for stateful policies."""
    kind = spec["kind"]
    score = probability
    if kind == "ema":
        score = smooth_ema(probability, patient_ids, float(spec["alpha"]))
        decision = score >= float(spec["threshold"])
    elif kind == "raw":
        decision = probability >= float(spec["threshold"])
    else:
        decision = stateful_policy(
            probability,
            patient_ids,
            high=float(spec["threshold"]),
            low_ratio=float(spec.get("low_ratio", 1.0)),
            persistence=int(spec.get("persistence", 1)),
            acute_delta=float(spec.get("acute_delta", np.inf)),
        )
    return score, decision

