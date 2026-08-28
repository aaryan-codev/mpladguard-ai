"""
Dataset loading utilities.

Responsible ONLY for reading CSV data into a DataFrame and attaching
provenance metadata (real vs synthetic). Validation and cleaning happen
in validation.py / preprocessing.py.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pandas as pd

from . import config

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = [
    "project_id",
    "project_name",
    "project_type",
    "work_category",
    "state",
    "district",
    "constituency",
    "estimated_cost",
    "sanctioned_amount",
    "released_amount",
    "utilized_amount",
    "actual_cost",
    "number_of_payments",
    "sanction_date",
    "work_order_date",
    "planned_completion_date",
    "actual_completion_date",
    "physical_progress",
    "financial_progress",
    "work_status",
    "inspection_count",
    "last_inspection_date",
    "issues_reported",
    "issues_resolved",
    "implementing_agency",
    "agency_type",
    "contractor_id",
    "contractor_name",
    "contract_value",
    "tender_id",
    "estimated_tender_value",
    "bid_count",
    "winning_bid",
    "second_lowest_bid",
    "procurement_method",
    "estimated_beneficiaries",
    "population_served",
]

# Columns that are optional / nice-to-have but not required for training.
OPTIONAL_COLUMNS = ["location", "latitude", "longitude", "delay_days", "dataset_type"]


class DatasetLoadError(Exception):
    """Raised when a dataset file cannot be loaded or is structurally invalid."""


def load_csv(path: Path | str, dataset_type: Optional[str] = None) -> pd.DataFrame:
    """
    Load a project dataset CSV into a DataFrame.

    Parameters
    ----------
    path: Path to the CSV file.
    dataset_type: "real" or "synthetic". If the CSV already has a
        `dataset_type` column, per-row values take precedence; this
        parameter is only used to FILL missing values, and defaults to
        config.DEFAULT_DATASET_TYPE if not provided at all.

    Raises
    ------
    DatasetLoadError if the file is missing, empty, or missing required columns.
    """
    path = Path(path)
    if not path.exists():
        raise DatasetLoadError(f"Dataset file not found: {path}")

    try:
        df = pd.read_csv(path)
    except Exception as exc:  # malformed CSV
        raise DatasetLoadError(f"Failed to parse CSV '{path}': {exc}") from exc

    if df.empty:
        raise DatasetLoadError(f"Dataset file '{path}' is empty.")

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise DatasetLoadError(
            f"Dataset '{path}' is missing required columns: {missing}"
        )

    if "dataset_type" not in df.columns:
        df["dataset_type"] = dataset_type or config.DEFAULT_DATASET_TYPE
    else:
        df["dataset_type"] = df["dataset_type"].fillna(
            dataset_type or config.DEFAULT_DATASET_TYPE
        )

    unknown_types = set(df["dataset_type"].unique()) - set(config.DATASET_TYPES)
    if unknown_types:
        logger.warning(
            "Dataset contains unrecognized dataset_type values %s; "
            "expected one of %s. Leaving as-is.",
            unknown_types,
            config.DATASET_TYPES,
        )

    logger.info(
        "Loaded dataset '%s' with %d rows, %d columns (dataset_type breakdown: %s)",
        path,
        len(df),
        len(df.columns),
        df["dataset_type"].value_counts().to_dict(),
    )
    return df


def load_sample_dataset() -> pd.DataFrame:
    """Convenience loader for the bundled synthetic/demo dataset."""
    return load_csv(config.SAMPLE_DATASET_PATH, dataset_type="synthetic")


def load_all_raw_datasets() -> pd.DataFrame:
    """
    Load and concatenate every CSV found in ml/data/raw/.

    This supports the "accumulated dataset" growth strategy: new batches
    of verified project data can simply be dropped into ml/data/raw/ and
    the next training run will use all of them together.
    """
    raw_files = sorted(config.RAW_DATA_DIR.glob("*.csv"))
    if not raw_files:
        raise DatasetLoadError(
            f"No CSV files found in {config.RAW_DATA_DIR}. "
            "Add project data batches there before training on real data."
        )

    frames = [load_csv(f) for f in raw_files]
    combined = pd.concat(frames, ignore_index=True)

    before = len(combined)
    combined = combined.drop_duplicates(subset=["project_id"], keep="last")
    after = len(combined)
    if before != after:
        logger.warning(
            "Dropped %d duplicate project_id rows when combining raw datasets.",
            before - after,
        )

    logger.info(
        "Combined %d raw dataset file(s) into %d unique project rows.",
        len(raw_files),
        after,
    )
    return combined
