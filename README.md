# TX/FL Distressed Property Lead-Gen System

> **Project location:** `d:\Personal\tx_fl_leadgen`  
> Production-grade lead generation for **Texas and Florida** distressed properties.

## Current status: Phase 1 + Premium Dashboard

| Component | Status |
|-----------|--------|
| TX Lead Finder (Harris, Dallas, Tarrant) | Done |
| Premium React Dashboard | Done |
| API auth, pagination, rate limiting | Done |
| FL connectors | Phase 2 |
| Skip trace / AI / Outreach | Phase 3+ |

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
