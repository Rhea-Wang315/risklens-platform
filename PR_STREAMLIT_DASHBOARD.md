# PR: Streamlit Operator Dashboard (Week 3 MVP)

## Why

For interview demos, a lightweight UI makes RiskLens much easier to understand than curl commands.
This PR adds a Streamlit operator dashboard that talks to the existing FastAPI service over HTTP.

## What Changed

- New Streamlit dashboard: `dashboard/app.py`
  - Recent Decisions: list + filter (`GET /api/v1/decisions`)
  - Evaluate Alert: generate decisions (`POST /api/v1/evaluate`)
  - Rules Management: create/update/delete rules (`/api/v1/rules`)
- Added optional dependency group: `pyproject.toml` -> `.[dashboard]`
- README: documented how to run the dashboard locally
- Alembic: allow overriding DB url via `DATABASE_URL` (helps local/dev and CI-like runs)

## How To Test (Local)

1) Start infra (Postgres recommended via Docker)

2) Install deps

```bash
pip install -e ".[dev,dashboard]"
```

3) Run API

```bash
risklens serve
```

4) Run dashboard

```bash
streamlit run dashboard/app.py
```

5) Open

- API docs: http://localhost:8000/docs
- Dashboard: http://localhost:8501

If your API base URL differs:

```bash
export RISKLENS_API_BASE_URL=http://localhost:8000
```

## Verification

- `pytest tests/` passes when `DATABASE_URL` points at a running Postgres instance
- Non-DB tests pass without Postgres/Kafka running

## Notes

- The dashboard is intentionally minimal (MVP) and designed for demos.
- Kafka can be down; API evaluation still works (producer degrades gracefully).
