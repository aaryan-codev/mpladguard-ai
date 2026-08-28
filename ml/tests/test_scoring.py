import numpy as np

from ml.src.scoring import compute_score_reference, normalize_to_risk_score, risk_level_from_score


def test_compute_score_reference_basic_stats():
    scores = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
    ref = compute_score_reference(scores)
    assert ref["min"] == 0.1
    assert ref["max"] == 0.5
    assert round(ref["mean"], 2) == 0.3


def test_normalize_most_anomalous_score_is_high_risk():
    ref = {"min": 0.0, "max": 1.0}
    risk = normalize_to_risk_score(0.0, ref)  # worst score in training range
    assert risk == 100.0


def test_normalize_most_normal_score_is_low_risk():
    ref = {"min": 0.0, "max": 1.0}
    risk = normalize_to_risk_score(1.0, ref)  # best score in training range
    assert risk == 0.0


def test_normalize_clips_outside_training_range():
    ref = {"min": 0.2, "max": 0.8}
    assert normalize_to_risk_score(-5.0, ref) == 100.0
    assert normalize_to_risk_score(5.0, ref) == 0.0


def test_normalize_handles_degenerate_reference():
    ref = {"min": 0.5, "max": 0.5}
    assert normalize_to_risk_score(0.5, ref) == 50.0


def test_risk_level_thresholds():
    assert risk_level_from_score(0) == "LOW"
    assert risk_level_from_score(30) == "LOW"
    assert risk_level_from_score(31) == "MEDIUM"
    assert risk_level_from_score(60) == "MEDIUM"
    assert risk_level_from_score(61) == "HIGH"
    assert risk_level_from_score(100) == "HIGH"
