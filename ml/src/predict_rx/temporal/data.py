"""Hourly sparse-event tensors for temporal models.

Each patient-hour carries, per variable, the value *only if measured that
hour* plus the measurement mask. Carried-forward values and time-since-last
measurement are recomputed inside the model from (value, mask), so augmented
views (dropped labs, delayed vitals) stay internally consistent.

Rows keep the exact order of the feature Parquet, so predictions align with
the tabular models, the metrics code, and the pseudo-site labels.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import torch

from predict_rx.eval.metrics import DT_OPTIMAL
from predict_rx.features.schema import LAB_COLS, MIN_HOURS_BEFORE_PRED, VITAL_COLS

VARIABLES = VITAL_COLS + LAB_COLS
STATIC = ["Age", "Gender", "Unit1", "Unit2", "HospAdmTime"]
HORIZONS = (1, 3, 6, 12)
MAX_HOURS = 336


@dataclass
class SequenceData:
    patient_ids: np.ndarray        # [P]
    split: np.ndarray              # [P]
    offsets: np.ndarray            # [P + 1] row offsets into the flat arrays
    values: np.ndarray             # [N, V] raw value where measured else NaN
    mask: np.ndarray               # [N, V] bool measured this hour
    static: np.ndarray             # [P, S]
    iculos: np.ndarray             # [N]
    label: np.ndarray              # [N] official SepsisLabel
    eligible: np.ndarray           # [N] hours_observed >= MIN_HOURS_BEFORE_PRED
    incident: np.ndarray           # [N, H] 0/1, NaN when censored (at/after onset)

    def lengths(self) -> np.ndarray:
        return np.diff(self.offsets)

    def rows_for(self, patient_indices: np.ndarray) -> np.ndarray:
        return np.concatenate([np.arange(self.offsets[i], self.offsets[i + 1]) for i in patient_indices])


def incident_targets(labels: np.ndarray, offsets: np.ndarray, horizons=HORIZONS) -> np.ndarray:
    """Onset = first positive SepsisLabel position + 6 h; post-onset rows censored (NaN)."""
    out = np.zeros((len(labels), len(horizons)), dtype=np.float32)
    for start, end in zip(offsets[:-1], offsets[1:]):
        patient = labels[start:end]
        if not patient.any():
            continue
        onset = int(np.argmax(patient)) - DT_OPTIMAL
        positions = np.arange(end - start)
        to_onset = onset - positions
        for k, horizon in enumerate(horizons):
            column = ((to_onset >= 1) & (to_onset <= horizon)).astype(np.float32)
            column[positions >= onset] = np.nan
            out[start:end, k] = column
    return out


def load_sequences(path: Path, splits: tuple[str, ...]) -> SequenceData:
    columns = ["patient_id", "split", "SepsisLabel", "hours_observed", "ICULOS"] + STATIC
    columns += VARIABLES + [f"{v}_missing" for v in VARIABLES]
    table = pq.read_table(path, columns=columns, filters=[("split", "in", list(splits))])
    frame = table.to_pandas()
    ids = frame["patient_id"].to_numpy()
    change = np.flatnonzero(ids[1:] != ids[:-1]) + 1
    offsets = np.concatenate([[0], change, [len(ids)]])
    mask = frame[[f"{v}_missing" for v in VARIABLES]].to_numpy() == 0
    values = np.where(mask, frame[VARIABLES].to_numpy(dtype=np.float32), np.nan).astype(np.float32)
    first = frame.iloc[offsets[:-1]]
    static = first[STATIC].to_numpy(dtype=np.float32)
    label = frame["SepsisLabel"].to_numpy(dtype=np.int8)
    if (np.diff(offsets) > MAX_HOURS).any():
        raise ValueError(f"Stay longer than {MAX_HOURS} hours; extend MAX_HOURS.")
    return SequenceData(
        patient_ids=first["patient_id"].to_numpy(),
        split=first["split"].astype(str).to_numpy(),
        offsets=offsets,
        values=values,
        mask=mask,
        static=static,
        iculos=frame["ICULOS"].to_numpy(dtype=np.float32),
        label=label,
        eligible=frame["hours_observed"].to_numpy() >= MIN_HOURS_BEFORE_PRED,
        incident=incident_targets(label, offsets),
    )


@dataclass
class Normalizer:
    """Fitted on training-fold patients only."""

    mean: np.ndarray
    std: np.ndarray
    static_mean: np.ndarray
    static_std: np.ndarray

    @classmethod
    def fit(cls, data: SequenceData, patient_indices: np.ndarray) -> "Normalizer":
        rows = data.rows_for(patient_indices)
        values = data.values[rows]
        static = data.static[patient_indices]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            mean = np.nanmean(values, axis=0)
            std = np.nanstd(values, axis=0)
            static_mean = np.nan_to_num(np.nanmean(static, axis=0), nan=0.0)
            static_std = np.nanstd(static, axis=0)
        mean = np.nan_to_num(mean, nan=0.0)
        std = np.where(np.isfinite(std) & (std > 1e-6), std, 1.0)
        static_std = np.where(np.isfinite(static_std) & (static_std > 1e-6), static_std, 1.0)
        return cls(mean.astype(np.float32), std.astype(np.float32),
                   static_mean.astype(np.float32), static_std.astype(np.float32))

    def as_dict(self) -> dict:
        return {key: getattr(self, key).tolist() for key in ("mean", "std", "static_mean", "static_std")}

    @classmethod
    def from_dict(cls, payload: dict) -> "Normalizer":
        return cls(*(np.asarray(payload[key], dtype=np.float32) for key in ("mean", "std", "static_mean", "static_std")))


def patient_row_weights(data: SequenceData, *, window_hours: int = 12, window_multiplier: float = 2.0,
                        positive_multiplier: float = 1.5) -> np.ndarray:
    """Same weighting as the tabular challenger: patient-balanced, onset-window emphasis."""
    weights = np.empty(len(data.label), dtype=np.float32)
    for start, end in zip(data.offsets[:-1], data.offsets[1:]):
        labels = data.label[start:end]
        w = np.full(end - start, 1.0 / (end - start), dtype=np.float32)
        if labels.any():
            onset = int(np.argmax(labels)) - DT_OPTIMAL
            lead = onset - np.arange(end - start)
            w *= np.where((lead >= 0) & (lead <= window_hours), window_multiplier, 1.0)
        w *= np.where(labels == 1, positive_multiplier, 1.0)
        weights[start:end] = w
    return weights / weights.mean()


def make_batch(data: SequenceData, patient_indices: np.ndarray, norm: Normalizer, weights: np.ndarray,
               device: torch.device) -> dict[str, torch.Tensor]:
    lengths = data.lengths()[patient_indices]
    batch, horizon = len(patient_indices), max(int(lengths.max()), 1)
    n_var = len(VARIABLES)
    x = np.zeros((batch, horizon, n_var), dtype=np.float32)
    m = np.zeros((batch, horizon, n_var), dtype=bool)
    iculos = np.zeros((batch, horizon), dtype=np.float32)
    label = np.zeros((batch, horizon), dtype=np.float32)
    eligible = np.zeros((batch, horizon), dtype=bool)
    incident = np.full((batch, horizon, len(HORIZONS)), np.nan, dtype=np.float32)
    weight = np.zeros((batch, horizon), dtype=np.float32)
    valid = np.zeros((batch, horizon), dtype=bool)
    for b, patient in enumerate(patient_indices):
        start, end = data.offsets[patient], data.offsets[patient + 1]
        n = end - start
        raw = (data.values[start:end] - norm.mean) / norm.std
        mask = data.mask[start:end]
        x[b, :n] = np.clip(np.where(mask, raw, 0.0), -6, 6)
        m[b, :n] = mask
        iculos[b, :n] = data.iculos[start:end]
        label[b, :n] = data.label[start:end]
        eligible[b, :n] = data.eligible[start:end]
        incident[b, :n] = data.incident[start:end]
        weight[b, :n] = weights[start:end]
        valid[b, :n] = True
    static = np.nan_to_num((data.static[patient_indices] - norm.static_mean) / norm.static_std, nan=0.0)
    static_missing = np.isnan(data.static[patient_indices]).astype(np.float32)
    tensor = lambda a, dtype=torch.float32: torch.as_tensor(a, dtype=dtype, device=device)  # noqa: E731
    return {
        "x": tensor(x), "m": tensor(m, torch.bool), "iculos": tensor(iculos),
        "static": tensor(np.concatenate([static, static_missing], axis=1)),
        "label": tensor(label), "eligible": tensor(eligible, torch.bool),
        "incident": tensor(incident), "weight": tensor(weight), "valid": tensor(valid, torch.bool),
    }


def length_batches(data: SequenceData, patient_indices: np.ndarray, max_tokens: int,
                   rng: np.random.Generator | None) -> list[np.ndarray]:
    """Group patients of similar length so padding stays small; shuffle batch order."""
    lengths = data.lengths()[patient_indices]
    order = patient_indices[np.argsort(lengths, kind="stable")]
    if rng is not None:
        order = order[np.argsort(data.lengths()[order] + rng.random(len(order)) * 4, kind="stable")]
    batches, current, longest = [], [], 0
    for patient in order:
        n = int(data.lengths()[patient])
        if current and max(longest, n) * (len(current) + 1) > max_tokens:
            batches.append(np.asarray(current))
            current, longest = [], 0
        current.append(patient)
        longest = max(longest, n)
    if current:
        batches.append(np.asarray(current))
    if rng is not None:
        rng.shuffle(batches)
    return batches


def augment(x: torch.Tensor, m: torch.Tensor, generator: torch.Generator, *, lab_drop: float,
            lab_group_drop: float, vital_mask: float, delay_fraction: float) -> tuple[torch.Tensor, torch.Tensor]:
    """Clinically plausible sampling perturbations applied to observed events only."""
    n_vital = len(VITAL_COLS)
    batch, horizon, n_var = x.shape
    device = x.device
    keep = torch.ones_like(m)
    rand = lambda *shape: torch.rand(*shape, generator=generator, device=device)  # noqa: E731
    keep[..., n_vital:] &= rand(batch, horizon, n_var - n_vital) >= lab_drop
    keep[..., n_vital:] &= (rand(batch, 1, n_var - n_vital) >= lab_group_drop)
    keep[..., :n_vital] &= rand(batch, horizon, n_vital) >= vital_mask
    m_aug = m & keep
    x_aug = x * m_aug
    delayed = rand(batch) < delay_fraction
    if delayed.any() and horizon > 2:
        shift = torch.where(rand(batch) < 0.5, 1, 2)
        for d in (1, 2):
            rows = delayed & (shift == d)
            if rows.any():
                vx = x_aug[rows, :, :n_vital].clone()
                vm = m_aug[rows, :, :n_vital].clone()
                x_aug[rows, d:, :n_vital] = vx[:, :-d]
                m_aug[rows, d:, :n_vital] = vm[:, :-d]
                x_aug[rows, :d, :n_vital] = 0
                m_aug[rows, :d, :n_vital] = False
    return x_aug, m_aug


def carry_forward(x: torch.Tensor, m: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Last observed value, ever-observed flag, and normalized log hours since last measurement."""
    horizon = x.shape[1]
    t = torch.arange(horizon, device=x.device).view(1, -1, 1).expand_as(m)
    index = torch.where(m, t, torch.full_like(t, -1))
    last = torch.cummax(index, dim=1).values
    ever = last >= 0
    x_last = torch.gather(x, 1, last.clamp(min=0)) * ever
    delta = torch.where(ever, t - last, t + 1).float()
    log_delta = torch.log1p(delta) / np.log1p(MAX_HOURS)
    return x_last, ever.float(), log_delta
