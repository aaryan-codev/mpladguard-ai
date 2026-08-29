from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from ..schemas.risk import RiskAnalyzeRequest, RiskAnalyzeResponse
from ..services import project_service, risk_service
from ..services.ml_service import MLModelUnavailableError, MLServiceError
from ..services.road_adapter import to_ml_payload

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/risk", tags=["risk"])


@router.post("/analyze", response_model=RiskAnalyzeResponse)
def analyze_risk(payload: RiskAnalyzeRequest) -> RiskAnalyzeResponse:
    try:
        ml_payload = to_ml_payload(payload.model_dump())
        assessment = risk_service.analyze(ml_payload)
    except MLModelUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"No trained road model available yet. Train one first: "
            f"python -m ml.src.road.train ({exc})",
        )
    except MLServiceError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return assessment.to_dict()


@router.get("/{project_id}", response_model=RiskAnalyzeResponse)
def get_risk(project_id: str) -> RiskAnalyzeResponse:
    """
    Returns the most recently computed risk assessment for a project.
    If none has been cached yet, computes it on demand (project must
    already exist via GET /api/projects/{project_id}).
    """
    try:
        assessment = risk_service.get_cached_risk(project_id)
    except risk_service.RiskNotFoundError:
        try:
            assessment = risk_service.analyze_by_project_id(project_id)
        except project_service.ProjectNotFoundError:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
        except MLModelUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        except MLServiceError as exc:
            raise HTTPException(status_code=500, detail=str(exc))
    return assessment.to_dict()
