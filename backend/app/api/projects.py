from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query

from ..schemas.project import ProjectListResponse, ProjectOut, RoadProjectCreate
from ..services import project_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=ProjectListResponse)
def list_projects(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> ProjectListResponse:
    total, records = project_service.list_projects(limit=limit, offset=offset)
    return ProjectListResponse(total=total, projects=records)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str) -> ProjectOut:
    try:
        record = project_service.get_project(project_id)
    except project_service.ProjectNotFoundError:
        raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found.")
    return record


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(project: RoadProjectCreate) -> ProjectOut:
    try:
        created = project_service.create_project(project.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception:  # noqa: BLE001
        logger.exception("Failed to create project '%s'", project.project_id)
        raise HTTPException(status_code=500, detail="Failed to create project.")
    return created
