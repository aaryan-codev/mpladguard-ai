import pandas as pd
import pytest

from ml.src.validation import validate_and_clean


def _base_row(**overrides):
    row = {
        "project_id": "P1",
        "estimated_cost": 1000000,
        "actual_cost": 1100000,
        "physical_progress": 50,
        "financial_progress": 55,
        "issues_reported": 2,
        "issues_resolved": 1,
        "number_of_payments": 3,
        "inspection_count": 1,
        "bid_count": 2,
        "work_order_date": "2023-01-01",
        "actual_completion_date": "2023-06-01",
    }
    row.update(overrides)
    return row


def test_drops_duplicate_project_ids():
    df = pd.DataFrame([_base_row(project_id="A"), _base_row(project_id="A")])
    cleaned, report = validate_and_clean(df)
    assert len(cleaned) == 1
    assert report.dropped_rows == 1


def test_clips_out_of_range_percentages():
    df = pd.DataFrame([_base_row(physical_progress=150), _base_row(project_id="P2", physical_progress=-10)])
    cleaned, report = validate_and_clean(df)
    assert cleaned.loc[0, "physical_progress"] == 100
    assert cleaned.loc[1, "physical_progress"] == 0
    assert report.corrected_cells >= 2


def test_negative_financial_values_become_nan():
    df = pd.DataFrame([_base_row(estimated_cost=-500)])
    cleaned, report = validate_and_clean(df)
    # essential-field drop rule removes rows missing estimated_cost after nan-ing
    assert len(cleaned) == 0
    assert report.dropped_rows == 1


def test_issues_resolved_capped_to_issues_reported():
    df = pd.DataFrame([_base_row(issues_reported=1, issues_resolved=5)])
    cleaned, _ = validate_and_clean(df)
    assert cleaned.loc[0, "issues_resolved"] == 1


def test_invalid_date_ordering_corrected():
    df = pd.DataFrame(
        [_base_row(work_order_date="2023-06-01", actual_completion_date="2023-01-01")]
    )
    cleaned, report = validate_and_clean(df)
    assert pd.isna(cleaned.loc[0, "actual_completion_date"])


def test_drops_rows_missing_essential_fields():
    df = pd.DataFrame([_base_row(project_id=None)])
    cleaned, report = validate_and_clean(df)
    assert len(cleaned) == 0
    assert report.dropped_rows == 1


