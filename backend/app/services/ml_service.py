"""
ML service.

This is the ONLY place in the backend that imports the `ml` package.
It exists so:
  - the ml/ package stays completely independent of FastAPI/DB code
    (per architecture: Database -> Backend -> ML Service -> Prediction)
  - ML import errors / missing-model errors are translated into clean
    HTTP-friendly exceptions instead of leaking stack traces to clients
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

from ..core.config import REPO_ROOT

# Make the sibling `ml` package importable regardless of CWD.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

logger = logging.getLogger(__name__)

try:
    from ml.src.predict import (  # noqa: E402
        ModelNotFoundError,
        PredictionError,
        RiskAssessment,
        clear_model_cache,
        predict_risk,
    )
except ImportError as exc:  # pragma: no cover
    logger.critical("Failed to import ml package: %s", exc)
    raise


class MLServiceError(Exception):
    """Generic ML-service-level error surfaced to the API layer."""


class MLModelUnavailableError(MLServiceError):
    """No trained model is available yet."""


def analyze_project_risk(project: dict[str, Any]) -> RiskAssessment:
    """
    Run risk analysis for a single project dict. Translates ml-layer
    exceptions into backend-service-level exceptions.
    """
    try:
        return predict_risk(project)
    except ModelNotFoundError as exc:
        logger.error("No trained model available: %s", exc)
        raise MLModelUnavailableError(str(exc)) from exc
    except PredictionError as exc:
        logger.error("Prediction failed for project '%s': %s", project.get("project_id"), exc)
        raise MLServiceError(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 - defensive: never leak raw stack traces
        logger.exception("Unexpected ML error for project '%s'", project.get("project_id"))
        raise MLServiceError("Unexpected error during risk analysis.") from exc


def refresh_models() -> None:
    """Call after retraining so newly trained models are picked up without a restart."""
    clear_model_cache()
