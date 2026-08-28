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


def test_list_projects():
    r = client.get("/api/projects?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 0
    assert len(body["projects"]) <= 5


def test_get_project_not_found():
    r = client.get("/api/projects/DOES-NOT-EXIST")
    assert r.status_code == 404


def test_get_existing_project():
    listing = client.get("/api/projects?limit=1").json()
    if listing["total"] == 0:
        pytest.skip("No sample projects available to test against.")
    project_id = listing["projects"][0]["project_id"]
    r = client.get(f"/api/projects/{project_id}")
    assert r.status_code == 200
    assert r.json()["project_id"] == project_id


VALID_PROJECT_PAYLOAD = {
    "project_id": "TEST-UNIT-001",
    "project_name": "Unit Test Project",
    "project_type": "road",
    "work_category": "road",
    "state": "TestState",
    "district": "TestDistrict",
    "constituency": "TestConstituency",
    "estimated_cost": 1000000,
    "sanctioned_amount": 1000000,
    "released_amount": 900000,
    "utilized_amount": 850000,
    "actual_cost": 1050000,
    "number_of_payments": 3,
    "sanction_date": "2023-01-01",
    "work_order_date": "2023-02-01",
    "planned_completion_date": "2023-08-01",
    "actual_completion_date": "2023-09-01",
    "physical_progress": 80,
    "financial_progress": 85,
    "work_status": "Completed",
    "inspection_count": 3,
    "last_inspection_date": "2023-07-01",
    "issues_reported": 2,
    "issues_resolved": 2,
    "implementing_agency": "PWD",
    "agency_type": "Government",
    "dataset_type": "synthetic",
}


def test_risk_analyze_returns_valid_shape():
    r = client.post("/api/risk/analyze", json=VALID_PROJECT_PAYLOAD)
    assert r.status_code in (200, 503)  # 503 only if no model has been trained yet
    if r.status_code == 200:
        body = r.json()
        assert body["project_id"] == "TEST-UNIT-001"
        assert 0 <= body["risk_score"] <= 100
        assert body["risk_level"] in ("LOW", "MEDIUM", "HIGH")
        assert isinstance(body["anomaly"], bool)
        assert "disclaimer" in body


def test_risk_analyze_rejects_invalid_progress():
    bad_payload = dict(VALID_PROJECT_PAYLOAD)
    bad_payload["physical_progress"] = 150
    r = client.post("/api/risk/analyze", json=bad_payload)
    assert r.status_code == 422


def test_risk_analyze_rejects_issues_resolved_over_reported():
    bad_payload = dict(VALID_PROJECT_PAYLOAD)
    bad_payload["issues_reported"] = 1
    bad_payload["issues_resolved"] = 5
    r = client.post("/api/risk/analyze", json=bad_payload)
    assert r.status_code == 422


def test_dashboard_summary_shape():
    r = client.get("/api/dashboard/summary")
    assert r.status_code == 200
    body = r.json()
    for key in ("total_projects", "total_sanctioned_amount", "completed_projects", "ongoing_projects"):
        assert key in body


def test_dashboard_financial_summary_shape():
    r = client.get("/api/dashboard/financial-summary")
    assert r.status_code == 200
    body = r.json()
    assert "cost_overrun_pct" in body
    assert "fund_utilization_pct" in body


def test_openapi_docs_available():
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    for expected in ["/api/health", "/api/projects", "/api/risk/analyze", "/api/dashboard/summary"]:
        assert expected in paths
