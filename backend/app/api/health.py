from __future__ import annotations

from fastapi import APIRouter

from ..core.config import settings
from ..schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    from ..core.config import REPO_ROOT

    registry_path = REPO_ROOT / "ml" / "models" / "registry.json"
    return HealthResponse(
        status="online",
        system="MPLADGuard-AI",
        version=settings.app_version,
        ml_models_available=registry_path.exists(),
    )
