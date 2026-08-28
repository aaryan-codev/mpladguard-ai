from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

from .project import ProjectBase


class RiskFactor(BaseModel):
    feature: str
    value: float
    severity: Literal["medium", "high"]
    explanation: str
    z_score: Optional[float] = None


class RiskAnalyzeRequest(ProjectBase):
    """A single project payload to run through the anomaly detection model."""


class RiskAnalyzeResponse(BaseModel):
    project_id: str
    risk_score: float
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    anomaly: bool
    risk_factors: list[RiskFactor]
    model_version: str
    model_category: str
    warnings: list[str] = []
    disclaimer: str = (
        "This is an anomaly indicator for human review, not a fraud determination. "
        "A HIGH risk score means the project requires further investigation."
    )
