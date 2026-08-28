"""
Feature engineering.

Converts validated raw project rows into the numerical feature set the
Isolation Forest model is trained on. All divisions are guarded against
zero/NaN denominators. Output is guaranteed to contain no inf values,
but MAY contain NaN (imputation happens later in preprocessing.py).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Elementwise division that returns NaN instead of inf/-inf for zero denominators."""
    num = pd.to_numeric(numerator, errors="coerce")
    den = pd.to_numeric(denominator, errors="coerce")
    with np.errstate(divide="ignore", invalid="ignore"):
        result = num / den
    result = result.replace([np.inf, -np.inf], np.nan)
    result = result.mask(den == 0, np.nan)
    return result


def engineer_features(df: pd.DataFrame, reference_date: pd.Timestamp | None = None) -> pd.DataFrame:
    """
    Compute engineered features and append them as new columns.

    Parameters
    ----------
    df: validated project DataFrame (see validation.validate_and_clean).
    reference_date: the "as of" date used for inspection_gap_days.
        Defaults to now (pd.Timestamp.now()) for inference; training should
        pass a fixed reference_date for reproducibility if desired.
    """
    df = df.copy()
    reference_date = reference_date or pd.Timestamp.now()

    # 1. cost_deviation = (actual_cost - estimated_cost) / estimated_cost
    df["cost_deviation"] = _safe_divide(
        df["actual_cost"] - df["estimated_cost"], df["estimated_cost"]
    )

    # 2. fund_utilization_ratio = utilized_amount / released_amount
    df["fund_utilization_ratio"] = _safe_divide(df["utilized_amount"], df["released_amount"])

    # 3. financial_physical_progress_gap = financial_progress - physical_progress
    df["financial_physical_progress_gap"] = pd.to_numeric(
        df["financial_progress"], errors="coerce"
    ) - pd.to_numeric(df["physical_progress"], errors="coerce")

    # 4. delay_ratio = actual_duration / planned_duration
    planned_duration = (
        pd.to_datetime(df["planned_completion_date"], errors="coerce")
        - pd.to_datetime(df["work_order_date"], errors="coerce")
    ).dt.days
    actual_end = pd.to_datetime(df["actual_completion_date"], errors="coerce")
    # For projects not yet completed, use "today" as the running actual duration.
    actual_end = actual_end.fillna(reference_date)
    actual_duration = (actual_end - pd.to_datetime(df["work_order_date"], errors="coerce")).dt.days
    df["delay_ratio"] = _safe_divide(actual_duration, planned_duration)

    # 5. inspection_gap_days = days since last inspection
    last_inspection = pd.to_datetime(df["last_inspection_date"], errors="coerce")
    df["inspection_gap_days"] = (reference_date - last_inspection).dt.days
    # If never inspected, treat as a very large (but finite) gap rather than NaN,
    # since "never inspected" is itself a strong risk signal.
    never_inspected = last_inspection.isna()
    if never_inspected.any():
        cap = df["inspection_gap_days"].max()
        cap = cap if pd.notna(cap) else 365
        df.loc[never_inspected, "inspection_gap_days"] = max(cap, 365)

    # 6. contract_estimate_ratio = contract_value / estimated_cost
    df["contract_estimate_ratio"] = _safe_divide(df["contract_value"], df["estimated_cost"])

    # 7. cost_per_beneficiary = actual_cost / estimated_beneficiaries
    df["cost_per_beneficiary"] = _safe_divide(df["actual_cost"], df["estimated_beneficiaries"])

    # 8. tender_estimate_ratio = winning_bid / estimated_tender_value
    df["tender_estimate_ratio"] = _safe_divide(df["winning_bid"], df["estimated_tender_value"])

    # 9. bid_competition_indicator: normalized bid_count (more bids = more competition = lower risk)
    bid_count = pd.to_numeric(df["bid_count"], errors="coerce")
    df["bid_competition_indicator"] = bid_count.clip(lower=0)

    # 10. unresolved_issue_ratio = (issues_reported - issues_resolved) / issues_reported
    issues_reported = pd.to_numeric(df["issues_reported"], errors="coerce")
    issues_resolved = pd.to_numeric(df["issues_resolved"], errors="coerce")
    unresolved = issues_reported - issues_resolved
    df["unresolved_issue_ratio"] = _safe_divide(unresolved, issues_reported)
    # A project with zero reported issues has an undefined ratio; treat as 0
    # (no evidence of unresolved issues) rather than NaN/anomalous.
    df.loc[issues_reported == 0, "unresolved_issue_ratio"] = 0.0

    # Final safety net: no infs should ever leave this function.
    feature_cols = config.ENGINEERED_FEATURES
    df[feature_cols] = df[feature_cols].replace([np.inf, -np.inf], np.nan)

    return df


def get_feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    """Extract just the engineered feature columns, in the canonical order."""
    missing = [c for c in config.ENGINEERED_FEATURES if c not in df.columns]
    if missing:
        raise KeyError(f"Engineered features missing from DataFrame: {missing}")
    return df[config.ENGINEERED_FEATURES].copy()
