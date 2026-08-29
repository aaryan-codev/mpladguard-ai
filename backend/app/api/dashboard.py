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
    """
    Aggregates over the canonical (road) project records. Only metrics
    that are actually derivable from real dataset fields are returned --
    no sanctioned/released/utilized fund figures, since the current
    road dataset has no fund-flow columns (see the schema audit).
    """
    total, projects = project_service.list_projects(limit=10_000)

    total_estimated_cost_lakh = sum(_safe_float(p["financial"]["estimated_cost_lakh"]) for p in projects)
    total_actual_cost_lakh = sum(_safe_float(p["financial"]["actual_expenditure_lakh"]) for p in projects)
    completed = sum(1 for p in projects if p["work_status"] == "Completed")
    ongoing = sum(1 for p in projects if p["work_status"] == "Ongoing")
    delayed = sum(1 for p in projects if p["work_status"] == "Delayed")

    return {
        "total_projects": total,
        "total_estimated_cost_lakh": round(total_estimated_cost_lakh, 2),
        "total_actual_expenditure_lakh": round(total_actual_cost_lakh, 2),
        "completed_projects": completed,
        "ongoing_projects": ongoing,
        "delayed_projects": delayed,
        "currency_unit": "INR_lakh",
    }


@router.get("/risk-distribution")
def risk_distribution():
    """
    Runs risk analysis across all known projects and returns a
    LOW/MEDIUM/HIGH count breakdown. Projects that fail validation/
    analysis are skipped and counted separately rather than silently
    dropped.
    """
    ml_payloads = project_service.list_ml_payloads()

    counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0}
    skipped = 0

    for payload in ml_payloads:
        try:
            assessment = risk_service.analyze(payload)
            counts[assessment.risk_level] += 1
        except MLModelUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        except MLServiceError:
            skipped += 1
            continue

    return {"distribution": counts, "skipped": skipped, "total_analyzed": sum(counts.values())}


@router.get("/financial-summary")
def financial_summary():
    total, projects = project_service.list_projects(limit=10_000)

    estimated = sum(_safe_float(p["financial"]["estimated_cost_lakh"]) for p in projects)
    actual = sum(_safe_float(p["financial"]["actual_expenditure_lakh"]) for p in projects)

    return {
        "total_estimated_cost_lakh": round(estimated, 2),
        "total_actual_expenditure_lakh": round(actual, 2),
        "cost_overrun_pct": round(100.0 * (actual - estimated) / estimated, 2) if estimated else 0.0,
        "currency_unit": "INR_lakh",
    }


@router.get("/status-distribution")
def status_distribution():
    """State-of-work breakdown -- used by the dashboard's status pie/bar chart."""
    _, projects = project_service.list_projects(limit=10_000)
    counts: dict[str, int] = {}
    for p in projects:
        status = p["work_status"]
        counts[status] = counts.get(status, 0) + 1
    return {"distribution": counts, "total": len(projects)}


@router.get("/state-distribution")
def state_distribution():
    """Project count per state -- used by the dashboard's state-wise chart/map summary."""
    _, projects = project_service.list_projects(limit=10_000)
    counts: dict[str, int] = {}
    for p in projects:
        counts[p["state"]] = counts.get(p["state"], 0) + 1
    return {"distribution": counts, "total": len(projects)}
