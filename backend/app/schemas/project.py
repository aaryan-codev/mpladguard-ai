"""
Road-domain project schemas -- the ACTIVE schemas for the current SIH
MVP (road projects only).

The original generic multi-category ProjectBase/ProjectOut schemas are
preserved unchanged in `project_generic.py`. They are not wired to any
route right now, but are the intended foundation for bridge/school/
water/etc. once those domains get their own dataset + ML module,
exactly like ml/src/road/ was added alongside the generic ml/src/
pipeline.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RoadProjectCreate(BaseModel):
    """
    Payload for POST /api/projects. Mirrors the raw columns in
    mplads_road_projects_synthetic.csv (see ml/src/road/config.
    REQUIRED_COLUMNS) so a created project can be sent straight to
    road risk analysis without remapping.
    """

    project_id: str
    state: str
    district: str
    parliamentary_constituency: str
    implementing_agency: str
    road_type: str
    road_length_km: float = Field(..., gt=0)
    estimated_cost_lakh: float = Field(..., gt=0)
    actual_expenditure_lakh: float = Field(..., gt=0)
    planned_duration_days: int = Field(..., gt=0)
    actual_duration_days: int = Field(..., gt=0)
    project_start_date: str
    project_completion_date: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    project_status: str = Field(..., pattern="^(Completed|Ongoing|Delayed)$")


class DomainDetails(BaseModel):
    road_type: str
    road_length_km: float


class FinancialInfo(BaseModel):
    estimated_cost_lakh: float
    actual_expenditure_lakh: float
    cost_deviation_pct: Optional[float] = None
    currency_unit: str = "INR_lakh"


class ScheduleInfo(BaseModel):
    project_start_date: Optional[str] = None
    project_completion_date: Optional[str] = None
    planned_duration_days: int
    actual_duration_days: int
    delay_days: int
    delay_pct: Optional[float] = None


class DemoEnrichment(BaseModel):
    """
    Illustrative contractor/tender/beneficiary data. NOT present in the
    real road dataset, generated deterministically for UI polish, and
    NEVER used as ML input -- see backend/app/services/road_adapter.py.
    """

    is_demo_data: bool = True
    note: str
    contractor_id: str
    contractor_name: str
    tender_id: str
    procurement_method: str
    bid_count: int
    winning_bid_lakh: float
    second_lowest_bid_lakh: float
    estimated_beneficiaries: int
    population_served: int


class ProjectOut(BaseModel):
    """Canonical project record served by GET /api/projects and /api/projects/{id}."""

    project_id: str
    project_category: str = "road"
    project_name: str
    state: str
    district: str
    constituency: str
    implementing_agency: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    domain_details: DomainDetails
    financial: FinancialInfo
    schedule: ScheduleInfo
    work_status: str
    demo_enrichment: DemoEnrichment


class ProjectListResponse(BaseModel):
    total: int
    projects: list[ProjectOut]
