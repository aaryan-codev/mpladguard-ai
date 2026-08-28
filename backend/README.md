# MPLADGuard-AI — Backend

FastAPI service exposing project data and ML-powered risk analysis to the
frontend. The ML pipeline is fully decoupled from this backend — see
`ml/README.md` — and is only ever touched through
`app/services/ml_service.py`.

```
Database/CSV  →  Backend (FastAPI)  →  ML Service  →  Prediction (ml/ package)
```

## Setup

```bash
cd backend
pip install -r requirements.txt --break-system-packages   # or use a venv
cp .env.example .env   # optional, defaults work out of the box
```

## Train a model first

The API needs at least one trained model to serve `/api/risk/*`. From
the **repo root**:

```bash
python -m ml.src.train
```

(Trains on the bundled synthetic sample dataset. See `ml/README.md` to
train on real/accumulated data instead.)

## Run the server

From `backend/`:

```bash
uvicorn app.main:app --reload
```

Then open **http://127.0.0.1:8000/docs** for interactive Swagger docs.

## API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Service + ML model availability status |
| GET | `/api/projects` | List projects (`?limit=&offset=`) |
| GET | `/api/projects/{project_id}` | Get one project |
| POST | `/api/projects` | Create a project (in-memory for this MVP) |
| POST | `/api/risk/analyze` | Run risk analysis on a project payload |
| GET | `/api/risk/{project_id}` | Get cached (or on-demand) risk assessment for a known project |
| GET | `/api/dashboard/summary` | Project/fund counts |
| GET | `/api/dashboard/risk-distribution` | LOW/MEDIUM/HIGH counts across all known projects |
| GET | `/api/dashboard/financial-summary` | Aggregate financial figures |

### Example: `POST /api/risk/analyze`

Request:
```json
{
  "project_id": "MPLAD-001",
  "project_name": "River Bridge",
  "project_type": "bridge",
  "work_category": "bridge",
  "state": "Maharashtra",
  "district": "District A",
  "constituency": "Constituency 1",
  "estimated_cost": 2000000,
  "sanctioned_amount": 2000000,
  "released_amount": 1800000,
  "utilized_amount": 1700000,
  "actual_cost": 3200000,
  "number_of_payments": 4,
  "sanction_date": "2023-01-01",
  "work_order_date": "2023-02-01",
  "planned_completion_date": "2023-08-01",
  "actual_completion_date": "2024-06-01",
  "physical_progress": 45,
  "financial_progress": 88,
  "work_status": "Ongoing",
  "inspection_count": 1,
  "last_inspection_date": "2023-03-01",
  "issues_reported": 2,
  "issues_resolved": 0,
  "implementing_agency": "PWD",
  "agency_type": "Government",
  "dataset_type": "synthetic"
}
```

Response:
```json
{
  "project_id": "MPLAD-001",
  "risk_score": 92.2,
  "risk_level": "HIGH",
  "anomaly": true,
  "risk_factors": [
    {
      "feature": "financial_physical_progress_gap",
      "value": 43.0,
      "severity": "high",
      "explanation": "Gap between financial and physical progress is higher than typical for similar projects (value=43.0, reference median=0.9).",
      "z_score": 9.87
    }
  ],
  "model_version": "1.0.0",
  "model_category": "bridge",
  "warnings": [
    "This model was trained on synthetic/demo data only. Risk scores are illustrative, not based on verified real MPLADS data."
  ],
  "disclaimer": "This is an anomaly indicator for human review, not a fraud determination. A HIGH risk score means the project requires further investigation."
}
```

## Data storage

For the hackathon MVP, `GET /api/projects` reads from a CSV
(`PROJECTS_CSV_PATH`, defaults to the bundled synthetic sample dataset).
`POST /api/projects` stores new records in-memory for the life of the
process. Swapping in Postgres/Supabase later only requires changing
`app/services/project_service.py` — the ML pipeline and API routes never
touch storage directly.

## Error handling

- Pydantic validation errors → clean `422` with field-level detail.
- Unknown project/risk lookups → `404`.
- No trained model available → `503` with a hint to run `python -m ml.src.train`.
- Any other unexpected error → generic `500`, full traceback logged
  server-side only (never returned to the client).

## Security

No secrets are hardcoded. All configuration is read from environment
variables via `app/core/config.py` (see `.env.example`). `.env` is
git-ignored.

## Running tests

```bash
cd backend
python -m pytest tests/ -v
```

## Limitations

- In-memory project store for `POST /api/projects` — restarting the
  server loses anything created that way (by design, for the MVP).
- `GET /api/dashboard/risk-distribution` runs risk analysis on every
  known project synchronously (fine for ~100s of rows, not for
  production scale).
- CORS defaults to `*` for local development — restrict
  `CORS_ALLOW_ORIGINS` before any real deployment.
