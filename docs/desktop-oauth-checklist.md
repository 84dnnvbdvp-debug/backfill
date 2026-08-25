# Backfill — One-Time Desktop OAuth Checkpoint

This is the only planned desktop-heavy checkpoint for the controlled live Google test. Everything below is setup; it does **not** send an email or book an appointment by itself.

## Before starting

- Use the desktop that will run Backfill locally.
- Have access to the Google account that owns the **Backfill Demo** calendar.
- Have access to the **One Bill project Gmail** account.
- Do **not** paste OAuth secrets or token files into ChatGPT, email, or GitHub.

## Part A — Create the Google app identity

1. Open Google Cloud Console and select or create a project for Backfill.
2. Open **APIs & Services / API Library** and enable:
   - **Google Calendar API**
   - **Gmail API**
3. Open **Google Auth Platform**. If this project has not been configured before, click **Get started** and name the app `Backfill`.
4. Keep the app in testing/development use for this controlled demo. Add only the Google accounts that need to authorize the test if Google asks for test users.
5. Open **Google Auth Platform → Clients → Create client**.
6. Choose **Desktop app** as the application type.
7. Name it `Backfill Desktop Test` and create it.
8. Download the OAuth client JSON immediately and save it as `credentials.json` in the local Backfill repository folder.

Google may show a client secret as part of this download. Treat the downloaded file like a password. The repository's `.gitignore` is configured so `credentials.json` and token files are not committed.

## Part B — Prepare Backfill locally

From a terminal opened in the Backfill repository folder:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-live.txt
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

## Part C — Authorize the dedicated calendar account

Run:

```bash
PYTHONPATH=. python scripts/google_oauth_bootstrap.py calendar --token calendar-token.json
```

A Google browser permission screen opens. Sign in with the account that owns **Backfill Demo** and approve the requested Calendar permission. The script saves `calendar-token.json` locally.

## Part D — Authorize the project Gmail account

Run:

```bash
PYTHONPATH=. python scripts/google_oauth_bootstrap.py gmail --token gmail-token.json
```

When the Google browser permission screen opens, sign in with the **One Bill project Gmail** account, not the personal Gmail account. Approve the requested Gmail permissions. The script saves `gmail-token.json` locally.

## Stop here

At this point the authorization checkpoint is complete. Do **not** manually send a test offer or create a new appointment. Return to the Backfill conversation and run the fresh E5 test only with a new slot/token so the actual Backfill runtime owns offer → reply → booking → verification → confirmation.

## What should exist locally afterward

- `credentials.json` — identifies the Backfill OAuth client.
- `calendar-token.json` — permission for the dedicated calendar account.
- `gmail-token.json` — permission for the One Bill project mailbox.

All three remain local and must stay out of GitHub.
