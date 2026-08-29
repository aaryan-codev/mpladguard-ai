"""
Risk service.

Thin orchestration layer between the API routes and ml_service. Also
keeps a small in-memory cache of the most recent risk assessment per
project so GET /api/risk/{project_id} can return a previously computed
result without recomputation (a real deployment would persist this to
the database instead).
"""
from __future__ import annotations

import logging
import threading
from typing import Any

from ..services import ml_service, project_service
from ..services.ml_service import MLModelUnavailableError, MLServiceError, RiskAssessment

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_risk_cache: dict[str, RiskAssessment] = {}


class RiskNotFoundError(Exception):
    pass


def analyze(project: dict[str, Any]) -> RiskAssessment:
    assessment = ml_service.analyze_project_risk(project)
    with _lock:
        _risk_cache[assessment.project_id] = assessment
    return assessment


def analyze_by_project_id(project_id: str) -> RiskAssessment:
    """Look up a known project's raw ML fields and run risk analysis on it."""
    ml_payload = project_service.get_ml_payload(project_id)
    return analyze(ml_payload)


def get_cached_risk(project_id: str) -> RiskAssessment:
    with _lock:
        result = _risk_cache.get(project_id)
    if result is None:
        raise RiskNotFoundError(
            f"No risk assessment cached for '{project_id}'. "
            "POST /api/risk/analyze first, or GET /api/risk/{project_id} "
            "will compute it on demand if the project is known."
        )
    return result
