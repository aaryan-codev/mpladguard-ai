"""
Explainability layer.

Isolation Forest itself does not tell you WHY a point is anomalous -- it
only tells you THAT it is. To make risk scores meaningful to a human
reviewer, this module compares each engineered feature of a project
against the reference distribution of that feature observed during
training (median + standard deviation, robust z-score style), and turns
large deviations into plain-language explanations.

This is explicitly RULE-BASED / STATISTICAL, not a causal claim from the
model. We never say "the model found X caused this" -- we say "X is
statistically unusual compared to other projects of this type."
"""
from __future__ import annotations

from typing import Any

import numpy as np

from . import config

# How many standard deviations away from the median before a feature is
# flagged, and at what threshold it becomes "high" severity.
MEDIUM_Z_THRESHOLD = 1.5
HIGH_Z_THRESHOLD = 2.5

MAX_RISK_FACTORS = 5


def compute_feature_reference(feature_df, engineered_features: list[str] | None = None) -> dict:
    """
    Compute per-feature median/std reference stats from the (imputed)
    training feature matrix. Saved into model metadata.

    engineered_features: which columns to compute reference stats for.
    Defaults to the generic pipeline's config.ENGINEERED_FEATURES for
    backward compatibility; domain plugins (e.g. ml/src/road) pass
    their own feature list.
    """
    engineered_features = engineered_features or config.ENGINEERED_FEATURES
    reference = {}
    for col in engineered_features:
        series = feature_df[col].dropna()
        if len(series) == 0:
            reference[col] = {"median": 0.0, "std": 1.0}
            continue
        median = float(series.median())
        std = float(series.std(ddof=0)) or 1.0
        reference[col] = {"median": median, "std": std}
    return reference


def _robust_z(value: float, median: float, std: float) -> float:
    if std == 0 or np.isnan(std):
        std = 1.0
    return (value - median) / std


def _severity(z: float) -> str | None:
    az = abs(z)
    if az >= HIGH_Z_THRESHOLD:
        return "high"
    if az >= MEDIUM_Z_THRESHOLD:
        return "medium"
    return None


def _direction_word(z: float) -> str:
    return "higher" if z > 0 else "lower"


def generate_risk_factors(
    feature_values: dict[str, Any],
    feature_reference: dict,
    max_factors: int = MAX_RISK_FACTORS,
    engineered_features: list[str] | None = None,
    feature_descriptions: dict | None = None,
) -> list[dict]:
    """
    Compare a project's engineered features against the training reference
    distribution and return the most unusual ones as structured, explained
    risk factors, sorted by severity (most unusual first).

    engineered_features / feature_descriptions: override the generic
    pipeline's config for domain-specific feature sets (e.g. road).
    Defaults preserve existing behavior for the generic pipeline.
    """
    engineered_features = engineered_features or config.ENGINEERED_FEATURES
    feature_descriptions = feature_descriptions or config.FEATURE_DESCRIPTIONS
    candidates = []

    for feature in engineered_features:
        value = feature_values.get(feature)
        if value is None or (isinstance(value, float) and np.isnan(value)):
            continue

        ref = feature_reference.get(feature, {"median": 0.0, "std": 1.0})
        z = _robust_z(value, ref["median"], ref["std"])
        severity = _severity(z)
        if severity is None:
            continue

        direction = _direction_word(z)
        description = feature_descriptions.get(feature, feature)
        explanation = (
            f"{description} is {direction} than typical for similar projects "
            f"(value={round(value, 3)}, reference median={round(ref['median'], 3)})."
        )

        candidates.append(
            {
                "feature": feature,
                "value": round(float(value), 4),
                "severity": severity,
                "z_score": round(float(z), 2),
                "explanation": explanation,
            }
        )

    candidates.sort(key=lambda c: abs(c["z_score"]), reverse=True)
    return candidates[:max_factors]
