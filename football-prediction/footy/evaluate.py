"""Step 5: how good are the probabilities?

* Log loss    - punishes confident wrong predictions hard. Lower is better.
                Guessing 1/3 for everything gives ln(3) = 1.0986.
* Brier score - average squared error between probabilities and what happened
                (we sum over the 3 outcomes, so it ranges 0..2). Lower is better.
                Guessing 1/3 for everything gives 0.667.
* Accuracy    - how often the most likely outcome happened. Easy to understand,
                but it ignores HOW confident we were, so it's the least useful here.
* Calibration - when we say "40%", does it happen about 40% of the time?
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from footy.models import OUTCOMES

EPS = 1e-15


def one_hot(y_idx, n_classes=3) -> np.ndarray:
    return np.eye(n_classes)[np.asarray(y_idx)]


def log_loss(probs, y_idx) -> float:
    p = np.clip(np.asarray(probs, dtype=float), EPS, 1)
    return float(-np.mean(np.log(p[np.arange(len(p)), y_idx])))


def brier(probs, y_idx) -> float:
    probs = np.asarray(probs, dtype=float)
    return float(np.mean(np.sum((probs - one_hot(y_idx, probs.shape[1])) ** 2, axis=1)))


def accuracy(probs, y_idx) -> float:
    return float(np.mean(np.argmax(probs, axis=1) == np.asarray(y_idx)))


def binary_log_loss(p, y) -> float:
    p = np.clip(np.asarray(p, dtype=float), EPS, 1 - EPS)
    y = np.asarray(y, dtype=float)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def binary_brier(p, y) -> float:
    return float(np.mean((np.asarray(p, dtype=float) - np.asarray(y, dtype=float)) ** 2))


def calibration_table(probs, y_idx, n_bins=10, labels=OUTCOMES) -> pd.DataFrame:
    """For each outcome, group predictions into probability bins and compare the
    average predicted probability with how often that outcome actually happened."""
    probs = np.asarray(probs, dtype=float)
    y = one_hot(y_idx, probs.shape[1])
    edges = np.linspace(0, 1, n_bins + 1)
    rows = []
    for k, label in enumerate(labels):
        bins = np.clip(np.digitize(probs[:, k], edges) - 1, 0, n_bins - 1)
        for b in range(n_bins):
            mask = bins == b
            if mask.any():
                rows.append({"outcome": label, "bin": b, "n": int(mask.sum()),
                             "mean_predicted": float(probs[mask, k].mean()),
                             "observed_frequency": float(y[mask, k].mean())})
    return pd.DataFrame(rows)


def expected_calibration_error(probs, y_idx, n_bins=10) -> float:
    """Weighted average gap between predicted and observed (0 = perfectly calibrated)."""
    t = calibration_table(probs, y_idx, n_bins)
    if t.empty:
        return float("nan")
    gaps = (t.mean_predicted - t.observed_frequency).abs() * t.n
    return float(gaps.groupby(t.outcome).sum().sum() / t.groupby("outcome").n.sum().sum())


def outcome_metrics(probs, y_idx) -> dict:
    return {"n_matches": int(len(y_idx)),
            "log_loss": log_loss(probs, y_idx),
            "brier": brier(probs, y_idx),
            "accuracy": accuracy(probs, y_idx),
            "calibration_error": expected_calibration_error(probs, y_idx)}
