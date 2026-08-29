"""
Training entry point for the road-domain model.

Usage:
    python -m ml.src.road.train
    python -m ml.src.road.train --data ml/data/raw/mplads_road_projects_synthetic.csv
    python -m ml.src.road.train --data f1.csv --data f2.csv   # combine multiple batches

Writes into the SAME ml/models/registry.json used by the generic
pipeline, under the "road" key, so ml/src/predict.py can find and load
it without any change to the backend/API layer. The metadata written
includes "domain": "road" so predict.py knows to route this category
through the road-specific validation/feature-engineering/explain
functions instead of the generic ones.
"""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest

from .. import config as generic_config
from ..explain import compute_feature_reference
from ..preprocessing import build_preprocessor
from ..scoring import compute_score_reference
from . import config
from .feature_engineering import engineer_features, get_feature_matrix
from .validation import validate_and_clean

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ml.road.train")


def _load_datasets(paths: list[str]) -> pd.DataFrame:
    frames = [pd.read_csv(p) for p in paths]
    df = pd.concat(frames, ignore_index=True)
    logger.info("Loaded %d road project rows from %d file(s): %s", len(df), len(paths), paths)
    return df


def train(data_paths: list[str]) -> dict:
    logger.info("=== MPLADGuard-AI ROAD model training starting ===")

    df = _load_datasets(data_paths)

    # ground_truth_anomaly is evaluation-only: split it off immediately so
    # it can never leak into feature engineering or the model itself.
    ground_truth = df["ground_truth_anomaly"].copy() if "ground_truth_anomaly" in df.columns else None
    df = df.drop(columns=["ground_truth_anomaly"], errors="ignore")

    df, report = validate_and_clean(df)
    if ground_truth is not None:
        ground_truth = ground_truth.loc[df.index] if len(ground_truth) == report.total_rows else None
    if len(df) == 0:
        raise RuntimeError("No valid road rows remained after validation. Aborting training.")

    df = engineer_features(df)
    X = get_feature_matrix(df)

    preprocessor = build_preprocessor()
    X_transformed = preprocessor.fit_transform(X)

    model = IsolationForest(**config.ISOLATION_FOREST_PARAMS)
    model.fit(X_transformed)

    raw_scores = model.score_samples(X_transformed)
    predictions = model.predict(X_transformed)  # -1 = anomaly, 1 = normal
    n_anomalies = int((predictions == -1).sum())

    pipeline = {"preprocessor": preprocessor, "model": model}

    score_reference = compute_score_reference(raw_scores)
    feature_reference = compute_feature_reference(X, engineered_features=config.ENGINEERED_FEATURES)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    model_filename = f"road_model_{timestamp}.joblib"
    meta_filename = f"road_model_{timestamp}.meta.json"

    models_dir = generic_config.MODELS_DIR
    model_path = models_dir / model_filename
    meta_path = models_dir / meta_filename

    joblib.dump(pipeline, model_path)

    metadata = {
        "model_name": "mpladguard-road-isolation-forest",
        "version": config.MODEL_VERSION,
        "domain": config.DOMAIN_NAME,
        "category": "road",
        "trained_at": timestamp,
        "training_samples": len(X),
        "features": config.ENGINEERED_FEATURES,
        "feature_descriptions": config.FEATURE_DESCRIPTIONS,
        "contamination": config.ISOLATION_FOREST_PARAMS["contamination"],
        "anomalies_detected": n_anomalies,
        "anomaly_pct": round(100.0 * n_anomalies / len(X), 2) if len(X) else 0.0,
        "score_reference": score_reference,
        "feature_reference": feature_reference,
        "dataset_type_breakdown": {"synthetic": len(X)},
        "model_file": model_filename,
        "source_files": data_paths,
    }
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    registry_path = models_dir / "registry.json"
    registry = {}
    if registry_path.exists():
        with open(registry_path) as f:
            registry = json.load(f)
    registry["road"] = {
        "model_file": model_filename,
        "meta_file": meta_filename,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(registry_path, "w") as f:
        json.dump(registry, f, indent=2)

    logger.info("=== Road model training complete ===")
    logger.info("Training samples: %d", len(X))
    logger.info("Anomalies flagged by model: %d (%.2f%%)", n_anomalies, metadata["anomaly_pct"])
    logger.info("Model saved to: %s", model_path)

    result = {
        "training_samples": len(X),
        "anomalies_detected": n_anomalies,
        "anomaly_pct": metadata["anomaly_pct"],
        "model_file": str(model_path),
        "meta_file": str(meta_path),
    }

    if ground_truth is not None:
        result["model_predictions_for_eval"] = predictions.tolist()
        result["ground_truth_for_eval"] = ground_truth.tolist()

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the MPLADGuard-AI road anomaly detection model.")
    parser.add_argument(
        "--data",
        type=str,
        action="append",
        default=None,
        help="Path to a road dataset CSV. Repeat to combine multiple batches.",
    )
    args = parser.parse_args()

    data_paths = args.data or ["ml/data/raw/mplads_road_projects_synthetic.csv"]
    result = train(data_paths)
    print(json.dumps({k: v for k, v in result.items() if "eval" not in k}, indent=2))


if __name__ == "__main__":
    main()
