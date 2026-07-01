# Where is Phase 0?

**Phase 0 lives in this folder** — not in the old `wholeselling_loop_agent` MVP.

```
d:\Personal\tx_fl_leadgen\
```

The old project at `d:\Personal\wholeselling_loop_agent\` is the separate Deal Loop Agent MVP and is **not** part of this build.

## Phase 0 deliverables (complete)

| Item | Location |
|------|----------|
| FastAPI app | `backend/app/main.py` |
| Postgres models | `backend/app/db/models.py` |
| Alembic migration | `backend/alembic/versions/001_initial_schema.py` |
| Docker Compose | `docker-compose.yml` |
| Environment template | `.env.example` |
| Adapter interfaces | `backend/app/adapters/interfaces.py` |
| Compliance gates | `backend/app/compliance/gates.py` |
| Health API | `GET /api/health` |

## Phase 1 deliverables (complete)

| Item | Location |
|------|----------|
| Harris connector | `backend/app/sources/tx/harris_tax_sale.py` |
| Dallas TRW connector | `backend/app/sources/tx/dallas_trw.py` |
| Tarrant connector | `backend/app/sources/tx/tarrant_tax_sale.py` |
| Ingestion service | `backend/app/services/lead_ingestion.py` |
| Fetch API | `POST /api/sources/fetch-tx` |
| CLI (no DB) | `python -m app.cli` |
| Real data fixtures | `backend/fixtures/` |
| Premium dashboard | `dashboard/` |
| API auth + pagination | `backend/app/auth/`, paginated `/api/leads` |
| CI pipeline | `.github/workflows/ci.yml` |

## Quick commands

```bash
cd d:\Personal\tx_fl_leadgen\backend
pip install -r requirements.txt
pytest

# Fetch leads without database (uses live county sites when reachable, else fixtures)
python -m app.cli

# Full stack with Postgres
cd d:\Personal\tx_fl_leadgen
docker compose up --build
# Then: POST http://localhost:8000/api/sources/fetch-tx
```
