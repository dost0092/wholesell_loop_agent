from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    secret_key: str = "dev-secret-change-me"
    api_key: str = ""
    require_human_approval: bool = True
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    rate_limit_per_minute: int = 60

    database_url: str = "sqlite:///./data/leadgen.db"

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_name: str = ""
    smtp_from_email: str = ""
    smtp_use_tls: bool = True
    smtp_daily_limit: int = 25
    smtp_send_delay_min_sec: int = 30
    smtp_send_delay_max_sec: int = 120
    canspam_physical_address: str = ""

    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    imap_user: str = ""
    imap_password: str = ""

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    skip_trace_provider: str = "batchdata"
    skip_trace_api_key: str = ""
    skip_trace_api_url: str = "https://api.batchdata.com/api/v1/property/skip-trace"

    opencorporates_api_key: str = ""

    top_n_per_state: int = 10
    target_states: str = "TX,FL"
    tx_counties: str = "Harris,Dallas,Tarrant"
    fl_counties: str = "Miami-Dade,Broward,Hillsborough"

    scheduler_enabled: bool = False
    scheduler_cron_hour: int = 7
    scheduler_cron_minute: int = 0
    scheduler_timezone: str = "America/Chicago"

    # Email provider selection: console | smtp | gmail_api
    email_provider: str = "console"

    # Gmail API (OAuth 2.0) — preferred over SMTP for production sending
    google_client_id: str = ""
    google_client_secret: str = ""
    google_refresh_token: str = ""
    sender_email: str = ""
    email_sender_name: str = ""

    # Daily email scheduler
    email_scheduler_enabled: bool = False
    email_timezone: str = "America/Chicago"
    emails_per_day: int = 10
    email_start_time: str = "09:00"
    email_end_time: str = "18:00"
    email_interval_minutes: int = 60
    email_jitter_min_minutes: int = 5
    email_jitter_max_minutes: int = 10
    email_max_retries: int = 5
    email_retry_base_seconds: int = 60

    @property
    def target_state_list(self) -> list[str]:
        return [s.strip().upper() for s in self.target_states.split(",") if s.strip()]

    @property
    def tx_county_list(self) -> list[str]:
        return [c.strip() for c in self.tx_counties.split(",") if c.strip()]

    @property
    def fl_county_list(self) -> list[str]:
        return [c.strip() for c in self.fl_counties.split(",") if c.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"

    @property
    def gmail_api_configured(self) -> bool:
        return bool(
            self.google_client_id
            and self.google_client_secret
            and self.google_refresh_token
            and self.sender_email
        )

    @property
    def email_start_hour_minute(self) -> tuple[int, int]:
        parts = self.email_start_time.strip().split(":")
        return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0


@lru_cache
def get_settings() -> Settings:
    return Settings()
