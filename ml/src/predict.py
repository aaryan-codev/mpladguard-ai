"""
Inference / prediction.

Given a single project's raw data (dict or one-row DataFrame), this module:
  1. runs it through the SAME validation + feature engineering used in training
  2. selects the appropriate trained model (category-specific if available,
     else the default/global model) via the registry
  3. runs the saved preprocessing+IsolationForest pipeline
  4. normalizes the raw score into a 0-100 risk score + LOW/MEDIUM/HIGH level
  5. generates explainable risk factors

This module deliberately reuses validation.py / feature_engineering.py
rather than reimplementing any preprocessing logic.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from . import config
from .explain import generate_risk_factors
from .feature_engineering import engineer_features, get_feature_matrix
from .scoring import normalize_to_risk_score, risk_level_from_score
from .train import _category_key  # reuse the exact same normalization used at training time
from .validation import validate_and_clean

logger = logging.getLogger(__name__)


class ModelNotFoundError(Exception):
    """Raised when no trained model (not even the default) is available."""


class PredictionError(Exception):
    """Raised for any other prediction-time failure (bad input, corrupted model, etc.)."""


@dataclass
class RiskAssessment:
    project_id: str
    risk_score: float
    risk_level: str
    anomaly: bool
    risk_factors: list[dict] = field(default_factory=list)
    model_version: str = config.MODEL_VERSION
    model_category: str = config.DEFAULT_MODEL_KEY
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "risk_score": round(self.risk_score, 1),
            "risk_level": self.risk_level,
            "anomaly": self.anomaly,
            "risk_factors": self.risk_factors,
            "model_version": self.model_version,
            "model_category": self.model_category,
            "warnings": self.warnings,
        }


def _load_registry() -> dict:
    registry_path = config.MODELS_DIR / "registry.json"
    if not registry_path.exists():
        raise ModelNotFoundError(
            f"No trained models found ({registry_path} missing). Run training first: "
            "python -m ml.src.train"
        )
    with open(registry_path) as f:
        return json.load(f)


@lru_cache(maxsize=32)
def _load_model_bundle(category_key: str) -> tuple[dict, dict]:
    """Load (pipeline, metadata) for a category, cached in-process."""
    registry = _load_registry()
    entry = registry.get(category_key)
    if entry is None:
        raise ModelNotFoundError(f"No model registered for category '{category_key}'.")

    model_path = config.MODELS_DIR / entry["model_file"]
    meta_path = config.MODELS_DIR / entry["meta_file"]

    if not model_path.exists() or not meta_path.exists():
        raise ModelNotFoundError(
            f"Registry points to missing model files for '{category_key}' "
            f"({model_path}, {meta_path})."
        )

    try:
        pipeline = joblib.load(model_path)
    except Exception as exc:  # noqa: BLE001
        raise PredictionError(f"Failed to load model file '{model_path}': {exc}") from exc

    with open(meta_path) as f:
        metadata = json.load(f)

    return pipeline, metadata


def clear_model_cache() -> None:
    """Call after retraining so the API picks up the newest model without a restart."""
    _load_model_bundle.cache_clear()


def _resolve_category(project: dict) -> str:
    raw_category = project.get("work_category") or project.get("project_type") or ""
    key = _category_key(raw_category)
    registry = _load_registry()  # raises ModelNotFoundError early if nothing trained
    if key in registry:
        return key
    return config.DEFAULT_MODEL_KEY


def predict_risk(project: dict[str, Any]) -> RiskAssessment:
    """
    Run the full inference pipeline for a single project provided as a dict.

    Dispatches to domain-specific validation/feature-engineering/explain
    functions based on the "domain" flag stored in the resolved model's
    metadata (set by each domain's train.py). Projects whose model has no
    "domain" key (the original default/bridge/school models) go through
    the original generic pipeline unchanged.
    """
    if "project_id" not in project or not project["project_id"]:
        raise PredictionError("project_id is required for risk analysis.")

    # Fail fast if no model has been trained at all, before doing any
    # feature engineering work on (possibly incomplete) input data.
    _load_registry()

    category_key = _resolve_category(project)
    pipeline, metadata = _load_model_bundle(category_key)

    warnings: list[str] = []
    domain = metadata.get("domain")

    if domain == "road":
        from .road import config as road_config
        from .road.feature_engineering import engineer_features as road_engineer_features
        from .road.feature_engineering import get_feature_matrix as road_get_feature_matrix
        from .road.validation import validate_and_clean as road_validate_and_clean

        # ground_truth_anomaly must never reach feature engineering / the model.
        project = {k: v for k, v in project.items() if k != "ground_truth_anomaly"}

        df = pd.DataFrame([project])
        try:
            df, report = road_validate_and_clean(df)
        except KeyError as exc:
            raise PredictionError(f"Project data is missing required road fields: {exc}") from exc

        if len(df) == 0:
            raise PredictionError(
                "Project data failed road validation (missing essential fields such as "
                "project_id, estimated_cost_lakh, actual_expenditure_lakh, or road_length_km)."
            )
        if report.issues:
            warnings.extend(report.issues)

        try:
            df = road_engineer_features(df)
            X = road_get_feature_matrix(df)
        except KeyError as exc:
            raise PredictionError(f"Road project data is missing required fields: {exc}") from exc

        engineered_features = road_config.ENGINEERED_FEATURES
        feature_descriptions = road_config.FEATURE_DESCRIPTIONS
    else:
        df = pd.DataFrame([project])
        # Reuse the exact same validation used during training.
        try:
            df, report = validate_and_clean(df)
        except KeyError as exc:
            raise PredictionError(f"Project data is missing required fields: {exc}") from exc

        if len(df) == 0:
            raise PredictionError(
                "Project data failed validation (missing essential fields such as "
                "project_id, estimated_cost, or actual_cost)."
            )
        if report.issues:
            warnings.extend(report.issues)

        try:
            df = engineer_features(df)
            X = get_feature_matrix(df)
        except KeyError as exc:
            raise PredictionError(f"Project data is missing required fields: {exc}") from exc

        engineered_features = None  # use explain.py's generic config defaults
        feature_descriptions = None

    X_transformed = pipeline["preprocessor"].transform(X)

    raw_score = float(pipeline["model"].score_samples(X_transformed)[0])
    raw_prediction = int(pipeline["model"].predict(X_transformed)[0])  # -1 anomaly, 1 normal

    risk_score = normalize_to_risk_score(raw_score, metadata["score_reference"])
    risk_level = risk_level_from_score(risk_score)

    feature_values = X.iloc[0].to_dict()
    risk_factors = generate_risk_factors(
        feature_values,
        metadata["feature_reference"],
        engineered_features=engineered_features,
        feature_descriptions=feature_descriptions,
    )

    if metadata.get("dataset_type_breakdown", {}).get("real", 0) == 0:
        warnings.append(
            "This model was trained on synthetic/demo data only. Risk scores are "
            "illustrative, not based on verified real MPLADS data."
        )

    return RiskAssessment(
        project_id=str(project["project_id"]),
        risk_score=risk_score,
        risk_level=risk_level,
        anomaly=(raw_prediction == -1),
        risk_factors=risk_factors,
        model_version=metadata.get("version", config.MODEL_VERSION),
        model_category=category_key,
        warnings=warnings,
    )
