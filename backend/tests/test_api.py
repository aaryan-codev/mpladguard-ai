import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "online"
    assert body["system"] == "MPLADGuard-AI"
    assert body["ml_models_available"] is True


def test_list_projects():
    r = client.get("/api/projects?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] > 0  # the road dataset should always be loaded
    assert len(body["projects"]) <= 5


def test_project_shape_has_no_leaked_demo_fields_at_top_level():
    """demo_enrichment must stay nested and flagged, never mixed into real fields."""
    r = client.get("/api/projects?limit=1")
    project = r.json()["projects"][0]
    assert "domain_details" in project
    assert "financial" in project
    assert "schedule" in project
    assert project["demo_enrichment"]["is_demo_data"] is True
    assert "contractor_name" not in project  # must be nested, not flattened


def test_get_project_not_found():
    r = client.get("/api/projects/DOES-NOT-EXIST")
    assert r.status_code == 404


def test_get_existing_project():
    listing = client.get("/api/projects?limit=1").json()
    project_id = listing["projects"][0]["project_id"]
    r = client.get(f"/api/projects/{project_id}")
    assert r.status_code == 200
    assert r.json()["project_id"] == project_id


VALID_ROAD_PAYLOAD = {
    "project_id": "TEST-UNIT-ROAD-001",
    "state": "TestState",
    "district": "TestDistrict",
    "parliamentary_constituency": "TestConstituency",
    "implementing_agency": "PWD",
    "road_type": "Village Road",
    "road_length_km": 3.5,
    "estimated_cost_lakh": 20.0,
    "actual_expenditure_lakh": 21.5,
    "planned_duration_days": 90,
    "actual_duration_days": 100,
    "project_start_date": "2023-01-01",
    "project_completion_date": "2023-04-10",
    "latitude": 20.0,
    "longitude": 78.0,
    "project_status": "Completed",
}


def test_risk_analyze_returns_valid_shape():
    r = client.post("/api/risk/analyze", json=VALID_ROAD_PAYLOAD)
    assert r.status_code == 200
    body = r.json()
    assert body["project_id"] == "TEST-UNIT-ROAD-001"
    assert 0 <= body["risk_score"] <= 100
    assert body["risk_level"] in ("LOW", "MEDIUM", "HIGH")
    assert isinstance(body["anomaly"], bool)
    assert body["model_category"] == "road"
    assert "disclaimer" in body


def test_risk_analyze_flags_a_clear_cost_and_delay_outlier_as_high_risk():
    outlier_payload = dict(VALID_ROAD_PAYLOAD)
    outlier_payload["project_id"] = "TEST-UNIT-ROAD-OUTLIER"
    outlier_payload["actual_expenditure_lakh"] = 60.0  # 3x estimate
    outlier_payload["actual_duration_days"] = 400  # 4.4x planned
    r = client.post("/api/risk/analyze", json=outlier_payload)
    assert r.status_code == 200
    body = r.json()
    assert body["risk_level"] == "HIGH"
    assert body["anomaly"] is True
    assert len(body["risk_factors"]) > 0


def test_risk_analyze_rejects_invalid_status():
    bad_payload = dict(VALID_ROAD_PAYLOAD)
    bad_payload["project_id"] = "TEST-UNIT-ROAD-BADSTATUS"
    bad_payload["project_status"] = "NotARealStatus"
    r = client.post("/api/risk/analyze", json=bad_payload)
    assert r.status_code == 422


def test_risk_analyze_rejects_non_positive_road_length():
    bad_payload = dict(VALID_ROAD_PAYLOAD)
    bad_payload["project_id"] = "TEST-UNIT-ROAD-BADLENGTH"
    bad_payload["road_length_km"] = 0
    r = client.post("/api/risk/analyze", json=bad_payload)
    assert r.status_code == 422


def test_get_risk_for_known_project_computes_on_demand():
    listing = client.get("/api/projects?limit=1").json()
    project_id = listing["projects"][0]["project_id"]
    r = client.get(f"/api/risk/{project_id}")
    assert r.status_code == 200
    assert r.json()["project_id"] == project_id


def test_get_risk_for_unknown_project_404s():
    r = client.get("/api/risk/DOES-NOT-EXIST")
    assert r.status_code == 404


def test_dashboard_summary_shape():
    r = client.get("/api/dashboard/summary")
    assert r.status_code == 200
    body = r.json()
    for key in (
        "total_projects",
        "total_estimated_cost_lakh",
        "total_actual_expenditure_lakh",
        "completed_projects",
        "ongoing_projects",
        "delayed_projects",
    ):
        assert key in body
    # No fabricated fund-flow figures the road dataset doesn't actually have.
    assert "total_sanctioned_amount" not in body
    assert "total_utilized_amount" not in body


def test_dashboard_financial_summary_shape():
    r = client.get("/api/dashboard/financial-summary")
    assert r.status_code == 200
    body = r.json()
    assert "cost_overrun_pct" in body
    assert "fund_utilization_pct" not in body  # not derivable from road dataset


def test_dashboard_risk_distribution_counts_all_projects():
    r = client.get("/api/dashboard/risk-distribution")
    assert r.status_code == 200
    body = r.json()
    total = sum(body["distribution"].values())
    assert total == body["total_analyzed"]
    assert body["total_analyzed"] + body["skipped"] > 0


def test_dashboard_status_and_state_distribution():
    r = client.get("/api/dashboard/status-distribution")
    assert r.status_code == 200
    assert sum(r.json()["distribution"].values()) == r.json()["total"]

    r = client.get("/api/dashboard/state-distribution")
    assert r.status_code == 200
    assert sum(r.json()["distribution"].values()) == r.json()["total"]


def test_create_project_then_fetch_it():
    payload = dict(VALID_ROAD_PAYLOAD)
    payload["project_id"] = "TEST-CREATE-ROAD-001"
    r = client.post("/api/projects", json=payload)
    assert r.status_code == 201
    created = r.json()
    assert created["project_id"] == "TEST-CREATE-ROAD-001"
    assert created["demo_enrichment"]["is_demo_data"] is True

    r = client.get("/api/projects/TEST-CREATE-ROAD-001")
    assert r.status_code == 200


def test_create_duplicate_project_conflicts():
    payload = dict(VALID_ROAD_PAYLOAD)
    payload["project_id"] = "TEST-DUP-ROAD-001"
    r1 = client.post("/api/projects", json=payload)
    assert r1.status_code == 201
    r2 = client.post("/api/projects", json=payload)
    assert r2.status_code == 409


def test_openapi_docs_available():
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    for expected in ["/api/health", "/api/projects", "/api/risk/analyze", "/api/dashboard/summary"]:
        assert expected in paths
