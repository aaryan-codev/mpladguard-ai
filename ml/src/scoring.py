"""
Risk scoring.

Isolation Forest's raw `score_samples` output is NOT a calibrated 0-100
risk score -- it is an unbounded "average path length" style value where
LOWER means MORE anomalous. This module documents and implements the
normalization strategy used to turn that into a stakeholder-facing
0-100 risk score:

    1. At training time we record the min/max (and a few percentiles) of
       score_samples() over the training set. These are saved in the
       model's metadata JSON.
    2. At inference time, a new project's raw score is linearly rescaled
       against that TRAINING reference range and inverted, so that:
         - a score at/below the training minimum (most anomalous seen) -> ~100
         - a score at/above the training maximum (most normal seen)    -> ~0
       Scores outside the observed training range are clipped to [0, 100].
    3. The resulting 0-100 value is bucketed into LOW/MEDIUM/HIGH using
       configurable thresholds (see config.RISK_LOW_MAX / RISK_MEDIUM_MAX).

This is a deliberately simple, transparent, and documented approach --
appropriate for an unsupervised MVP where there is no ground truth to
calibrate a probability against.
"""
from __future__ import annotations

import numpy as np

from . import config


def compute_score_reference(raw_scores: np.ndarray) -> dict:
    """Compute the reference statistics saved with a trained model."""
    return {
        "min": float(np.min(raw_scores)),
        "max": float(np.max(raw_scores)),
        "mean": float(np.mean(raw_scores)),
        "std": float(np.std(raw_scores)),
        "p25": float(np.percentile(raw_scores, 25)),
        "p50": float(np.percentile(raw_scores, 50)),
        "p75": float(np.percentile(raw_scores, 75)),
    }


def normalize_to_risk_score(raw_score: float, score_reference: dict) -> float:
    """
    Rescale a raw Isolation Forest score into a 0-100 risk score using the
    training reference range. Lower raw score => higher risk.
    """
    train_min = score_reference["min"]
    train_max = score_reference["max"]

    if train_max == train_min:
        # Degenerate training distribution (e.g. only 1 sample); avoid div/0.
        return 50.0

    normalized = (train_max - raw_score) / (train_max - train_min)
    risk_score = normalized * 100.0
    return float(np.clip(risk_score, 0.0, 100.0))


def risk_level_from_score(risk_score: float) -> str:
    if risk_score <= config.RISK_LOW_MAX:
        return "LOW"
    if risk_score <= config.RISK_MEDIUM_MAX:
        return "MEDIUM"
    return "HIGH"
