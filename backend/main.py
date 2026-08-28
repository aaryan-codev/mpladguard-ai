"""
Legacy entry point, kept for backward compatibility with the original
`uvicorn main:app` command from inside backend/.

The application has been restructured into the app/ package (see
app/main.py) with proper routers, schemas, services, and ML integration.
This file simply re-exports that app so existing commands keep working.

Prefer running:
    uvicorn app.main:app --reload
from inside backend/, per backend/README.md.
"""
from app.main import app  # noqa: F401
