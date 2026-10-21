"""Serialisable model wrapper shared by training, evaluation and the API."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression


class CalibratedEnsemble:
    """Mean of LightGBM members' scores, mapped to probabilities by isotonic regression.

    The calibrator is fitted on validation patients only, never on training rows.
    """

    def __init__(self, members: list, feature_columns: list[str], calibrator: IsotonicRegression | None = None):
        self.members = members
        self.feature_columns = feature_columns
        self.calibrator = calibrator

    def raw_score(self, X: pd.DataFrame) -> np.ndarray:
        X = X[self.feature_columns]
        return np.mean([m.predict_proba(X)[:, 1] for m in self.members], axis=0)

    def member_scores(self, X: pd.DataFrame) -> np.ndarray:
        X = X[self.feature_columns]
        return np.stack([m.predict_proba(X)[:, 1] for m in self.members])

    def calibrate(self, raw: np.ndarray) -> np.ndarray:
        if self.calibrator is None:
            return raw
        return self.calibrator.predict(raw)

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        p = self.calibrate(self.raw_score(X))
        return np.column_stack([1 - p, p])

    def uncertainty(self, X: pd.DataFrame) -> np.ndarray:
        """Spread of calibrated member probabilities (0 when a single member)."""
        return np.std([self.calibrate(s) for s in self.member_scores(X)], axis=0)

    def contributions(self, X: pd.DataFrame) -> np.ndarray:
        """TreeSHAP values in log-odds space, averaged over members. Last column is the bias."""
        X = X[self.feature_columns]
        return np.mean([m.predict(X, pred_contrib=True) for m in self.members], axis=0)
