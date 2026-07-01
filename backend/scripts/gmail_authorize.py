"""One-time Gmail OAuth authorization script.

Run this once to obtain a refresh token for unattended sending:

    cd backend
    python -m scripts.gmail_authorize

Follow the browser prompt, then copy the printed GOOGLE_REFRESH_TOKEN into .env.
"""

from __future__ import annotations

import sys

from google_auth_oauthlib.flow import InstalledAppFlow

from app.config import get_settings
from app.email.oauth import GMAIL_SCOPES

CLIENT_CONFIG_TEMPLATE = {
    "installed": {
        "client_id": "",
        "client_secret": "",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }
}


def main() -> int:
    settings = get_settings()
    if not settings.google_client_id or not settings.google_client_secret:
        print(
            "ERROR: Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env first.",
            file=sys.stderr,
        )
        return 1

    config = CLIENT_CONFIG_TEMPLATE.copy()
    config["installed"] = config["installed"].copy()
    config["installed"]["client_id"] = settings.google_client_id
    config["installed"]["client_secret"] = settings.google_client_secret

    flow = InstalledAppFlow.from_client_config(config, scopes=GMAIL_SCOPES)
    creds = flow.run_local_server(port=0)

    print("\n=== Gmail OAuth Authorization Complete ===\n")
    print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")
    print(f"SENDER_EMAIL={settings.sender_email or '<your gmail address>'}")
    print("\nAdd these to your .env file. The refresh token does not expire")
    print("unless you revoke access at https://myaccount.google.com/permissions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
