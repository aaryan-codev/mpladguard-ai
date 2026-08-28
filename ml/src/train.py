"""
Training entry point.

Usage:
    python -m ml.src.train                              # trains on bundled sample dataset
    python -m ml.src.train --data ml/data/raw/batch1.csv # trains on a specific CSV
    python -m ml.src.train --use-raw                     # trains on ALL files in ml/data/raw/ combined

Trains one Isolation Forest per project_type/work_category that has at
least config.MIN_CATEGORY_SAMPLES rows, plus one "default" model trained
on the full dataset for categories that don't meet the threshold.

Every run produces a NEW versioned model file per category (never
overwrites), and updates a registry.json that points at the latest
version for each category.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from . import config
from .data_loader import DatasetLoadError, load_all_raw_datasets, load_csv, load_sample_dataset
from .explain import compute_feature_reference
from .feature_engineering import engineer_features, get_feature_matrix
from .preprocessing import build_preprocessor
from .scoring import compute_score_reference
from .validation import validate_and_clean

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ml.train")


def _category_key(raw_category: str) -> str:
    """Normalize a category string into a filesystem-safe key."""
    return (
        str(raw_category).strip().lower().replace(" ", "_").replace("/", "_")
        or config.DEFAULT_MODEL_KEY
    )


def _train_single_model(feature_df: pd.DataFrame) -> dict:
    """Train one preprocessing+IsolationForest pipeline on a feature matrix."""
    X = get_feature_matrix(feature_df)

    preprocessor = build_preprocessor()
    X_transformed = preprocessor.fit_transform(X)

    model = IsolationForest(**config.ISOLATION_FOREST_PARAMS)
    model.fit(X_transformed)

    raw_scores = model.score_samples(X_transformed)
    predictions = model.predict(X_transformed)  # -1 = anomaly, 1 = normal
    n_anomalies = int((predictions == -1).sum())

    pipeline = {"preprocessor": preprocessor, "model": model}

    return {
        "pipeline": pipeline,
        "score_reference": compute_score_reference(raw_scores),
        "feature_reference": compute_feature_reference(X),
        "n_samples": len(X),
        "n_anomalies": n_anomalies,
        "anomaly_pct": round(100.0 * n_anomalies / len(X), 2) if len(X) else 0.0,
    }


def _save_model_bundle(category_key: str, result: dict, dataset_type_summary: dict) -> tuple[Path, Path]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    model_filename = f"{category_key}_model_{timestamp}.joblib"
    meta_filename = f"{category_key}_model_{timestamp}.meta.json"

    model_path = config.MODELS_DIR / model_filename
    meta_path = config.MODELS_DIR / meta_filename

    joblib.dump(result["pipeline"], model_path)

    metadata = {
        "model_name": config.MODEL_NAME,
        "version": config.MODEL_VERSION,
        "category": category_key,
        "trained_at": timestamp,
        "training_samples": result["n_samples"],
        "features": config.ENGINEERED_FEATURES,
        "contamination": config.ISOLATION_FOREST_PARAMS["contamination"],
        "anomalies_detected": result["n_anomalies"],
        "anomaly_pct": result["anomaly_pct"],
        "score_reference": result["score_reference"],
        "feature_reference": result["feature_reference"],
        "dataset_type_breakdown": dataset_type_summary,
        "model_file": model_filename,
    }
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    return model_path, meta_path


def _update_registry(category_key: str, model_path: Path, meta_path: Path) -> None:
    registry_path = config.MODELS_DIR / "registry.json"
    registry = {}
    if registry_path.exists():
        with open(registry_path) as f:
            registry = json.load(f)

    registry[category_key] = {
        "model_file": model_path.name,
        "meta_file": meta_path.name,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(registry_path, "w") as f:
        json.dump(registry, f, indent=2)


def train(data_path: str | None = None, use_raw: bool = False) -> dict:
    """
    Run the full training pipeline. Returns a summary dict (also printed).
    """
    logger.info("=== MPLADGuard-AI training pipeline starting ===")

    # 1. Load
    if use_raw:
        df = load_all_raw_datasets()
    elif data_path:
        df = load_csv(data_path)
    else:
        logger.info("No --data provided; training on bundled sample dataset.")
        df = load_sample_dataset()

    dataset_type_summary = df["dataset_type"].value_counts().to_dict()
    if dataset_type_summary.get("synthetic", 0) > 0 and dataset_type_summary.get("real", 0) == 0:
        logger.warning(
            "Training entirely on SYNTHETIC/DEMO data. Do not present this model's "
            "output as based on real MPLADS data."
        )

    # 2. Validate + clean
    df, report = validate_and_clean(df)
    if len(df) == 0:
        raise RuntimeError("No valid rows remained after validation. Aborting training.")

    # 3. Feature engineering
    df = engineer_features(df)

    # 4. Split into categories
    df["_category_key"] = df["work_category"].fillna(df["project_type"]).map(_category_key)
    category_counts = df["_category_key"].value_counts()

    trainable_categories = category_counts[category_counts >= config.MIN_CATEGORY_SAMPLES].index.tolist()
    skipped_categories = category_counts[category_counts < config.MIN_CATEGORY_SAMPLES].index.tolist()

    if skipped_categories:
        logger.info(
            "Categories below MIN_CATEGORY_SAMPLES=%d (%s) will rely on the default model: %s",
            config.MIN_CATEGORY_SAMPLES,
            config.MIN_CATEGORY_SAMPLES,
            skipped_categories,
        )

    summary = {"trained_at": datetime.now(timezone.utc).isoformat(), "categories": {}}

    # 5. Always train a default/global model on the FULL dataset.
    logger.info("Training default/global model on %d total samples...", len(df))
    default_result = _train_single_model(df)
    model_path, meta_path = _save_model_bundle(config.DEFAULT_MODEL_KEY, default_result, dataset_type_summary)
    _update_registry(config.DEFAULT_MODEL_KEY, model_path, meta_path)
    summary["categories"][config.DEFAULT_MODEL_KEY] = {
        "samples": default_result["n_samples"],
        "anomaly_pct": default_result["anomaly_pct"],
        "model_file": model_path.name,
    }
    logger.info(
        "Default model trained: %d samples, %.2f%% flagged anomalous.",
        default_result["n_samples"],
        default_result["anomaly_pct"],
    )

    # 6. Train category-specific models where there's enough data.
    for category_key in trainable_categories:
        cat_df = df[df["_category_key"] == category_key]
        logger.info("Training model for category '%s' on %d samples...", category_key, len(cat_df))
        cat_dataset_summary = cat_df["dataset_type"].value_counts().to_dict()
        result = _train_single_model(cat_df)
        model_path, meta_path = _save_model_bundle(category_key, result, cat_dataset_summary)
        _update_registry(category_key, model_path, meta_path)
        summary["categories"][category_key] = {
            "samples": result["n_samples"],
            "anomaly_pct": result["anomaly_pct"],
            "model_file": model_path.name,
        }
        logger.info(
            "Category '%s' model trained: %d samples, %.2f%% flagged anomalous.",
            category_key,
            result["n_samples"],
            result["anomaly_pct"],
        )

    logger.info("=== Training complete ===")
    logger.info("Model trained successfully.")
    logger.info("Total training samples: %d", len(df))
    logger.info("Engineered features: %d (%s)", len(config.ENGINEERED_FEATURES), config.ENGINEERED_FEATURES)
    logger.info(
        "Categories trained: %s (+ default)",
        trainable_categories if trainable_categories else "none",
    )
    logger.info("Models saved to: %s", config.MODELS_DIR)

    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Train MPLADGuard-AI anomaly detection models.")
    parser.add_argument("--data", type=str, default=None, help="Path to a specific CSV dataset.")
    parser.add_argument(
        "--use-raw",
        action="store_true",
        help="Train on ALL CSV files combined from ml/data/raw/ (accumulated dataset growth).",
    )
    args = parser.parse_args()

    try:
        train(data_path=args.data, use_raw=args.use_raw)
    except DatasetLoadError as exc:
        logger.error("Dataset error: %s", exc)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Training failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
