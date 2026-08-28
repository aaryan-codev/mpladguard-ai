import numpy as np
import pandas as pd

from ml.src import config
from ml.src.feature_engineering import engineer_features, get_feature_matrix


def _project_row(**overrides):
    row = {
        "project_id": "P1",
        "estimated_cost": 1000000.0,
        "actual_cost": 1200000.0,
        "utilized_amount": 800000.0,
        "released_amount": 1000000.0,
        "financial_progress": 60.0,
        "physical_progress": 50.0,
        "work_order_date": "2023-01-01",
        "planned_completion_date": "2023-07-01",
        "actual_completion_date": "2023-08-01",
        "last_inspection_date": "2023-06-01",
        "contract_value": 950000.0,
        "estimated_beneficiaries": 1000,
        "winning_bid": 900000.0,
        "estimated_tender_value": 1000000.0,
        "bid_count": 3,
        "issues_reported": 4,
        "issues_resolved": 2,
    }
    row.update(overrides)
    return row


def test_engineer_features_produces_all_columns():
    df = pd.DataFrame([_project_row()])
    result = engineer_features(df, reference_date=pd.Timestamp("2023-09-01"))
    for feature in config.ENGINEERED_FEATURES:
        assert feature in result.columns


def test_cost_deviation_computed_correctly():
    df = pd.DataFrame([_project_row(estimated_cost=1000000.0, actual_cost=1200000.0)])
    result = engineer_features(df, reference_date=pd.Timestamp("2023-09-01"))
    assert abs(result.loc[0, "cost_deviation"] - 0.2) < 1e-6


def test_zero_denominator_yields_nan_not_inf():
    df = pd.DataFrame([_project_row(estimated_beneficiaries=0)])
    result = engineer_features(df, reference_date=pd.Timestamp("2023-09-01"))
    assert not np.isinf(result.loc[0, "cost_per_beneficiary"])
    assert pd.isna(result.loc[0, "cost_per_beneficiary"])


def test_unresolved_issue_ratio_zero_when_no_issues_reported():
    df = pd.DataFrame([_project_row(issues_reported=0, issues_resolved=0)])
    result = engineer_features(df, reference_date=pd.Timestamp("2023-09-01"))
    assert result.loc[0, "unresolved_issue_ratio"] == 0.0


def test_never_inspected_gets_large_but_finite_gap():
    df = pd.DataFrame([_project_row(last_inspection_date=None)])
    result = engineer_features(df, reference_date=pd.Timestamp("2023-09-01"))
    assert np.isfinite(result.loc[0, "inspection_gap_days"])
    assert result.loc[0, "inspection_gap_days"] >= 365


def test_get_feature_matrix_returns_canonical_columns():
    df = pd.DataFrame([_project_row()])
    result = engineer_features(df, reference_date=pd.Timestamp("2023-09-01"))
    matrix = get_feature_matrix(result)
    assert list(matrix.columns) == config.ENGINEERED_FEATURES
