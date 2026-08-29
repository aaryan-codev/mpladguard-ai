"""
Config for the road-domain anomaly detection model.

Mirrors the structure of ml/src/config.py (generic pipeline) but with
values appropriate to the road-specific dataset and feature set.
"""
from __future__ import annotations

DOMAIN_NAME = "road"
MODEL_VERSION = "road_v1"

# The MPLADGuard-AI road dataset the team profiled: 500 rows, 10% flagged
# ground_truth_anomaly (evaluation-only, never a training feature).
ISOLATION_FOREST_PARAMS = {
    "n_estimators": 200,
    "max_samples": "auto",
    "contamination": 0.10,
    "random_state": 42,
    "n_jobs": -1,
}

RISK_LOW_MAX = 30
RISK_MEDIUM_MAX = 60

# Raw columns required to be present (post-validation) before feature
# engineering can run. ground_truth_anomaly is intentionally excluded:
# it is loaded for evaluation only and must never reach the model.
REQUIRED_COLUMNS = [
    "project_id",
    "state",
    "district",
    "parliamentary_constituency",
    "implementing_agency",
    "road_type",
    "road_length_km",
    "estimated_cost_lakh",
    "actual_expenditure_lakh",
    "planned_duration_days",
    "actual_duration_days",
    "project_start_date",
    "project_status",
]

OPTIONAL_COLUMNS = ["project_completion_date", "latitude", "longitude", "ground_truth_anomaly"]

VALID_PROJECT_STATUSES = ("Completed", "Ongoing", "Delayed")

# Engineered feature list (order matters -- must match training/inference).
ENGINEERED_FEATURES = [
    "cost_deviation",
    "cost_per_km_estimated",
    "cost_per_km_actual",
    "cost_per_km_ratio",
    "delay_ratio",
    "delay_days_normalized",
]

FEATURE_DESCRIPTIONS = {
    "cost_deviation": "Actual expenditure vs. estimated cost deviation",
    "cost_per_km_estimated": "Estimated cost per kilometre of road",
    "cost_per_km_actual": "Actual expenditure per kilometre of road",
    "cost_per_km_ratio": "Actual vs. estimated cost-per-km ratio",
    "delay_ratio": "Actual duration relative to planned duration",
    "delay_days_normalized": "Delay in days, normalized by planned duration",
}

# 1 -> higher is riskier, -1 -> lower is riskier, 0 -> deviation from 0 is riskier
FEATURE_RISK_DIRECTION = {
    "cost_deviation": 0,
    "cost_per_km_estimated": 0,
    "cost_per_km_actual": 1,
    "cost_per_km_ratio": 1,
    "delay_ratio": 1,
    "delay_days_normalized": 1,
}
