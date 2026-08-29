"""
Feature engineering for the road domain.

Every feature here is computed directly from columns that actually
exist in the road dataset (see config.REQUIRED_COLUMNS) -- nothing is
backfilled or assumed from the generic MPLADS schema.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    num = pd.to_numeric(numerator, errors="coerce")
    den = pd.to_numeric(denominator, errors="coerce")
    with np.errstate(divide="ignore", invalid="ignore"):
        result = num / den
    result = result.replace([np.inf, -np.inf], np.nan)
    result = result.mask(den == 0, np.nan)
    return result


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute road-specific engineered features and append them as columns.

    1. cost_deviation = (actual_expenditure - estimated_cost) / estimated_cost
    2. cost_per_km_estimated = estimated_cost / road_length_km
    3. cost_per_km_actual = actual_expenditure / road_length_km
    4. cost_per_km_ratio = cost_per_km_actual / cost_per_km_estimated
    5. delay_ratio = actual_duration_days / planned_duration_days
    6. delay_days_normalized = (actual_duration - planned_duration) / planned_duration
       (kept distinct from delay_ratio so a project that is merely "1 day
       over" on a very short project doesn't get the same emphasis as one
       that is genuinely proportionally very late -- both are informative.)
    """
    df = df.copy()

    df["cost_deviation"] = _safe_divide(
        df["actual_expenditure_lakh"] - df["estimated_cost_lakh"], df["estimated_cost_lakh"]
    )

    df["cost_per_km_estimated"] = _safe_divide(df["estimated_cost_lakh"], df["road_length_km"])
    df["cost_per_km_actual"] = _safe_divide(df["actual_expenditure_lakh"], df["road_length_km"])
    df["cost_per_km_ratio"] = _safe_divide(df["cost_per_km_actual"], df["cost_per_km_estimated"])

    df["delay_ratio"] = _safe_divide(df["actual_duration_days"], df["planned_duration_days"])
    df["delay_days_normalized"] = _safe_divide(
        df["actual_duration_days"] - df["planned_duration_days"], df["planned_duration_days"]
    )

    feature_cols = config.ENGINEERED_FEATURES
    df[feature_cols] = df[feature_cols].replace([np.inf, -np.inf], np.nan)

    return df


def get_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in config.ENGINEERED_FEATURES if c not in df.columns]
    if missing:
        raise KeyError(f"Road engineered features missing from DataFrame: {missing}")
    return df[config.ENGINEERED_FEATURES].copy()
