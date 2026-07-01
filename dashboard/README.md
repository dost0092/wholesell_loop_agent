# LeadGen Dashboard

Premium React dashboard for the TX/FL distressed property lead-gen system.

## Features

- Overview with charts and KPIs
- Searchable, paginated leads table
- One-click TX source fetch
- Approval queue viewer
- Dark / light / system theme
- Command palette (⌘K)
- Toast notifications
- Mobile-responsive layout

## Development

```bash
npm install
npm run dev
```

API requests proxy to `http://localhost:8000` via Vite.

## Build

```bash
npm run build
npm run preview
```

## Environment

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `""` | API base URL (empty = same origin / proxy) |
