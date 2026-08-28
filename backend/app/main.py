"""
MPLADGuard-AI backend entry point.

Run with:
    uvicorn app.main:app --reload --app-dir backend

or, from the backend/ directory:
    uvicorn app.main:app --reload
"""
from __future__ import annotations

import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import dashboard, health, projects, risk
from .core.config import settings
from .core.logging import configure_logging

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("%s v%s starting up (env=%s)", settings.app_name, settings.app_version, settings.environment)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AI-powered decision-support API for MPLADS project monitoring. "
        "Produces anomaly/risk indicators for human review -- NOT fraud "
        "determinations."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Never leak raw stack traces to API clients."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


app.include_router(health.router)
app.include_router(projects.router)
app.include_router(risk.router)
app.include_router(dashboard.router)
