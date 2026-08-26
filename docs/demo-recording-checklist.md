# Backfill — Demo Recording Checklist

Purpose: capture the required <=5-minute hackathon demo with minimal retakes while preserving Backfill's verified evidence and privacy boundaries.

Target finished runtime: **about 4:15**.

## Before recording

- Close or hide `credentials.json`, `calendar-token.json`, `gmail-token.json`, personal inbox history, private ChatGPT conversations, and unrelated browser tabs.
- Use only the dedicated `Backfill Demo` calendar and the project mailbox.
- Use a **fresh test slot/token** if recording a new live run. Never use the invalid duplicate-email thread from 2026-08-24.
- Keep the public repository open in one tab with `docs/backfill-architecture.svg` and `docs/judge-testing.md` easy to reach.
- Keep the terminal large enough that `OFFER_SENT`, `RESPONSE_RECEIVED`, and `WORKFLOW_FINAL` are readable on video.
- Do not call the 8,500-cent test value revenue.

## Shot order

### 1. Problem / audience — ~0:00–0:35

Say, in plain language:

> A cancellation creates a short window where staff have to find an eligible client, contact them, wait for a reply, avoid double-booking, update the calendar, and confirm the winner. Backfill turns that interruption into a background workflow for appointment-based small businesses.

Visual: one open appointment slot + waitlist concept/title card.

### 2. Architecture — ~0:35–1:05

Show `docs/backfill-architecture.svg`.

Say only the important distinction:

> Strands orchestrates bounded actions, while deterministic Backfill code owns eligibility, waitlist order, idempotency, policy gates, booking verification, terminal state, and recovered-value accounting.

Do not claim AgentCore or production deployment.

### 3. Working end-to-end demo — ~1:05–3:05

If using a fresh capture:

1. Show the dedicated test slot is open.
2. Start `scripts/live_e5_google.py` with a fresh slot/token.
3. Capture exactly one `OFFER_SENT` line.
4. Show the consenting recipient's new Backfill offer only. Avoid exposing unrelated inbox contents.
5. Reply with exactly `ACCEPT` on the first authored line.
6. Return to the terminal and capture `RESPONSE_RECEIVED`.
7. Show `Backfill Demo` receive the booking.
8. Capture terminal `WORKFLOW_FINAL state=COMPLETED_RECOVERED`.
9. Show the confirmation email only.

Verified prior E5 facts for fallback captions/reference:
- offer id `1a03f13d58b58c0a`
- response id `1a03f14b5a0211a2`
- booking event id `bfhtv9s07juncl52g0s896e1j07av75oo9bel6ev1lun4ccqiiu290`
- confirmation id `1a03f14ce96609a6`
- test slot `2026-08-27 16:00–16:30 ET`
- terminal state `COMPLETED_RECOVERED`
- test recovered value `8,500 cents`

### 4. Why this is non-trivial — ~3:05–3:40

Show green CI or the test command output briefly.

Say:

> Backfill does not blindly retry external actions. It uses deterministic identifiers and reconciliation for ambiguous Calendar and Gmail outcomes, fails closed on unexpected replies, and interrupts for real policy exceptions instead of letting the model improvise business rules.

### 5. Close — ~3:40–4:15

Show the public repo.

Say:

> Backfill turns cancelled appointments from a small operational emergency into a background workflow. The verified demo is a consenting real-provider test context, not a production customer deployment or revenue claim.

End with:
- **Backfill**
- **Professional Agents**
- public repository visible

## Privacy / safety cut list

Cut or blur any frame containing:
- OAuth client secrets or token JSON;
- personal inbox messages unrelated to Backfill;
- private ChatGPT conversation content;
- Google account security pages;
- unrelated calendar entries;
- any message from the invalid duplicate-offer attempt.

## Deliverability note

The verified offer previously landed in Gmail Spam. If a fresh demo offer does so again, do not hide the fact or rerun repeatedly to force inbox placement. It is acceptable to show the recipient finding the legitimate transactional message in Spam and marking it **Not spam**, then continuing the demo.

## Done criteria

The video is ready when it is:
- <=5:00;
- public-safe;
- shows an actual working end-to-end recovery;
- states the problem, audience, and why it matters;
- preserves test-context / no-revenue / no-production claim boundaries;
- uploaded publicly to YouTube or Vimeo.
