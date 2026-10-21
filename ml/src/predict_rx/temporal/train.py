"""Training, prediction, and fold evaluation for temporal challengers."""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score

from predict_rx.eval.metrics import UtilityTable, best_utility_threshold
from predict_rx.temporal.data import (
    Normalizer,
    SequenceData,
    augment,
    length_batches,
    make_batch,
)
from predict_rx.temporal.models import build_model
from predict_rx.train.challenger import _pseudo_site_labels, _safe_ranking


@dataclass
class ExperimentSpec:
    name: str
    model: str
    params: dict[str, Any] = field(default_factory=dict)
    hazard_weight: float = 0.0
    aux_weight: float = 0.0
    consistency_weight: float = 0.0
    augment: bool = False
    augmentation: dict[str, float] = field(default_factory=lambda: {
        "lab_drop": 0.3, "lab_group_drop": 0.1, "vital_mask": 0.1, "delay_fraction": 0.3})
    lr: float = 1e-3
    weight_decay: float = 1e-4
    max_epochs: int = 25
    patience: int = 4
    max_tokens: int = 16000

    @classmethod
    def from_config(cls, name: str, payload: dict, defaults: dict) -> "ExperimentSpec":
        merged = {**defaults, **payload}
        return cls(name=name, **merged)


def _weighted_bce(logits_or_probs: torch.Tensor, target: torch.Tensor, weight: torch.Tensor,
                  *, probabilities: bool = False) -> torch.Tensor:
    if weight.sum() <= 0:
        return logits_or_probs.sum() * 0.0
    with torch.autocast(device_type=logits_or_probs.device.type, enabled=False):
        values, target, weight = logits_or_probs.float(), target.float(), weight.float()
        if probabilities:
            loss = F.binary_cross_entropy(values.clamp(1e-6, 1 - 1e-6), target, reduction="none")
        else:
            loss = F.binary_cross_entropy_with_logits(values, target, reduction="none")
        return (loss * weight).sum() / weight.sum()


def compute_loss(model, batch: dict, spec: ExperimentSpec, generator: torch.Generator) -> torch.Tensor:
    out = model(batch["x"], batch["m"], batch["static"], batch["iculos"])
    train_mask = batch["eligible"].float() * batch["weight"]
    loss = _weighted_bce(out["challenge_logit"], batch["label"], train_mask)

    if spec.hazard_weight:
        at_risk = torch.isfinite(batch["incident"]) & batch["eligible"].unsqueeze(-1)
        target = torch.nan_to_num(batch["incident"], nan=0.0)
        hazard_weight = at_risk.float() * batch["weight"].unsqueeze(-1)
        loss = loss + spec.hazard_weight * _weighted_bce(out["hazard_prob"], target, hazard_weight, probabilities=True)

    if spec.aux_weight:
        next_m = batch["m"][:, 1:]
        if next_m.any():
            error = (out["reconstruction"][:, :-1].float() - batch["x"][:, 1:]) ** 2
            loss = loss + spec.aux_weight * error[next_m].mean()

    if spec.augment:
        x_aug, m_aug = augment(batch["x"], batch["m"], generator, **spec.augmentation)
        out_aug = model(x_aug, m_aug, batch["static"], batch["iculos"])
        loss = loss + 0.5 * _weighted_bce(out_aug["challenge_logit"], batch["label"], train_mask)
        if spec.consistency_weight:
            valid = batch["valid"] & batch["eligible"]
            gap = (torch.sigmoid(out_aug["challenge_logit"].float())
                   - torch.sigmoid(out["challenge_logit"].float()).detach()) ** 2
            loss = loss + spec.consistency_weight * gap[valid].mean()
    return loss


@torch.no_grad()
def predict(model, data: SequenceData, patients: np.ndarray, norm: Normalizer, device: torch.device,
            max_tokens: int = 32000) -> dict[str, np.ndarray]:
    """Scores for every row of `patients`, in data row order (patients sorted by index)."""
    model.eval()
    patients = np.sort(patients)
    dummy_weights = np.ones(len(data.label), dtype=np.float32)
    challenge, hazard = {}, {}
    for batch_patients in length_batches(data, patients, max_tokens, rng=None):
        batch = make_batch(data, batch_patients, norm, dummy_weights, device)
        with torch.autocast(device_type=device.type, dtype=torch.bfloat16, enabled=device.type == "cuda"):
            out = model(batch["x"], batch["m"], batch["static"], batch["iculos"])
        logits = out["challenge_logit"].float().cpu().numpy()
        probs = out["hazard_prob"].float().cpu().numpy()
        for b, patient in enumerate(batch_patients):
            n = int(data.lengths()[patient])
            challenge[patient] = 1 / (1 + np.exp(-logits[b, :n]))
            hazard[patient] = probs[b, :n]
    return {
        "challenge": np.concatenate([challenge[p] for p in patients]),
        "hazard": np.concatenate([hazard[p] for p in patients]),
    }


def _early_stopping_score(model, data, patients, norm, device) -> float:
    rows = data.rows_for(np.sort(patients))
    scores = predict(model, data, patients, norm, device)["challenge"]
    eligible = data.eligible[rows]
    labels = data.label[rows][eligible]
    if len(np.unique(labels)) < 2:
        return float("nan")
    return float(average_precision_score(labels, scores[eligible]))


def train_model(data: SequenceData, fit_patients: np.ndarray, stop_patients: np.ndarray, spec: ExperimentSpec,
                *, weights: np.ndarray, device: torch.device, seed: int, log=print) -> tuple[Any, Normalizer, dict]:
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    generator = torch.Generator(device=device).manual_seed(seed)
    norm = Normalizer.fit(data, fit_patients)
    n_static = 2 * data.static.shape[1]
    model = build_model(spec.model, n_static, spec.params).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=spec.lr, weight_decay=spec.weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=spec.max_epochs)
    best_state, best_score, best_epoch, stale = None, -np.inf, -1, 0
    history = []
    for epoch in range(spec.max_epochs):
        model.train()
        started, total, batches = time.perf_counter(), 0.0, 0
        for batch_patients in length_batches(data, fit_patients, spec.max_tokens, rng):
            batch = make_batch(data, batch_patients, norm, weights, device)
            with torch.autocast(device_type=device.type, dtype=torch.bfloat16, enabled=device.type == "cuda"):
                loss = compute_loss(model, batch, spec, generator)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total += float(loss.detach())
            batches += 1
        scheduler.step()
        score = _early_stopping_score(model, data, stop_patients, norm, device)
        history.append({"epoch": epoch, "loss": total / max(batches, 1), "stop_auprc": score,
                        "seconds": time.perf_counter() - started})
        log(f"  epoch {epoch:02d} loss={total / max(batches, 1):.4f} stop_AUPRC={score:.4f} "
            f"({time.perf_counter() - started:.0f}s)")
        if score > best_score:
            best_state, best_score, best_epoch, stale = copy.deepcopy(model.state_dict()), score, epoch, 0
        else:
            stale += 1
            if stale >= spec.patience:
                break
    model.load_state_dict(best_state)
    model.eval()
    return model, norm, {"best_epoch": best_epoch, "best_stop_auprc": best_score, "history": history}


def evaluate_fold(frame_meta: pd.DataFrame, raw_calibration: np.ndarray, calibration_rows: np.ndarray,
                  raw_validation: np.ndarray, validation_rows: np.ndarray, train_rows: np.ndarray,
                  *, clusters: int, min_rows: int, seed: int) -> tuple[dict, np.ndarray]:
    """Same isotonic/threshold/metric protocol as the tabular challenger folds."""
    calibration = frame_meta.iloc[calibration_rows]
    validation = frame_meta.iloc[validation_rows]
    calibration_eligible = calibration["eligible"].to_numpy()
    calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1).fit(
        raw_calibration[calibration_eligible], calibration["SepsisLabel"].to_numpy()[calibration_eligible]
    )
    threshold, _ = best_utility_threshold(
        UtilityTable.from_frame(calibration), calibrator.predict(raw_calibration), calibration_eligible
    )
    probability = calibrator.predict(raw_validation)
    eligible = validation["eligible"].to_numpy()
    y = validation["SepsisLabel"].to_numpy()
    auroc, auprc = _safe_ranking(y[eligible], probability[eligible])
    utility = UtilityTable.from_frame(validation).normalized((probability >= threshold) & eligible)
    missing = [c for c in frame_meta if c.endswith("_missing")]
    sites = _pseudo_site_labels(frame_meta.iloc[train_rows][["patient_id"] + missing],
                                validation[["patient_id"] + missing], clusters=clusters, seed=seed)
    group_auprc = []
    for group in np.unique(sites):
        mask = eligible & (sites == group)
        if mask.sum() >= min_rows:
            _, score = _safe_ranking(y[mask], probability[mask])
            if score is not None:
                group_auprc.append(score)
    return {
        "auroc": auroc,
        "auprc": auprc,
        "normalized_utility": float(utility),
        "threshold": float(threshold),
        "worst_pseudo_site_auprc": min(group_auprc) if group_auprc else None,
    }, probability
