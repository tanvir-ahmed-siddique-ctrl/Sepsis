"""Patient-level train / validation / test splitting."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml


@dataclass
class SplitConfig:
    seed: int = 42
    train_frac: float = 0.70
    val_frac: float = 0.15
    # remaining → test within Dataset A; Dataset B is separate folder


def assign_patient_splits(
    patient_ids: list[str],
    cfg: SplitConfig | None = None,
) -> dict[str, str]:
    cfg = cfg or SplitConfig()
    rng = np.random.default_rng(cfg.seed)
    ids = np.array(sorted(set(patient_ids)))
    rng.shuffle(ids)
    n = len(ids)
    n_train = int(n * cfg.train_frac)
    n_val = int(n * cfg.val_frac)
    mapping: dict[str, str] = {}
    for i, pid in enumerate(ids):
        if i < n_train:
            mapping[pid] = "train"
        elif i < n_train + n_val:
            mapping[pid] = "val"
        else:
            mapping[pid] = "test"
    return mapping


def load_split_config(path: Path) -> SplitConfig:
    raw = yaml.safe_load(path.read_text()) if path.exists() else {}
    return SplitConfig(**{k: v for k, v in (raw or {}).items() if k in SplitConfig.__dataclass_fields__})
