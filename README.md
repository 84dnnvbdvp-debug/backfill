# Backfill

Backfill is a policy-gated cancelled-appointment recovery agent. Deterministic application code owns eligibility, waitlist ordering, policy gates, idempotency, booking verification, terminal state, and recovered-value accounting; the Strands layer provides orchestration and bounded tool use around that deterministic core.

## What it does

1. Detect an appointment opening or cancellation.
2. Select the next eligible waitlist client deterministically.
3. Send one offer at a time and track the first authoritative response.
4. Book the first valid acceptance and verify the provider-side booking.
5. Send/track confirmation, update waitlist state, audit the outcome, and record recovered value.
6. Interrupt for owner policy decisions such as discount exceptions, then resume deterministically.

The application includes explicit reconciliation paths for ambiguous Calendar/Gmail outcomes and process-crash replay boundaries so retries do not silently duplicate bookings or client messages.

## Architecture

See [`docs/backfill-architecture.svg`](docs/backfill-architecture.svg). The diagram separates Strands orchestration from the deterministic Backfill authority and shows the Calendar/Gmail adapter boundary. No AgentCore or Bedrock deployment is claimed by this repository.

## Canonical setup

The canonical proof path uses Python 3.12 and pins Strands exactly for reproducibility.

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-ci.txt
```

## Tests

```bash
PYTHONPATH=. python -m unittest discover -s tests -v
```

The canonical suite currently contains 30 tests: 16 application/hardening tests, 10 mocked Google-adapter tests, and 4 zero-credential live-bridge parser/slot-gate tests.

## Zero-credential Strands smoke harness

```bash
PYTHONPATH=. python scripts/strands_smoke_harness.py
```

The smoke harness imports the real installed `strands-agents==1.52.0` SDK but uses local in-memory Calendar/message doubles. It exercises a happy-path recovery and a policy-exception interrupt/resume flow without touching real Google resources or requiring credentials.

## Live Google provider bridge

The live path intentionally keeps OAuth material local and out of Git. It is for explicitly authorized demo resources only.

Install the pinned live dependencies:

```bash
python -m pip install -r requirements-live.txt
```

Create a Google OAuth **Desktop app** client in a Google Cloud project with the Gmail and Calendar APIs enabled, download its JSON as `credentials.json`, then authorize the two provider identities separately as needed:

```bash
PYTHONPATH=. python scripts/google_oauth_bootstrap.py calendar --token calendar-token.json
PYTHONPATH=. python scripts/google_oauth_bootstrap.py gmail --token gmail-token.json
```

The requested scopes are deliberately narrower than full mailbox/calendar control:
- Calendar: `calendar.events.owned`
- Gmail: `gmail.readonly` + `gmail.send`

`credentials.json`, `*-token.json`, and `.backfill-live/` are ignored by Git and must never be committed.

A one-process live test runner is provided at `scripts/live_e5_google.py`. It lets the real `BackfillApplication` own offer idempotency, Gmail reconciliation, deterministic reply classification, Calendar booking/verification, confirmation, and terminal completion. It fails closed on unexpected reply text and verifies that the Gmail token belongs to the explicitly named sender before sending.

This live runner is a controlled test bridge, not a claim of production deployment or durable crash recovery across a process restart.

## Real-provider boundary

Real provider mutation/readback must be performed only against explicitly authorized dedicated/controlled demo resources. Fixture/mock recovered value is not business revenue. Private ChatGPT conversation content must never be used as outbound email material unless the user explicitly identifies and authorizes that specific content for external sharing.

## License

MIT. See [`LICENSE`](LICENSE).
