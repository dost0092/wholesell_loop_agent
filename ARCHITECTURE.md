# Architecture

## System overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  React Dashboard │────▶│  FastAPI Backend  │────▶│  Postgres+PostGIS│
│  (Vite, port 5173)│     │  (port 8000)      │     │  (port 5432)     │
└─────────────────┘     └────────┬─────────┘     └─────────────────┘
                                   │
                          ┌────────▼─────────┐
                          │  TX County Sites  │
                          │  Harris, Dallas,  │
                          │  Tarrant          │
                          └──────────────────┘
```

## Layers

| Layer | Location | Responsibility |
|-------|----------|----------------|
| UI | `dashboard/src/` | Premium React SPA — overview, leads, sources, approval, settings |
| API | `backend/app/api/` | REST endpoints, pagination, auth |
| Services | `backend/app/services/` | Business logic (ingestion, future scoring) |
| Sources | `backend/app/sources/` | County-specific data connectors |
| Adapters | `backend/app/adapters/` | Swappable interfaces (skip trace, email, SMS) |
| Data | `backend/app/db/` | SQLAlchemy models + Alembic migrations |
| Compliance | `backend/app/compliance/` | DNC + human approval gates |

## Lead pipeline (planned full flow)

1. **Fetch** — County connectors pull public distressed property records
2. **Ingest** — Dedup and persist to `leads` table
3. **Score** — AI ranks deals (Phase 3)
4. **Skip trace** — Find owner contact info (Phase 4)
5. **Draft** — AI writes outreach messages (Phase 5)
6. **Approve** — Human reviews in approval queue
7. **Send** — SMTP/Twilio with compliance gates
8. **Track** — Inbound replies via IMAP

## Security model

- **API key** (`X-API-Key` header) protects write and sensitive read endpoints
- **Health** and **sources list** remain public for monitoring
- **Rate limiting** via SlowAPI (120 req/min default)
- **Security headers** on all responses
- **Human approval** required before any outbound message

## Deployment

- **Development**: `docker compose up` — hot reload on API + Vite dev server
- **Production**: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up` — multi-worker API + nginx dashboard

## Database schema

Core tables: `leads`, `owners`, `contacts`, `messages`, `approval_queue`, `dnc_list`, `users`

See `backend/app/db/models.py` for the full lead lifecycle status enum.
