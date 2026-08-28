"""
Project data service.

For the hackathon MVP this is backed by a CSV file (see
Settings.projects_csv_path) loaded into memory, plus an in-memory list for
projects created via POST /api/projects during the running process.

Swapping this for Postgres/Supabase later only requires changing this
file -- the ML pipeline and API routes never touch storage directly
(Database -> Backend -> ML Service -> Prediction, per the architecture).
"""
from __future__ import annotations

import logging
import threading
from typing import Optional

import pandas as pd

from ..core.config import settings

logger = logging.getLogger(__name__)

_lock = threading.RLock()  # RLock: create_project() calls get_project() while holding the lock
_projects_df: Optional[pd.DataFrame] = None
_runtime_projects: list[dict] = []  # projects added via POST during this process


class ProjectNotFoundError(Exception):
    pass


def _load_csv_once() -> pd.DataFrame:
    global _projects_df
    if _projects_df is None:
        path = settings.effective_projects_csv_path
        try:
            _projects_df = pd.read_csv(path)
            _projects_df = _projects_df.fillna("")
            logger.info("Loaded %d projects from %s", len(_projects_df), path)
        except FileNotFoundError:
            logger.warning(
                "Projects CSV not found at %s; starting with an empty project list.",
                path,
            )
            _projects_df = pd.DataFrame()
    return _projects_df


def list_projects(limit: int = 100, offset: int = 0) -> tuple[int, list[dict]]:
    with _lock:
        df = _load_csv_once()
        csv_records = df.to_dict(orient="records")
        all_records = csv_records + _runtime_projects
        total = len(all_records)
        page = all_records[offset : offset + limit]
        return total, page


def get_project(project_id: str) -> dict:
    with _lock:
        df = _load_csv_once()
        match = df[df["project_id"] == project_id] if not df.empty else df
        if not df.empty and len(match) > 0:
            return match.iloc[0].to_dict()

        for p in _runtime_projects:
            if p.get("project_id") == project_id:
                return p

    raise ProjectNotFoundError(f"Project '{project_id}' not found.")


def create_project(project: dict) -> dict:
    with _lock:
        try:
            existing = get_project(project["project_id"])
            if existing:
                raise ValueError(f"Project '{project['project_id']}' already exists.")
        except ProjectNotFoundError:
            pass  # good, it's new
        _runtime_projects.append(project)
        logger.info("Created project '%s' (in-memory, not persisted to CSV).", project["project_id"])
    return project


def reset_cache() -> None:
    """Mainly for tests: force the CSV to be reloaded on next access."""
    global _projects_df
    with _lock:
        _projects_df = None
