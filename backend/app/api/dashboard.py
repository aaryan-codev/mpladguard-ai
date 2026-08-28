from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from ..services import project_service, risk_service
from ..services.ml_service import MLModelUnavailableError, MLServiceError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _safe_float(value, default=0.0) -> float:
    try:
        f = float(value)
        return f if f == f else default  # filter NaN
    except (TypeError, ValueError):
        return default


@router.get("/summary")
def dashboard_summary():
    total, projects = project_service.list_projects(limit=10_000)

    total_sanctioned = sum(_safe_float(p.get("sanctioned_amount")) for p in projects)
    total_utilized = sum(_safe_float(p.get("utilized_amount")) for p in projects)
    completed = sum(1 for p in projects if str(p.get("work_status", "")).lower() == "completed")
    ongoing = sum(1 for p in projects if str(p.get("work_status", "")).lower() == "ongoing")
    delayed = sum(1 for p in projects if _safe_float(p.get("delay_days")) > 30)

    return {
        "total_projects": total,
        "total_sanctioned_amount": round(total_sanctioned, 2),
        "total_utilized_amount": round(total_utilized, 2),
        "completed_projects": completed,
        "ongoing_projects": ongoing,
        "delayed_projects": delayed,
    }


@router.get("/risk-distribution")
def risk_distribution():
    """
    Runs (or reuses cached) risk analysis across all known projects and
    returns a LOW/MEDIUM/HIGH count breakdown. Projects that fail
    validation/analysis are skipped and counted separately rather than
    silently dropped.
    """
    _, projects = project_service.list_projects(limit=10_000)

    counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    skipped = 0

    for project in projects:
        try:
            assessment = risk_service.analyze(project)
            counts[assessment.risk_level] += 1
        except MLModelUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        except MLServiceError:
            skipped += 1
            continue

    return {"distribution": counts, "skipped": skipped, "total_analyzed": sum(counts.values())}


@router.get("/financial-summary")
def financial_summary():
    _, projects = project_service.list_projects(limit=10_000)

    estimated = sum(_safe_float(p.get("estimated_cost")) for p in projects)
    actual = sum(_safe_float(p.get("actual_cost")) for p in projects)
    sanctioned = sum(_safe_float(p.get("sanctioned_amount")) for p in projects)
    released = sum(_safe_float(p.get("released_amount")) for p in projects)
    utilized = sum(_safe_float(p.get("utilized_amount")) for p in projects)

    return {
        "total_estimated_cost": round(estimated, 2),
        "total_actual_cost": round(actual, 2),
        "total_sanctioned_amount": round(sanctioned, 2),
        "total_released_amount": round(released, 2),
        "total_utilized_amount": round(utilized, 2),
        "cost_overrun_pct": round(100.0 * (actual - estimated) / estimated, 2) if estimated else 0.0,
        "fund_utilization_pct": round(100.0 * utilized / released, 2) if released else 0.0,
    }
