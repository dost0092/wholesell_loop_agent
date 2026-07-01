# TX/FL Distressed Property Lead-Gen System

> **Project location:** `d:\Personal\tx_fl_leadgen`  
> Production-grade lead generation for **Texas and Florida** distressed properties.

## Current status: Phase 5 (full pipeline through email outreach)

| Component | Status |
|-----------|--------|
| TX Lead Finder (Harris, Dallas, Tarrant) | Done |
| FL Lead Finder (Miami-Dade, Broward, Hillsborough) | Done |
| Premium React Dashboard | Done |
| API auth, pagination, rate limiting | Done |
| **AI deal scoring (Phase 3)** | **Done** |
| **Owner discovery — skip trace + LLC lookup (Phase 4)** | **Done** |
| **Contact validation — MX, phone type, DNC (Phase 5)** | **Done** |
| **Email outreach — draft, human approval, compliant send (Phase 5)** | **Done** |

Runs end-to-end with **zero external API keys** using built-in heuristic scoring,
mock skip-trace/entity providers (clearly flagged as synthetic), and a console
email sender. Set `ANTHROPIC_API_KEY`, `SKIP_TRACE_API_KEY`, `OPENCORPORATES_API_KEY`,
and SMTP creds in `.env` to switch on the real providers — no code changes.

### Lead pipeline

```
Fetch → Score (AI) → Trace owner (skip trace + LLC) → Validate contacts
      → Draft email → Human approval → Compliant send
```

Per-lead endpoints: `POST /api/leads/{id}/score | trace | validate | draft | pipeline`.
Approval endpoints: `POST /api/approval-queue/{id}/approve | reject | send`.
Every send is gated by `app/compliance/gates.py` (approval required + DNC scrub).

## Quick start

### Backend only (no Docker)

```bash
cd backend
pip install -r requirements.txt
pytest
python -m app.cli
```

### Full stack (recommended)

```bash
cp .env.example .env
docker compose up --build
```

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:5173 |
| API docs | http://localhost:8000/docs |
| Health | http://localhost:8000/api/health |

### Dashboard (local dev)

```bash
cd dashboard
npm install
npm run dev
```

## API endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/api/health` | No | Health + DB status |
| GET | `/api/sources` | No | List county connectors |
| POST | `/api/sources/fetch-tx` | Yes | Fetch + persist TX leads |
| POST | `/api/sources/fetch-fl` | Yes | Fetch + persist FL leads |
| POST | `/api/sources/fetch-all` | Yes | Fetch + persist TX + FL leads |
| GET | `/api/leads` | Yes | Paginated leads (`?search=&county=&page=`) |
| GET | `/api/leads/{id}` | Yes | Lead detail |
| GET | `/api/stats/leads` | Yes | Dashboard aggregates |
| GET | `/api/approval-queue` | Yes | Pending outreach approvals |

Set `API_KEY` in `.env` and configure the same key in **Settings** in the dashboard.

## Production deployment

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

See [ARCHITECTURE.md](./ARCHITECTURE.md) for system design.

## Project layout

```
tx_fl_leadgen/
├── dashboard/          # React + Vite premium UI
├── backend/            # FastAPI + SQLAlchemy
├── docker-compose.yml
├── ARCHITECTURE.md
└── PHASES.md
```
