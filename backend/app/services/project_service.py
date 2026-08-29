"""
Project data service.

CURRENT MVP SCOPE: road projects only. Backed by the road dataset CSV
(see Settings.projects_csv_path) loaded into memory, plus an in-memory
list for projects created via POST /api/projects during the running
process.

Every loaded/created project is kept in TWO shapes:
  - `_ml_payloads`: exact raw fields the road ML pipeline needs
    (road_adapter.to_ml_payload) -- never includes fabricated data.
  - `_api_records`: the canonical nested record served by GET
    /api/projects (road_adapter.build_project_record) -- includes the
    clearly-flagged `demo_enrichment` block for UI polish.

This split is the "adapter" layer discussed in the data-contract
review: the generic ProjectBase/ProjectOut schemas in schemas/project.py
are preserved for future non-road domains, but the current MVP's
storage and API responses are road-shaped.

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
from . import road_adapter

logger = logging.getLogger(__name__)

_lock = threading.RLock()  # RLock: create_project() calls get_project() while holding the lock
_loaded = False
_ml_payloads: dict[str, dict] = {}   # project_id -> raw fields for the ML pipeline
_api_records: dict[str, dict] = {}   # project_id -> canonical nested API record
_order: list[str] = []               # preserves CSV row order for stable pagination


class ProjectNotFoundError(Exception):
    pass


def _load_csv_once() -> None:
    global _loaded
    if _loaded:
        return
    path = settings.effective_projects_csv_path
    try:
        df = pd.read_csv(path)
    except FileNotFoundError:
        logger.warning("Projects CSV not found at %s; starting with an empty project list.", path)
        _loaded = True
        return

    for row in df.to_dict(orient="records"):
        row = {k: (None if pd.isna(v) else v) for k, v in row.items()}
        project_id = str(row["project_id"])
        _ml_payloads[project_id] = road_adapter.to_ml_payload(row)
        _api_records[project_id] = road_adapter.build_project_record(row)
        _order.append(project_id)

    logger.info("Loaded %d road projects from %s", len(_order), path)
    _loaded = True


def list_projects(limit: int = 100, offset: int = 0) -> tuple[int, list[dict]]:
    with _lock:
        _load_csv_once()
        total = len(_order)
        page_ids = _order[offset : offset + limit]
        page = [_api_records[pid] for pid in page_ids]
        return total, page


def get_project(project_id: str) -> dict:
    """Returns the canonical API-facing record (for GET /api/projects/{id})."""
    with _lock:
        _load_csv_once()
        record = _api_records.get(project_id)
    if record is None:
        raise ProjectNotFoundError(f"Project '{project_id}' not found.")
    return record


def list_ml_payloads() -> list[dict]:
    """All known projects' raw ML-ready fields (for dashboard-wide risk analysis)."""
    with _lock:
        _load_csv_once()
        return [_ml_payloads[pid] for pid in _order]


def get_ml_payload(project_id: str) -> dict:
    """Returns the raw fields the ML pipeline needs (for risk analysis)."""
    with _lock:
        _load_csv_once()
        payload = _ml_payloads.get(project_id)
    if payload is None:
        raise ProjectNotFoundError(f"Project '{project_id}' not found.")
    return payload


def create_project(raw_road_fields: dict) -> dict:
    """
    Accepts raw road fields (see road_adapter.ROAD_ML_FIELDS), builds
    both representations, and stores them in-memory (not persisted to
    the CSV -- a fresh backend restart will not remember it).
    """
    with _lock:
        _load_csv_once()
        project_id = str(raw_road_fields["project_id"])
        if project_id in _api_records:
            raise ValueError(f"Project '{project_id}' already exists.")

        _ml_payloads[project_id] = road_adapter.to_ml_payload(raw_road_fields)
        record = road_adapter.build_project_record(raw_road_fields)
        _api_records[project_id] = record
        _order.insert(0, project_id)  # new projects show up first
        logger.info("Created project '%s' (in-memory, not persisted to CSV).", project_id)
    return record


def reset_cache() -> None:
    """Mainly for tests: force the CSV to be reloaded on next access."""
    global _loaded
    with _lock:
        _loaded = False
        _ml_payloads.clear()
        _api_records.clear()
        _order.clear()
