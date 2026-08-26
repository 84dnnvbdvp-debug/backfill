# Backfill — Hackathon Presentation Plan

Last checked against the official Agents for Humans Devpost overview/rules: 2026-08-26.

Current intended track: **Professional Agents**. Devpost describes this track as agents that make professionals, makers, creators, or small-business owners dramatically better at work they already do by taking on repetitive, judgment-heavy tasks.

Official overview: https://agentsforhumans.devpost.com/
Official rules: https://agentsforhumans.devpost.com/rules

## Submission description draft

Backfill is a policy-gated cancelled-appointment recovery agent for appointment-based small businesses. When a cancellation opens a slot, Backfill works through an eligible waitlist in deterministic order, sends one offer at a time, accepts only an authoritative response, books the first valid acceptance, verifies the provider-side booking, sends confirmation, and records the recovered value.

The Strands layer provides orchestration and bounded tool use, while deterministic application code owns eligibility, waitlist order, policy gates, idempotency, booking verification, terminal state, and accounting. That separation is deliberate: Backfill should run quietly in the background, but it should not improvise on the rules that decide who gets contacted, whether a slot is still valid, or whether a booking really happened.

Backfill is aimed at salons, spas, groomers, clinics, and other appointment businesses that lose revenue and staff attention when cancellations create short-notice gaps. Instead of making an owner manually scan a waitlist, send messages, interpret replies, update the calendar, and reconcile failures, Backfill handles the routine path end to end and surfaces only genuine policy decisions.

## Five-minute video target

Target final runtime: **about 4:15**, leaving margin under Devpost's five-minute maximum.

### 0:00–0:35 — Problem / audience / why it matters

Show one simple cancelled slot and a waitlist.

Voiceover points:
- A cancellation is not just an empty calendar cell; it creates a short window in which staff have to find an eligible client, contact them, wait for a reply, avoid double-booking, and update everyone.
- The target user is an appointment-based small business where that recovery work is repetitive but still policy-sensitive.
- Backfill's job is to handle the routine recovery path without requiring the owner to babysit another app.

### 0:35–1:05 — Architecture in one screen

Show `docs/backfill-architecture.svg`.

Explain only the distinction that matters:
- Strands orchestrates bounded actions.
- Deterministic Backfill code owns eligibility, ordering, idempotency, booking verification, terminal state, and recovered-value accounting.
- Gmail and Calendar sit behind adapters with reconciliation paths for ambiguous provider outcomes.

Do not claim AgentCore or production deployment unless that has actually been added and independently verified before recording.

### 1:05–3:05 — Fresh end-to-end E5 demo

Use a **new dedicated test slot and new tracking token**, never the invalid duplicate-email thread from 2026-08-24.

The visible sequence should be:
1. Start with one open slot and one or more controlled eligible waitlist candidates.
2. Launch the real `scripts/live_e5_google.py` runtime.
3. Show Backfill sending exactly one offer from the project mailbox.
4. From the consenting test recipient, reply with exactly `ACCEPT` on the first authored line.
5. Return to the runtime and show it detect that authoritative response.
6. Show the dedicated `Backfill Demo` calendar receive the booking.
7. Show provider-side verification succeed.
8. Show the confirmation message sent.
9. End on the terminal workflow/audit output showing one winner and recovered-value accounting.

The runtime must own the workflow. Do not use conversational ChatGPT connector calls to simulate any of these steps.

### 3:05–3:40 — Why the implementation is non-trivial

Use one concise proof point rather than a tour of every test:
- deterministic event/message tokens prevent silent duplicate work,
- ambiguous Gmail/Calendar outcomes are reconciled rather than blindly retried,
- unexpected reply text fails closed,
- owner-policy exceptions interrupt the routine path instead of being improvised by the agent.

A brief terminal shot of the clean test suite or CI result can support this section, but it should not replace the working demo.

### 3:40–4:15 — Close / impact

Restate the product in practical terms:
- Backfill turns a cancellation from a small emergency into a background workflow.
- It is designed to recover useful appointment capacity while preserving explicit business policy and requiring human attention only when a real decision is needed.

Close with the public repository and track name.

## Presentation guardrails

- Do not call mock/fixture recovered value revenue.
- Do not claim E5 until a fresh live run actually completes under the real runtime.
- Do not claim E6 until external revenue is independently verified.
- Do not show OAuth secrets, `credentials.json`, token JSON files, personal inbox content, or private ChatGPT conversation content on screen.
- Use only the dedicated/controlled Google resources authorized for the demo.
- If the final system still uses the one-process live bridge, describe it that way rather than implying durable production deployment across process restarts.

## Remaining human-dependent presentation inputs

These should wait until they are genuinely available rather than being fabricated:
- fresh valid E5 screen recording,
- final AWS Builder ID,
- final YouTube/Vimeo public URL,
- final Devpost project fields,
- any awarded AWS credit amount/status.
