from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class ProjectBase(BaseModel):
    """
    Mirrors the raw MPLADS project schema used by the ML pipeline
    (see ml/src/data_loader.REQUIRED_COLUMNS). Kept intentionally close to
    that schema so a project record can be sent straight to ML risk
    analysis without remapping.
    """

    project_id: str
    project_name: str
    project_type: str
    work_category: str
    state: str
    district: str
    constituency: str
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    estimated_cost: float = Field(..., ge=0)
    sanctioned_amount: float = Field(..., ge=0)
    released_amount: float = Field(..., ge=0)
    utilized_amount: float = Field(..., ge=0)
    actual_cost: float = Field(..., ge=0)
    number_of_payments: int = Field(..., ge=0)

    sanction_date: str
    work_order_date: str
    planned_completion_date: str
    actual_completion_date: Optional[str] = None
    delay_days: Optional[int] = None

    physical_progress: float = Field(..., ge=0, le=100)
    financial_progress: float = Field(..., ge=0, le=100)
    work_status: str

    inspection_count: int = Field(..., ge=0)
    last_inspection_date: Optional[str] = None
    issues_reported: int = Field(0, ge=0)
    issues_resolved: int = Field(0, ge=0)

    implementing_agency: str
    agency_type: str

    contractor_id: Optional[str] = None
    contractor_name: Optional[str] = None
    contract_value: Optional[float] = Field(None, ge=0)

    tender_id: Optional[str] = None
    estimated_tender_value: Optional[float] = Field(None, ge=0)
    bid_count: Optional[int] = Field(None, ge=0)
    winning_bid: Optional[float] = Field(None, ge=0)
    second_lowest_bid: Optional[float] = Field(None, ge=0)
    procurement_method: Optional[str] = None

    estimated_beneficiaries: Optional[int] = Field(None, ge=0)
    population_served: Optional[int] = Field(None, ge=0)

    dataset_type: str = "synthetic"

    @field_validator("dataset_type")
    @classmethod
    def validate_dataset_type(cls, v: str) -> str:
        if v not in ("real", "synthetic"):
            raise ValueError("dataset_type must be 'real' or 'synthetic'")
        return v

    @field_validator("issues_resolved")
    @classmethod
    def resolved_not_greater_than_reported(cls, v, info):
        reported = info.data.get("issues_reported")
        if reported is not None and v > reported:
            raise ValueError("issues_resolved cannot exceed issues_reported")
        return v


class ProjectCreate(ProjectBase):
    pass


class ProjectOut(ProjectBase):
    pass


class ProjectListResponse(BaseModel):
    total: int
    projects: list[ProjectOut]
