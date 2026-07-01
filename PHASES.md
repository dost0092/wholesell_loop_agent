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

## Phase 2 deliverables (complete)

| Item | Location |
|------|----------|
| Miami-Dade connector | `backend/app/sources/fl/miami_dade_delinquent.py` |
| Broward connector | `backend/app/sources/fl/broward_tax_deed.py` |
| Hillsborough connector | `backend/app/sources/fl/hillsborough_tax_deed.py` |
| Fetch FL API | `POST /api/sources/fetch-fl` |
| Fetch all API | `POST /api/sources/fetch-all` |
| FL fixtures | `backend/fixtures/miami_dade_*`, `broward_*`, `hillsborough_*` |
| Dashboard FL fetch | `dashboard/src/pages/SourcesPage.tsx` |

## Phase 3 deliverables — AI Scoring (complete)

| Item | Location |
|------|----------|
| Deal scorer (heuristic + Claude) | `backend/app/agents/scorer.py` |
| Scoring service | `backend/app/services/scoring.py` |
| Score API | `POST /api/leads/{id}/score` |
| Dashboard score + reasoning | `dashboard/src/pages/LeadsPage.tsx` |

Deterministic heuristic runs with **no API key**; set `ANTHROPIC_API_KEY` to use Claude.

## Phase 4 deliverables — Owner Discovery (complete)

| Item | Location |
|------|----------|
| Skip trace (mock + BatchData) | `backend/app/adapters/skip_trace.py` |
| Entity / LLC lookup (mock + OpenCorporates) | `backend/app/adapters/entity_lookup.py` |
| Owner discovery service | `backend/app/services/owner_discovery.py` |
| Trace API | `POST /api/leads/{id}/trace` |

Mock providers produce clearly-flagged synthetic contacts offline; real providers
activate when `SKIP_TRACE_API_KEY` / `OPENCORPORATES_API_KEY` are set.

## Phase 5 deliverables — Contact Validation + Email Outreach (complete)

| Item | Location |
|------|----------|
| Contact validation (MX, phone type, DNC scrub) | `backend/app/services/contact_validation.py` |
| Email drafting (template + Claude) | `backend/app/agents/message_writer.py` |
| Outreach service (draft/approve/reject/send) | `backend/app/services/outreach.py` |
| Email senders (console + SMTP) | `backend/app/adapters/email.py` |
| Compliance gate (enforced on every send) | `backend/app/compliance/gates.py` |
| Pipeline orchestrator | `backend/app/services/pipeline.py` |
| Validate / draft / pipeline APIs | `POST /api/leads/{id}/validate`, `/draft`, `/pipeline` |
| Approval actions | `POST /api/approval-queue/{id}/approve\|reject\|send` |
| DNC list management | `GET\|POST /api/dnc` |
| Approval review UI | `dashboard/src/pages/ApprovalPage.tsx` |

Human approval is required by default (`REQUIRE_HUMAN_APPROVAL=true`). With no SMTP
configured, sends are logged via a console sender so the flow is fully testable.

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
