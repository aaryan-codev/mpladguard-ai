"""
End-to-end integration test: train on the bundled sample dataset in a
temporary models directory, then run a prediction against it.

This is the closest thing to "does the whole pipeline actually work"
without touching the real ml/models/ directory used by the running app.
"""
import importlib
import json

import pandas as pd
import pytest


@pytest.fixture()
def isolated_models_dir(tmp_path, monkeypatch):
    """Redirect config.MODELS_DIR to a scratch directory for this test only."""
    from ml.src import config

    scratch = tmp_path / "models"
    scratch.mkdir()
    monkeypatch.setattr(config, "MODELS_DIR", scratch)

    # train.py and predict.py import config functions directly; reload them
    # so they pick up the patched MODELS_DIR via the shared config module object.
    yield scratch


def test_train_then_predict_end_to_end(isolated_models_dir):
    from ml.src import predict, train
    from ml.src.data_loader import load_sample_dataset

    summary = train.train()  # trains on bundled sample dataset
    assert "default" in summary["categories"]
    assert (isolated_models_dir / "registry.json").exists()

    predict.clear_model_cache()

    df = load_sample_dataset()
    sample_project = df.iloc[0].to_dict()

    result = predict.predict_risk(sample_project)
    assert result.project_id == sample_project["project_id"]
    assert 0 <= result.risk_score <= 100
    assert result.risk_level in ("LOW", "MEDIUM", "HIGH")
    assert isinstance(result.anomaly, bool)
    assert isinstance(result.risk_factors, list)


def test_predict_without_trained_model_raises(tmp_path, monkeypatch):
    from ml.src import config, predict

    empty_dir = tmp_path / "empty_models"
    empty_dir.mkdir()
    monkeypatch.setattr(config, "MODELS_DIR", empty_dir)
    predict.clear_model_cache()

    with pytest.raises(predict.ModelNotFoundError):
        predict.predict_risk({"project_id": "X", "estimated_cost": 100, "actual_cost": 100})
