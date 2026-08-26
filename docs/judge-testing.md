# Backfill — Judge Testing Instructions

These instructions are designed so judges can verify the repository safely without needing Backfill's private OAuth credentials, personal accounts, or production resources.

## 1. Zero-credential verification (recommended)

Requirements:
- Python 3.12
- public repository checkout

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-ci.txt
PYTHONPATH=. python -m unittest discover -s tests -v
PYTHONPATH=. python scripts/strands_smoke_harness.py
```

Expected result:
- 30 tests pass.
- smoke harness prints `STRANDS_SMOKE_OK`.

This verifies the deterministic application/hardening suite, mocked Google adapter behavior, live-bridge parser/slot gates, and execution against the real pinned `strands-agents==1.52.0` SDK.

## 2. What the public smoke harness does

The smoke harness uses the real installed Strands SDK but local in-memory provider doubles. It exercises:
- a normal cancelled-slot recovery path;
- a policy-exception interrupt/resume path;
- deterministic Backfill application authority around the agent orchestration layer.

It intentionally does not require Google credentials.

## 3. Optional live Google provider reproduction

The repository includes a controlled live bridge for judges who want to reproduce provider behavior with **their own** dedicated Google test resources.

Never use Backfill's private credentials or the entrant's personal resources.

Install:

```bash
python -m pip install -r requirements-live.txt
```

Create a Google OAuth Desktop client in a Google Cloud project with Calendar and Gmail APIs enabled. Keep `credentials.json`, `calendar-token.json`, and `gmail-token.json` local; `.gitignore` excludes them.

Bootstrap narrow scopes:

```bash
PYTHONPATH=. python scripts/google_oauth_bootstrap.py calendar --token calendar-token.json
PYTHONPATH=. python scripts/google_oauth_bootstrap.py gmail --token gmail-token.json
```

The live bridge requests:
- Calendar: `calendar.events.owned`
- Gmail: `gmail.readonly` + `gmail.send`

Use only a dedicated test calendar and a consenting test recipient. Then run `scripts/live_e5_google.py` with a fresh slot and your own account identifiers.

## 4. Evidence boundary

Verified entrant evidence:
- clean-runtime Strands + tests: E3;
- authenticated Calendar/Gmail mutation/readback: E4;
- consenting end-to-end real-provider **test-context** recovery: E5.

Not claimed:
- production deployment;
- durable restart recovery across separate live-runner processes;
- a real customer/business recovery;
- external revenue.

The 8,500-cent recovered value shown in the verified E5 run is test workflow value only.

## 5. Privacy and safety

- OAuth credentials/tokens are never committed.
- The live runtime can use separate Google identities for Calendar and Gmail.
- Private ChatGPT conversation content is prohibited from outbound email unless explicitly selected and authorized for that exact purpose.
- Dedicated demo resources are used instead of the entrant's primary/Family calendars.
- Unexpected reply text fails closed; only an exact first authored `ACCEPT` or `DECLINE` is accepted by the live reply poller.

## 6. Known deliverability note

In the verified E5 test, the offer landed in the consenting recipient's Gmail Spam folder. The recipient found it and replied, and the runtime completed successfully. This is treated as a real product-readiness risk rather than hidden or promoted as production-ready deliverability.
