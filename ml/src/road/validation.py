"""
Validation and cleaning for the road-domain raw schema.

Mirrors ml/src/validation.py's philosophy: never silently drop/alter
data without recording it in a ValidationReport. Column set differs
because the road dataset has no financial-flow/contractor/tender/
inspection columns.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

import numpy as np
import pandas as pd

from . import config

logger = logging.getLogger(__name__)

DATE_COLUMNS = ["project_start_date", "project_completion_date"]

MONEY_COLUMNS = ["estimated_cost_lakh", "actual_expenditure_lakh"]

POSITIVE_NUMERIC_COLUMNS = [
    "road_length_km",
    "planned_duration_days",
    "actual_duration_days",
]


@dataclass
class RoadValidationReport:
    total_rows: int = 0
    dropped_rows: int = 0
    corrected_cells: int = 0
    issues: List[str] = field(default_factory=list)

    def log_summary(self) -> None:
        logger.debug(
            "Road validation complete: %d/%d rows kept, %d dropped, %d cells corrected.",
            self.total_rows - self.dropped_rows,
            self.total_rows,
            self.dropped_rows,
            self.corrected_cells,
        )
        for issue in self.issues[:20]:
            logger.warning(issue)


def validate_and_clean(df: pd.DataFrame) -> tuple[pd.DataFrame, RoadValidationReport]:
    df = df.copy()
    report = RoadValidationReport(total_rows=len(df))

    missing_cols = [c for c in config.REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise KeyError(f"Road dataset missing required columns: {missing_cols}")

    # --- Duplicate project IDs ---------------------------------------------
    dup_mask = df["project_id"].duplicated(keep="last")
    if dup_mask.any():
        dup_ids = df.loc[dup_mask, "project_id"].unique().tolist()
        report.issues.append(f"Removed {dup_mask.sum()} duplicate project_id rows: {dup_ids[:10]}")
        report.dropped_rows += int(dup_mask.sum())
        df = df.loc[~dup_mask].copy()

    # --- Parse dates ---------------------------------------------------------
    for col in DATE_COLUMNS:
        if col in df.columns:
            parsed = pd.to_datetime(df[col], errors="coerce")
            invalid = parsed.isna() & df[col].notna()
            if invalid.any():
                report.issues.append(f"{invalid.sum()} invalid dates in '{col}' set to NaT")
                report.corrected_cells += int(invalid.sum())
            df[col] = parsed

    # --- project_completion_date before project_start_date -------------------
    if {"project_start_date", "project_completion_date"}.issubset(df.columns):
        bad_order = (
            df["project_completion_date"].notna()
            & df["project_start_date"].notna()
            & (df["project_completion_date"] < df["project_start_date"])
        )
        if bad_order.any():
            report.issues.append(
                f"{bad_order.sum()} rows have project_completion_date before project_start_date; "
                "completion date set to NaT"
            )
            report.corrected_cells += int(bad_order.sum())
            df.loc[bad_order, "project_completion_date"] = pd.NaT

    # --- Money columns: coerce numeric, clip negatives ------------------------
    for col in MONEY_COLUMNS:
        numeric = pd.to_numeric(df[col], errors="coerce")
        non_numeric = numeric.isna() & df[col].notna()
        if non_numeric.any():
            report.issues.append(f"{non_numeric.sum()} non-numeric values in '{col}' set to NaN")
            report.corrected_cells += int(non_numeric.sum())
        negative = numeric < 0
        if negative.any():
            report.issues.append(f"{negative.sum()} negative values in '{col}' clipped to NaN")
            report.corrected_cells += int(negative.sum())
            numeric = numeric.mask(negative)
        df[col] = numeric

    # --- Positive numeric columns (length, durations) -------------------------
    for col in POSITIVE_NUMERIC_COLUMNS:
        numeric = pd.to_numeric(df[col], errors="coerce")
        non_positive = numeric <= 0
        if non_positive.any():
            report.issues.append(
                f"{non_positive.sum()} non-positive values in '{col}' set to NaN"
            )
            report.corrected_cells += int(non_positive.sum())
            numeric = numeric.mask(non_positive)
        df[col] = numeric

    # --- project_status must be a known value ---------------------------------
    unknown_status = ~df["project_status"].isin(config.VALID_PROJECT_STATUSES)
    if unknown_status.any():
        report.issues.append(
            f"{unknown_status.sum()} rows have unrecognized project_status values; "
            f"expected one of {config.VALID_PROJECT_STATUSES}"
        )
        report.corrected_cells += int(unknown_status.sum())

    # --- Replace inf with NaN everywhere (defensive) --------------------------
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    if len(numeric_cols):
        inf_mask = np.isinf(df[numeric_cols]).any(axis=1)
        if inf_mask.any():
            report.issues.append(f"{inf_mask.sum()} rows contained infinite values; replaced with NaN")
            report.corrected_cells += int(inf_mask.sum())
            df[numeric_cols] = df[numeric_cols].replace([np.inf, -np.inf], np.nan)

    # --- Drop rows missing essential identifiers/cost basis --------------------
    essential = ["project_id", "estimated_cost_lakh", "actual_expenditure_lakh", "road_length_km"]
    missing_essential = df[essential].isna().any(axis=1)
    if missing_essential.any():
        report.issues.append(f"Dropped {missing_essential.sum()} rows missing essential fields {essential}")
        report.dropped_rows += int(missing_essential.sum())
        df = df.loc[~missing_essential].copy()

    report.log_summary()
    return df.reset_index(drop=True), report
