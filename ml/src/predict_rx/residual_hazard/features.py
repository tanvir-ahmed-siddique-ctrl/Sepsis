"""Causal and fold-fitted features for RESIDUAL-HAZARD-01.

The names here are intentionally conservative:
- sparse dynamics are descriptive statistics, not transfer entropy;
- healthy residuals compare with a non-septic training reference, not a
  patient counterfactual;
- OrthoBio residuals are linear residualisation, not causal adjustment.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge


def _observed(frame: pd.DataFrame, variable: str) -> pd.Series:
    missing = f"{variable}_missing"
    if variable not in frame or missing not in frame:
        return pd.Series(np.nan, index=frame.index, dtype=np.float32)
    return frame[variable].where(frame[missing].eq(0)).astype(np.float32)


def _rolling_slope(values: pd.Series, patient: pd.Series, window: int, minimum: int) -> pd.DataFrame:
    """Irregular-observation OLS slope and count over causal row windows."""
    blocks = []
    for _, index in patient.groupby(patient, sort=False).groups.items():
        y = values.loc[index].to_numpy(dtype=np.float64)
        m = np.isfinite(y).astype(np.float64)
        y0 = np.nan_to_num(y)
        t = np.arange(len(y), dtype=np.float64)
        data = pd.DataFrame({
            "n": m,
            "t": t * m,
            "y": y0,
            "tt": t * t * m,
            "ty": t * y0,
        })
        sums = data.rolling(window, min_periods=1).sum()
        denominator = sums["n"] * sums["tt"] - sums["t"] ** 2
        slope = (sums["n"] * sums["ty"] - sums["t"] * sums["y"]) / denominator
        slope[(sums["n"] < minimum) | (denominator <= 1e-9)] = np.nan
        blocks.append(pd.DataFrame(
            {"slope": slope.to_numpy(), "count": sums["n"].to_numpy()},
            index=index,
        ))
    return pd.concat(blocks).sort_index()


def _rolling_lag_correlation(
    source: pd.Series,
    target: pd.Series,
    patient: pd.Series,
    window: int,
    minimum: int,
) -> pd.DataFrame:
    """Corr(source[t-1], target[t]) using only synchronised valid pairs."""
    blocks = []
    for _, index in patient.groupby(patient, sort=False).groups.items():
        x = source.loc[index].shift(1)
        y = target.loc[index]
        pair = x.notna() & y.notna()
        corr = x.rolling(window, min_periods=minimum).corr(y)
        count = pair.rolling(window, min_periods=1).sum()
        corr[count < minimum] = np.nan
        blocks.append(pd.DataFrame({"corr": corr, "count": count}, index=index))
    return pd.concat(blocks).sort_index()


def sparse_dynamics(frame: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Deterministic causal dynamics with explicit reliability counts."""
    patient = frame["patient_id"]
    variables = [v for v in config["variables"] if v in frame]
    minimum = int(config["minimum_synchronised_pairs"])
    out: dict[str, pd.Series] = {}
    observed = {v: _observed(frame, v) for v in variables}
    for window in map(int, config["windows"]):
        for variable in variables:
            slope = _rolling_slope(observed[variable], patient, window, minimum)
            prefix = f"dyn_{variable}_{window}h"
            out[f"{prefix}_slope"] = slope["slope"].astype(np.float32)
            out[f"{prefix}_observed"] = slope["count"].astype(np.float32)
        for source, target, name in (
            ("SBP", "HR", "sbp_to_hr"),
            ("MAP", "HR", "map_to_hr"),
            ("Resp", "O2Sat", "resp_to_o2sat"),
        ):
            if source not in observed or target not in observed:
                continue
            pair = _rolling_lag_correlation(
                observed[source], observed[target], patient, window, minimum
            )
            out[f"dyn_{name}_{window}h_lag_corr"] = pair["corr"].astype(np.float32)
            out[f"dyn_{name}_{window}h_pairs"] = pair["count"].astype(np.float32)
    return pd.DataFrame(out, index=frame.index)


def _lagged_predictors(frame: pd.DataFrame, predictors: list[str]) -> pd.DataFrame:
    patient = frame["patient_id"]
    columns: dict[str, pd.Series] = {}
    static = {"Age", "Gender", "HospAdmTime"}
    for column in predictors:
        if column not in frame:
            continue
        values = frame[column]
        columns[f"ref_{column}"] = values if column in static else values.groupby(patient, sort=False).shift(1)
        missing = f"{column}_missing"
        if column not in static and missing in frame:
            columns[f"ref_{column}_missing"] = frame[missing].groupby(patient, sort=False).shift(1)
    return pd.DataFrame(columns, index=frame.index)


@dataclass
class HealthyResidualProjector:
    targets: list[str]
    predictors: list[str]
    alpha: float
    minimum_observations: int
    windows: list[int]
    medians_: np.ndarray | None = None
    models_: dict[str, Ridge] | None = None
    scales_: dict[str, float] | None = None
    predictor_columns_: list[str] | None = None

    @classmethod
    def from_config(cls, config: dict) -> "HealthyResidualProjector":
        return cls(
            targets=list(config["targets"]),
            predictors=list(config["predictors"]),
            alpha=float(config["ridge_alpha"]),
            minimum_observations=int(config["minimum_observations"]),
            windows=list(map(int, config["windows"])),
        )

    def fit(self, frame: pd.DataFrame) -> "HealthyResidualProjector":
        x_frame = _lagged_predictors(frame, self.predictors)
        self.predictor_columns_ = list(x_frame)
        x = x_frame.to_numpy(dtype=np.float64)
        self.medians_ = np.nanmedian(x, axis=0)
        x = np.where(np.isfinite(x), x, self.medians_)
        septic = frame.groupby("patient_id", sort=False)["SepsisLabel"].transform("max").to_numpy() > 0
        models, scales = {}, {}
        for target in self.targets:
            if target not in frame:
                continue
            y = _observed(frame, target).to_numpy(dtype=np.float64)
            use = (~septic) & np.isfinite(y) & np.isfinite(x).all(axis=1)
            if use.sum() < self.minimum_observations:
                continue
            model = Ridge(alpha=self.alpha).fit(x[use], y[use])
            residual = y[use] - model.predict(x[use])
            median = np.median(residual)
            scale = 1.4826 * np.median(np.abs(residual - median))
            models[target] = model
            scales[target] = float(scale if np.isfinite(scale) and scale > 1e-6 else np.std(residual) or 1.0)
        self.models_, self.scales_ = models, scales
        return self

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        if self.models_ is None or self.medians_ is None:
            raise RuntimeError("HealthyResidualProjector must be fitted first.")
        x_frame = _lagged_predictors(frame, self.predictors)
        x = x_frame.reindex(columns=self.predictor_columns_).to_numpy(dtype=np.float64)
        x = np.where(np.isfinite(x), x, self.medians_)
        patient = frame["patient_id"]
        blocks: dict[str, pd.Series] = {}
        z_columns = []
        for target, model in self.models_.items():
            actual = _observed(frame, target)
            residual = (actual.to_numpy() - model.predict(x)) / self.scales_[target]
            name = f"healthy_ref_{target}_z"
            series = pd.Series(residual, index=frame.index, dtype=np.float32)
            blocks[name] = series
            z_columns.append(name)
            for window in self.windows:
                grouped = series.abs().groupby(patient, sort=False)
                blocks[f"{name}_abs_mean_{window}h"] = grouped.rolling(
                    window, min_periods=1
                ).mean().reset_index(level=0, drop=True).sort_index().astype(np.float32)
                blocks[f"{name}_count_{window}h"] = grouped.rolling(
                    window, min_periods=1
                ).count().reset_index(level=0, drop=True).sort_index().astype(np.float32)
        result = pd.DataFrame(blocks, index=frame.index)
        if z_columns:
            result["healthy_ref_observed_mean_abs_z"] = result[z_columns].abs().mean(axis=1)
            result["healthy_ref_observed_max_abs_z"] = result[z_columns].abs().max(axis=1)
        return result


@dataclass
class OrthoBioProjector:
    bio: list[str]
    care_suffixes: list[str]
    care_context: list[str]
    alpha: float
    care_columns_: list[str] | None = None
    bio_columns_: list[str] | None = None
    care_mean_: np.ndarray | None = None
    care_scale_: np.ndarray | None = None
    bio_mean_: np.ndarray | None = None
    beta_: np.ndarray | None = None

    @classmethod
    def from_config(cls, config: dict) -> "OrthoBioProjector":
        return cls(
            bio=list(config["bio"]),
            care_suffixes=list(config["care_suffixes"]),
            care_context=list(config["care_context"]),
            alpha=float(config["ridge_alpha"]),
        )

    def fit(self, frame: pd.DataFrame) -> "OrthoBioProjector":
        self.bio_columns_ = [c for c in self.bio if c in frame]
        self.care_columns_ = [
            c for c in frame
            if any(c.endswith(suffix) for suffix in self.care_suffixes)
        ] + [c for c in self.care_context if c in frame]
        self.care_columns_ = list(dict.fromkeys(self.care_columns_))
        x = frame[self.care_columns_].to_numpy(dtype=np.float64)
        y = frame[self.bio_columns_].to_numpy(dtype=np.float64)
        self.care_mean_ = np.nanmedian(x, axis=0)
        self.care_scale_ = np.nanstd(x, axis=0)
        self.care_scale_ = np.where(
            np.isfinite(self.care_scale_) & (self.care_scale_ > 1e-6), self.care_scale_, 1.0
        )
        self.bio_mean_ = np.nanmedian(y, axis=0)
        x = np.nan_to_num((x - self.care_mean_) / self.care_scale_)
        y = np.where(np.isfinite(y), y, self.bio_mean_) - self.bio_mean_
        gram = x.T @ x
        gram.flat[:: len(gram) + 1] += self.alpha
        self.beta_ = np.linalg.solve(gram, x.T @ y)
        return self

    def transform(self, frame: pd.DataFrame) -> pd.DataFrame:
        if self.beta_ is None:
            raise RuntimeError("OrthoBioProjector must be fitted first.")
        x = frame[self.care_columns_].to_numpy(dtype=np.float64)
        y = frame[self.bio_columns_].to_numpy(dtype=np.float64)
        x = np.nan_to_num((x - self.care_mean_) / self.care_scale_)
        y = np.where(np.isfinite(y), y, self.bio_mean_) - self.bio_mean_
        residual = y - x @ self.beta_
        return pd.DataFrame(
            residual.astype(np.float32),
            columns=[f"orthobio_{c}_residual" for c in self.bio_columns_],
            index=frame.index,
        )

