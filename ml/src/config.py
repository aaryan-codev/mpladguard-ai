"""
Central configuration for the MPLADGuard-AI ML pipeline.

Keep all tunable constants here so training/inference behavior can be
changed without touching pipeline logic.
"""
from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ML_ROOT = Path(__file__).resolve().parent.parent  # ml/
DATA_DIR = ML_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
SAMPLE_DATA_DIR = DATA_DIR / "sample"
MODELS_DIR = ML_ROOT / "models"

SAMPLE_DATASET_PATH = SAMPLE_DATA_DIR / "sample_projects.csv"

MODELS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Model versioning
# ---------------------------------------------------------------------------
MODEL_NAME = "mpladguard-isolation-forest"
MODEL_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Category-specific model training
# ---------------------------------------------------------------------------
# Minimum number of samples a project_type/work_category must have before a
# dedicated model is trained for it. Categories below this threshold fall
# back to the "default" (global) model at inference time.
MIN_CATEGORY_SAMPLES = 30

DEFAULT_MODEL_KEY = "default"

# ---------------------------------------------------------------------------
# Isolation Forest hyperparameters
# ---------------------------------------------------------------------------
ISOLATION_FOREST_PARAMS = {
    "n_estimators": 200,
    "max_samples": "auto",
    "contamination": 0.08,  # assumed proportion of anomalous projects
    "random_state": 42,
    "n_jobs": -1,
}

# ---------------------------------------------------------------------------
# Risk score thresholds (0-100 scale, configurable)
# ---------------------------------------------------------------------------
RISK_LOW_MAX = 30       # 0-30   -> LOW
RISK_MEDIUM_MAX = 60    # 31-60  -> MEDIUM
                        # 61-100 -> HIGH

RISK_LEVELS = ("LOW", "MEDIUM", "HIGH")

# ---------------------------------------------------------------------------
# Engineered feature list (order matters - must match training/inference)
# ---------------------------------------------------------------------------
ENGINEERED_FEATURES = [
    "cost_deviation",
    "fund_utilization_ratio",
    "financial_physical_progress_gap",
    "delay_ratio",
    "inspection_gap_days",
    "contract_estimate_ratio",
    "cost_per_beneficiary",
    "tender_estimate_ratio",
    "bid_competition_indicator",
    "unresolved_issue_ratio",
]

# Human-readable descriptions used by the explainability layer.
FEATURE_DESCRIPTIONS = {
    "cost_deviation": "Actual cost vs. estimated cost deviation",
    "fund_utilization_ratio": "Utilized funds relative to released funds",
    "financial_physical_progress_gap": "Gap between financial and physical progress",
    "delay_ratio": "Actual duration relative to planned duration",
    "inspection_gap_days": "Days since the project was last inspected",
    "contract_estimate_ratio": "Contract value relative to estimated cost",
    "cost_per_beneficiary": "Actual cost per estimated beneficiary",
    "tender_estimate_ratio": "Winning bid relative to estimated tender value",
    "bid_competition_indicator": "Level of competition in the tender process",
    "unresolved_issue_ratio": "Proportion of reported inspection issues left unresolved",
}

# Direction in which a HIGH value of a feature is considered "risky".
# 1 -> higher is riskier, -1 -> lower is riskier, 0 -> deviation from 0 is riskier
FEATURE_RISK_DIRECTION = {
    "cost_deviation": 0,
    "fund_utilization_ratio": 1,
    "financial_physical_progress_gap": 0,
    "delay_ratio": 1,
    "inspection_gap_days": 1,
    "contract_estimate_ratio": 0,
    "cost_per_beneficiary": 1,
    "tender_estimate_ratio": 0,
    "bid_competition_indicator": -1,
    "unresolved_issue_ratio": 1,
}

# ---------------------------------------------------------------------------
# Validation bounds
# ---------------------------------------------------------------------------
PROGRESS_MIN, PROGRESS_MAX = 0.0, 100.0

# ---------------------------------------------------------------------------
# Dataset provenance
# ---------------------------------------------------------------------------
DATASET_TYPES = ("real", "synthetic")
DEFAULT_DATASET_TYPE = os.environ.get("MPLADGUARD_DATASET_TYPE", "synthetic")
