# Gmail Email Sending Module

Production-grade automated email sending for the TX/FL wholesaling loop agent.
Sends **10 highly personalized emails per day** via the **Gmail API (OAuth 2.0)**.

## Architecture

```
backend/app/email/
├── interfaces.py      # EmailProvider abstraction (swappable providers)
├── oauth.py           # OAuth 2.0 credentials + auto-refresh
├── gmail_client.py    # Gmail API transport layer
├── sender.py          # GmailEmailProvider implementation
├── scheduler.py       # APScheduler daily batch + restart recovery
├── dispatch.py        # Orchestrates validate → send → log
├── validator.py       # Pre-send safety checks
├── logger.py          # EmailLog persistence service
├── templates.py       # Professional signature blocks
├── monitoring.py      # Send statistics
└── utils.py           # Hashing, schedule computation

backend/app/agents/email_agent.py   # Personalized content generation
backend/scripts/gmail_authorize.py  # One-time OAuth setup
```

### Data flow

1. **Daily plan** (cron at `EMAIL_START_TIME`) finds up to 10 approved leads.
2. **EmailLog** entries are created with staggered `scheduled_time` values (~1 hour apart ± jitter).
3. **APScheduler** fires one job per email at its scheduled time.
4. Each job runs **validator** → **compliance gate** → **Gmail API send** → **EmailLog update**.
5. On **restart**, `resume_pending()` re-schedules unsent entries — no duplicates.

### Provider abstraction

Business logic depends on `EmailProvider`, not Gmail directly:

```python
class EmailProvider(ABC):
    def send(self, email: OutboundEmail) -> SendResult: ...
```

To swap providers (Brevo, Mailgun, SES), implement `EmailProvider` and update `EMAIL_PROVIDER`.

## Setup

### 1. Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project (or use an existing one).
3. Enable the **Gmail API** (APIs & Services → Library).
4. Create **OAuth 2.0 credentials** (Desktop app type).
5. Copy the Client ID and Client Secret.

### 2. Environment variables

Copy `.env.example` to `.env` and set:

```env
EMAIL_PROVIDER=gmail_api
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
SENDER_EMAIL=your.email@gmail.com
EMAIL_SENDER_NAME=Your Name
CANSPAM_PHYSICAL_ADDRESS=123 Main St, Houston, TX 77002

EMAIL_SCHEDULER_ENABLED=true
EMAIL_TIMEZONE=America/Chicago
EMAILS_PER_DAY=10
EMAIL_START_TIME=09:00
EMAIL_INTERVAL_MINUTES=60
EMAIL_JITTER_MIN_MINUTES=5
EMAIL_JITTER_MAX_MINUTES=10
```

### 3. One-time OAuth authorization

```bash
cd backend
pip install -r requirements.txt
python -m scripts.gmail_authorize
```

Follow the browser prompt. Copy the printed `GOOGLE_REFRESH_TOKEN` into `.env`.

The refresh token does not expire unless you revoke access at
[Google Account Permissions](https://myaccount.google.com/permissions).

### 4. Database migration (Postgres)

```bash
cd backend
alembic upgrade head
```

SQLite dev mode creates tables automatically on startup.

### 5. Start the application

```bash
cd backend
uvicorn app.main:app --reload
```

The email scheduler starts automatically when `EMAIL_SCHEDULER_ENABLED=true`.

## Daily sending schedule

With default settings, 10 emails are sent roughly one hour apart:

| Email | Approximate time |
|-------|-----------------|
| #1    | 09:00 AM        |
| #2    | 10:06 AM (±5–10 min jitter) |
| #3    | 11:01 AM        |
| ...   | ...             |
| #10   | ~06:00 PM       |

Jitter is randomized per slot to avoid a predictable pattern.

## Safety checks

Before every send:

- Recipient email format validation
- Non-empty subject and body
- Duplicate lead/message detection
- DNC / opt-out list check
- Bounced address skip
- Compliance gate (human approval required)
- Spam-trigger phrase warning (logged)

Skipped emails are recorded in `EmailLog` with `delivery_status=skipped` and a `skip_reason`.

## Monitoring

```bash
curl -H "X-API-Key: your-key" http://localhost:8000/api/email/stats
```

Returns:

- `total_scheduled`, `total_sent`, `total_failed`, `total_skipped`
- `next_scheduled_email`
- `average_send_duration_ms`
- `retry_total`, `retry_average`

Manual planning trigger:

```bash
curl -X POST -H "X-API-Key: your-key" http://localhost:8000/api/email/plan-today
```

## EmailLog table

Every send attempt is persisted:

| Column | Description |
|--------|-------------|
| `lead_id` | Associated lead |
| `recipient_email` | Normalized recipient |
| `subject` | Email subject |
| `body_hash` | SHA-256 of body (dedup) |
| `scheduled_time` | When send was planned |
| `sent_time` | Actual send timestamp |
| `delivery_status` | scheduled / sent / failed / skipped / retry_pending |
| `gmail_message_id` | Gmail API message ID |
| `retry_count` | Number of retry attempts |
| `error_message` | Failure details |

## Error handling

- **Rate limits (429)**: Exponential backoff, up to `EMAIL_MAX_RETRIES`
- **Expired OAuth token**: Auto-refreshed via refresh token
- **Network failures**: Retryable with backoff
- **Permanent failures**: Marked `failed`, scheduler continues
- **Scheduler isolation**: One failed email never crashes the scheduler

## Testing

```bash
cd backend
pytest tests/test_email.py -v
```

Tests use mocked Gmail API — no real credentials needed.

## Development mode

Without Gmail credentials, the system uses `ConsoleEmailSender` (logs to stdout):

```env
EMAIL_PROVIDER=console
EMAIL_SCHEDULER_ENABLED=false
```

This lets you test the full pipeline without sending real email.
