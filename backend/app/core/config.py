"""
Backend application configuration.

All environment-dependent values are read here via pydantic-settings so
nothing is hardcoded. See .env.example for the full list of variables.
"""
from __future__ import annotations

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "MPLADGuard-AI Backend"
    app_version: str = "1.0.0"
    environment: str = "development"

    # CORS
    cors_allow_origins: str = "*"  # comma-separated in .env, e.g. "http://localhost:5173"

    # Data sources -----------------------------------------------------------
    # Where the backend reads "known" project records from for GET /api/projects.
    # Kept as a simple CSV for the hackathon MVP; swap for Supabase/Postgres later
    # without touching the ML pipeline (see services/project_service.py).
    projects_csv_path: str | None = None

    # Optional database (not required to run the ML model locally)
    database_url: str | None = None
    supabase_url: str | None = None
    supabase_service_key: str | None = None

    log_level: str = "INFO"

    @field_validator("projects_csv_path", "database_url", "supabase_url", "supabase_service_key", mode="before")
    @classmethod
    def _blank_to_default(cls, v):
        # Treat an empty string in .env (e.g. "PROJECTS_CSV_PATH=") as "unset"
        # rather than an explicit empty path/URL.
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @property
    def effective_projects_csv_path(self) -> str:
        if self.projects_csv_path:
            return self.projects_csv_path
        # Current MVP scope: road projects only.
        return str(REPO_ROOT / "ml" / "data" / "raw" / "mplads_road_projects_synthetic.csv")

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_allow_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


settings = Settings()
