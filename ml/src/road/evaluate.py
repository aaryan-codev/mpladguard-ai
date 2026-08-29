"""
Evaluates the trained road Isolation Forest against ground_truth_anomaly.

ground_truth_anomaly is NEVER used as a training feature (see train.py --
it is dropped from the DataFrame before validation/feature engineering
even run). It is used here, after training, purely to measure how well
the *unsupervised* model's anomaly flags line up with the known synthetic
labels. This is standard practice for evaluating unsupervised anomaly
detectors when labels happen to be available for validation, and is
exactly what SIH judges will want to see a real number for.

Usage:
    python -m ml.src.road.evaluate
    python -m ml.src.road.evaluate --data ml/data/raw/mplads_road_projects_synthetic.csv
"""
from __future__ import annotations

import argparse
import json
import logging

import joblib
import pandas as pd
from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score

from .. import config as generic_config
from .feature_engineering import engineer_features, get_feature_matrix
from .validation import validate_and_clean

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ml.road.evaluate")


def evaluate(data_path: str, model_file: str | None = None) -> dict:
    with open(generic_config.MODELS_DIR / "registry.json") as f:
        registry = json.load(f)

    if "road" not in registry:
        raise RuntimeError("No road model found in registry.json. Run `python -m ml.src.road.train` first.")

    model_file = model_file or registry["road"]["model_file"]
    pipeline = joblib.load(generic_config.MODELS_DIR / model_file)

    df = pd.read_csv(data_path)
    if "ground_truth_anomaly" not in df.columns:
        raise ValueError("Dataset has no ground_truth_anomaly column; cannot evaluate.")

    ground_truth = df["ground_truth_anomaly"].copy()
    df = df.drop(columns=["ground_truth_anomaly"])

    df, report = validate_and_clean(df)
    # validate_and_clean can drop rows (duplicates / missing essentials);
    # keep ground_truth aligned to what actually got scored.
    ground_truth = ground_truth.loc[df.index]

    df = engineer_features(df)
    X = get_feature_matrix(df)
    X_transformed = pipeline["preprocessor"].transform(X)

    predictions = pipeline["model"].predict(X_transformed)  # -1 = anomaly, 1 = normal
    y_pred = (predictions == -1).astype(int)
    y_true = ground_truth.astype(int).to_numpy()

    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)

    result = {
        "n_evaluated": int(len(y_true)),
        "n_ground_truth_anomalies": int(y_true.sum()),
        "n_model_flagged_anomalies": int(y_pred.sum()),
        "confusion_matrix": {
            "true_negative": int(tn),
            "false_positive": int(fp),
            "false_negative": int(fn),
            "true_positive": int(tp),
        },
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1_score": round(float(f1), 4),
    }

    logger.info("Evaluation on %d rows:", result["n_evaluated"])
    logger.info(
        "  Ground truth anomalies: %d | Model flagged: %d",
        result["n_ground_truth_anomalies"],
        result["n_model_flagged_anomalies"],
    )
    logger.info("  Precision: %.4f  Recall: %.4f  F1: %.4f", precision, recall, f1)
    logger.info("  Confusion matrix: %s", result["confusion_matrix"])

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the road model against ground_truth_anomaly.")
    parser.add_argument("--data", type=str, default="ml/data/raw/mplads_road_projects_synthetic.csv")
    args = parser.parse_args()
    result = evaluate(args.data)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
