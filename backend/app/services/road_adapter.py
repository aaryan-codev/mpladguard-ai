"""
Road-domain adapter.

Converts a raw row from mplads_road_projects_synthetic.csv (see
ml/src/road/config.REQUIRED_COLUMNS) into two different shapes:

1. `to_ml_payload()` -- the exact raw fields the road ML pipeline needs
   (ml/src/road/*), tagged with work_category="road" so
   ml/src/predict.py routes it to the road model. Never includes
   fabricated data.

2. `build_project_record()` -- the project representation served by the
   API / consumed by the frontend. It has three clearly separated parts:
     - real fields straight from the road dataset (core project info)
     - `demo_enrichment`: contractor/tender/beneficiary fields that do
       NOT exist in the current road dataset. These are generated
       deterministically (seeded by project_id, not random per-request)
       purely so the hackathon UI can show a fuller project profile.
       They are explicitly flagged `is_demo_data: true` and are NEVER
       passed to `to_ml_payload()` / the risk model.

This is the one place a future domain adapter (bridge/school/water)
would be added alongside this one -- project_service.py only needs to
know which adapter to call for a given dataset/category.
"""
from __future__ import annotations

import hashlib
from typing import Any, Optional

CONTRACTOR_NAMES = [
    "Shree Balaji Infra Projects",
    "Nav Bharat Road Constructions",
    "Rajasthan Highway Builders Pvt Ltd",
    "Sharma Infrastructure Ltd.",
    "Konkan Engineering & Roads",
    "Deccan Civil Works",
    "Ganga Setu Constructions",
    "Vindhya Road Contractors",
]

PROCUREMENT_METHODS = ["Open Tender", "Limited Tender", "Direct Contract", "e-Tender"]


def _seed_int(project_id: str, salt: str, mod: int) -> int:
    """Deterministic pseudo-random int in [0, mod) seeded by project_id.

    Using a hash instead of `random` keeps demo enrichment stable across
    requests/restarts without needing to persist it anywhere.
    """
    digest = hashlib.sha256(f"{project_id}:{salt}".encode()).hexdigest()
    return int(digest[:8], 16) % mod


def _demo_enrichment(project_id: str, estimated_cost_lakh: float) -> dict[str, Any]:
    """
    Illustrative contractor/tender/beneficiary data for UI polish only.

    Explicitly NOT derived from or fed back into the AI risk model --
    see the module docstring. bid amounts are generated as plausible
    percentages of the REAL estimated cost so they look coherent on
    screen, but they are still demo values, not measurements.
    """
    contractor_idx = _seed_int(project_id, "contractor", len(CONTRACTOR_NAMES))
    procurement_idx = _seed_int(project_id, "procurement", len(PROCUREMENT_METHODS))
    bid_count = 3 + _seed_int(project_id, "bidcount", 6)  # 3-8 bidders

    winning_bid_pct = 92 + _seed_int(project_id, "winbid", 12)  # 92-103% of estimate
    second_bid_pct = winning_bid_pct + 2 + _seed_int(project_id, "secondbid", 8)

    winning_bid = round(estimated_cost_lakh * winning_bid_pct / 100.0, 2)
    second_lowest_bid = round(estimated_cost_lakh * second_bid_pct / 100.0, 2)

    beneficiaries = 500 + _seed_int(project_id, "beneficiaries", 9500)

    return {
        "is_demo_data": True,
        "note": "Illustrative demo data for display only -- not used by the AI risk model.",
        "contractor_id": f"CONT-{1000 + _seed_int(project_id, 'contractorid', 8999)}",
        "contractor_name": CONTRACTOR_NAMES[contractor_idx],
        "tender_id": f"TND-{10000 + _seed_int(project_id, 'tenderid', 89999)}",
        "procurement_method": PROCUREMENT_METHODS[procurement_idx],
        "bid_count": bid_count,
        "winning_bid_lakh": winning_bid,
        "second_lowest_bid_lakh": second_lowest_bid,
        "estimated_beneficiaries": beneficiaries,
        "population_served": beneficiaries - _seed_int(project_id, "popserved", 200),
    }


ROAD_ML_FIELDS = [
    "project_id",
    "state",
    "district",
    "parliamentary_constituency",
    "implementing_agency",
    "road_type",
    "road_length_km",
    "estimated_cost_lakh",
    "actual_expenditure_lakh",
    "planned_duration_days",
    "actual_duration_days",
    "project_start_date",
    "project_completion_date",
    "latitude",
    "longitude",
    "project_status",
]


def to_ml_payload(row: dict[str, Any]) -> dict[str, Any]:
    """Exact real fields the road ML pipeline needs, tagged for routing."""
    payload = {k: row.get(k) for k in ROAD_ML_FIELDS}
    payload["work_category"] = "road"
    return payload


def build_project_record(row: dict[str, Any]) -> dict[str, Any]:
    """
    Canonical API-facing project record for a road project.

    Top-level fields are all REAL data from the dataset. `demo_enrichment`
    is the only fabricated part and is nested + flagged so the frontend
    can render it distinctly (e.g. a "demo data" badge).
    """
    project_id = str(row["project_id"])
    estimated_cost_lakh = float(row["estimated_cost_lakh"])
    actual_expenditure_lakh = float(row["actual_expenditure_lakh"])
    planned_duration_days = int(row["planned_duration_days"])
    actual_duration_days = int(row["actual_duration_days"])

    return {
        "project_id": project_id,
        "project_category": "road",
        "project_name": f"{row['road_type']} - {row['district']}, {row['state']}",
        "state": row["state"],
        "district": row["district"],
        "constituency": row["parliamentary_constituency"],
        "implementing_agency": row["implementing_agency"],
        "latitude": _to_optional_float(row.get("latitude")),
        "longitude": _to_optional_float(row.get("longitude")),
        "domain_details": {
            "road_type": row["road_type"],
            "road_length_km": float(row["road_length_km"]),
        },
        "financial": {
            "estimated_cost_lakh": estimated_cost_lakh,
            "actual_expenditure_lakh": actual_expenditure_lakh,
            "cost_deviation_pct": round(
                100.0 * (actual_expenditure_lakh - estimated_cost_lakh) / estimated_cost_lakh, 2
            )
            if estimated_cost_lakh
            else None,
            "currency_unit": "INR_lakh",
        },
        "schedule": {
            "project_start_date": row.get("project_start_date"),
            "project_completion_date": row.get("project_completion_date") or None,
            "planned_duration_days": planned_duration_days,
            "actual_duration_days": actual_duration_days,
            "delay_days": actual_duration_days - planned_duration_days,
            "delay_pct": round(
                100.0 * (actual_duration_days - planned_duration_days) / planned_duration_days, 2
            )
            if planned_duration_days
            else None,
        },
        "work_status": row["project_status"],
        "demo_enrichment": _demo_enrichment(project_id, estimated_cost_lakh),
    }


def _to_optional_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
