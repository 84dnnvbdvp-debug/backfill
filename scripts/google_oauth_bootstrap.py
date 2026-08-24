from __future__ import annotations

import argparse
import os
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from backfill.live_google import CALENDAR_SCOPES, GMAIL_SCOPES


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create/refresh a local Google OAuth token for Backfill live-provider tests."
    )
    parser.add_argument("provider", choices=("calendar", "gmail"))
    parser.add_argument("--client", default="credentials.json")
    parser.add_argument("--token", default=None)
    args = parser.parse_args()

    scopes = CALENDAR_SCOPES if args.provider == "calendar" else GMAIL_SCOPES
    token_path = Path(args.token or f"{args.provider}-token.json")
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(args.client, scopes)
        creds = flow.run_local_server(port=0)

    token_path.write_text(creds.to_json(), encoding="utf-8")
    try:
        os.chmod(token_path, 0o600)
    except OSError:
        pass
    print(f"AUTHORIZED provider={args.provider} token={token_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
