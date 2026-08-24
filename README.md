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

The canonical suite contains 26 tests: 16 current application/hardening tests and 10 mocked Google-adapter tests.

## Zero-credential Strands smoke harness

```bash
PYTHONPATH=. python scripts/strands_smoke_harness.py
```

The smoke harness imports the real installed `strands-agents==1.52.0` SDK but uses local in-memory Calendar/message doubles. It exercises a happy-path recovery and a policy-exception interrupt/resume flow without touching real Google resources or requiring credentials.

## Real-provider boundary

The repository's Google adapters are designed for authenticated Calendar/Gmail integration, but real provider mutation/readback should be performed only against explicitly authorized dedicated demo resources. Fixture/mock recovered value is not business revenue.

## License

MIT. See [`LICENSE`](LICENSE).
