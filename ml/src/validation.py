"""
Dataset validation.

Catches structurally invalid rows (bad dates, out-of-range percentages,
negative money values, duplicate IDs) BEFORE feature engineering, so a
handful of corrupt rows can't silently poison the model.

Invalid rows are not silently dropped without a trace: every row that is
removed or corrected is recorded in a ValidationReport that callers can
inspect/log.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List

import numpy as np
import pandas as pd

from . import config

logger = logging.getLogger(__name__)

DATE_COLUMNS = [
    "sanction_date",
    "work_order_date",
    "planned_completion_date",
    "actual_completion_date",
    "last_inspection_date",
]

MONEY_COLUMNS = [
    "estimated_cost",
    "sanctioned_amount",
    "released_amount",
    "utilized_amount",
    "actual_cost",
    "contract_value",
    "estimated_tender_value",
    "winning_bid",
    "second_lowest_bid",
]

PERCENTAGE_COLUMNS = ["physical_progress", "financial_progress"]


@dataclass
class ValidationReport:
    total_rows: int = 0
    dropped_rows: int = 0
    corrected_cells: int = 0
    issues: List[str] = field(default_factory=list)

    def log_summary(self) -> None:
        logger.info(
            "Validation complete: %d/%d rows kept, %d dropped, %d cells corrected.",
            self.total_rows - self.dropped_rows,
            self.total_rows,
            self.dropped_rows,
            self.corrected_cells,
        )
        for issue in self.issues[:20]:
            logger.warning(issue)
        if len(self.issues) > 20:
            logger.warning("... %d additional validation issues suppressed.", len(self.issues) - 20)


def validate_and_clean(df: pd.DataFrame) -> tuple[pd.DataFrame, ValidationReport]:
    """
    Validate and lightly clean a raw project DataFrame.

    Returns (cleaned_df, report). Never raises for row-level data quality
    issues; instead it drops/corrects and records what happened so it is
    fully auditable.
    """
    df = df.copy()
    report = ValidationReport(total_rows=len(df))

    # --- Duplicate project IDs -------------------------------------------------
    dup_mask = df["project_id"].duplicated(keep="last")
    if dup_mask.any():
        dup_ids = df.loc[dup_mask, "project_id"].unique().tolist()
        report.issues.append(f"Removed {dup_mask.sum()} duplicate project_id rows: {dup_ids[:10]}")
        report.dropped_rows += int(dup_mask.sum())
        df = df.loc[~dup_mask].copy()

    # --- Parse dates -------------------------------------------------------
    for col in DATE_COLUMNS:
        if col in df.columns:
            parsed = pd.to_datetime(df[col], errors="coerce")
            invalid = parsed.isna() & df[col].notna()
            if invalid.any():
                report.issues.append(f"{invalid.sum()} invalid dates in '{col}' set to NaT")
                report.corrected_cells += int(invalid.sum())
            df[col] = parsed

    # --- Inconsistent date ordering -----------------------------------------
    # actual_completion_date should not be before work_order_date/sanction_date
    if {"work_order_date", "actual_completion_date"}.issubset(df.columns):
        bad_order = (
            df["actual_completion_date"].notna()
            & df["work_order_date"].notna()
            & (df["actual_completion_date"] < df["work_order_date"])
        )
        if bad_order.any():
            report.issues.append(
                f"{bad_order.sum()} rows have actual_completion_date before work_order_date; "
                "actual_completion_date set to NaT"
            )
            report.corrected_cells += int(bad_order.sum())
            df.loc[bad_order, "actual_completion_date"] = pd.NaT

    # --- Negative financial values ------------------------------------------
    for col in MONEY_COLUMNS:
        if col in df.columns:
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

    # --- Percentage bounds ----------------------------------------------------
    for col in PERCENTAGE_COLUMNS:
        if col in df.columns:
            numeric = pd.to_numeric(df[col], errors="coerce")
            out_of_range = (numeric < config.PROGRESS_MIN) | (numeric > config.PROGRESS_MAX)
            if out_of_range.any():
                report.issues.append(
                    f"{out_of_range.sum()} values in '{col}' outside [0,100]; clipped"
                )
                report.corrected_cells += int(out_of_range.sum())
                numeric = numeric.clip(lower=config.PROGRESS_MIN, upper=config.PROGRESS_MAX)
            df[col] = numeric

    # --- Count-like columns must be non-negative integers -----------------
    for col in ["number_of_payments", "inspection_count", "issues_reported", "issues_resolved", "bid_count"]:
        if col in df.columns:
            numeric = pd.to_numeric(df[col], errors="coerce")
            negative = numeric < 0
            if negative.any():
                report.issues.append(f"{negative.sum()} negative values in '{col}' clipped to NaN")
                report.corrected_cells += int(negative.sum())
                numeric = numeric.mask(negative)
            df[col] = numeric

    # --- issues_resolved should not exceed issues_reported -----------------
    if {"issues_reported", "issues_resolved"}.issubset(df.columns):
        over = df["issues_resolved"] > df["issues_reported"]
        over = over.fillna(False)
        if over.any():
            report.issues.append(
                f"{over.sum()} rows had issues_resolved > issues_reported; capped to issues_reported"
            )
            report.corrected_cells += int(over.sum())
            df.loc[over, "issues_resolved"] = df.loc[over, "issues_reported"]

    # --- Replace inf with NaN everywhere (defensive) -----------------------
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    inf_mask = np.isinf(df[numeric_cols]).any(axis=1)
    if inf_mask.any():
        report.issues.append(f"{inf_mask.sum()} rows contained infinite values; replaced with NaN")
        report.corrected_cells += int(inf_mask.sum())
        df[numeric_cols] = df[numeric_cols].replace([np.inf, -np.inf], np.nan)

    # --- Drop rows missing an essential identifier or cost basis ------------
    essential = ["project_id", "estimated_cost", "actual_cost"]
    missing_essential = df[essential].isna().any(axis=1)
    if missing_essential.any():
        report.issues.append(
            f"Dropped {missing_essential.sum()} rows missing essential fields {essential}"
        )
        report.dropped_rows += int(missing_essential.sum())
        df = df.loc[~missing_essential].copy()

    report.log_summary()
    return df.reset_index(drop=True), report
