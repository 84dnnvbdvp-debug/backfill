# Backfill — Hackathon Presentation Plan

Last checked against the official Agents for Humans Devpost overview/rules: 2026-08-26.

Current intended track: **Professional Agents**.

Official overview: https://agentsforhumans.devpost.com/
Official rules: https://agentsforhumans.devpost.com/rules

## Submission description draft

Backfill is a policy-gated cancelled-appointment recovery agent for appointment-based small businesses. When a cancellation opens a slot, Backfill works through an eligible waitlist in deterministic order, sends one offer at a time, accepts only an authoritative response, books the first valid acceptance, verifies the provider-side booking, sends confirmation, and records the recovered appointment value.

The Strands layer provides orchestration and bounded tool use, while deterministic application code owns eligibility, waitlist order, policy gates, idempotency, booking verification, terminal state, and recovered-value accounting. That separation is deliberate: Backfill can run quietly in the background without improvising on the rules that decide who gets contacted, whether a slot is still valid, or whether a booking really happened.

Backfill is aimed at salons, spas, groomers, clinics, and other appointment businesses that lose revenue opportunity and staff attention when cancellations create short-notice gaps. Instead of making an owner manually scan a waitlist, send messages, interpret replies, update the calendar, and reconcile failures, Backfill handles the routine path end to end and surfaces only genuine policy decisions.

A consenting real-provider test has now completed end to end under the actual Backfill runtime: one offer was sent, the recipient replied `ACCEPT`, Backfill created and verified the dedicated Google Calendar booking, sent the confirmation, and reached `COMPLETED_RECOVERED`. The recorded 8,500-cent appointment value is test workflow value, not project revenue.

## Five-minute video target

Target final runtime: **about 4:15**, leaving margin under Devpost's five-minute maximum.

### 0:00–0:35 — Problem / audience / why it matters

Show one simple cancelled slot and a waitlist.

Voiceover:
- A cancellation creates a short window in which staff have to find an eligible client, contact them, wait for a reply, avoid double-booking, and update everyone.
- The target user is an appointment-based small business where that recovery work is repetitive but still policy-sensitive.
- Backfill handles the routine recovery path without requiring the owner to babysit another app.

### 0:35–1:05 — Architecture in one screen

Show `docs/backfill-architecture.svg`.

Explain only the distinction that matters:
- Strands orchestrates bounded actions.
- Deterministic Backfill code owns eligibility, ordering, idempotency, booking verification, terminal state, and recovered-value accounting.
- Gmail and Calendar sit behind adapters with reconciliation paths for ambiguous provider outcomes.

Do not claim AgentCore, production deployment, or durable multi-process restart recovery unless independently added and verified before recording.

### 1:05–3:05 — Verified end-to-end E5 test

Use the verified 2026-08-26 test-context run, or repeat it only if recording requires a fresh clean capture. Never use the invalid duplicate-email thread from 2026-08-24.

Visible sequence:
1. Show the dedicated test slot and controlled eligible candidate.
2. Launch the real `scripts/live_e5_google.py` runtime.
3. Show Backfill send exactly one offer from the project mailbox.
4. Show the consenting recipient reply with exactly `ACCEPT`.
5. Show the runtime print `RESPONSE_RECEIVED`.
6. Show the dedicated `Backfill Demo` calendar contain the recovered booking.
7. Show provider-side verification/terminal runtime output.
8. Show the confirmation message.
9. End on `WORKFLOW_FINAL state=COMPLETED_RECOVERED` and the audit/recovered-value record.

Verified run facts available for captioning:
- offer message id: `1a03f13d58b58c0a`
- accepted response id: `1a03f14b5a0211a2`
- booking event id: `bfhtv9s07juncl52g0s896e1j07av75oo9bel6ev1lun4ccqiiu290`
- confirmation message id: `1a03f14ce96609a6`
- test slot: 2026-08-27 16:00–16:30 ET
- terminal state: `COMPLETED_RECOVERED`
- test recovered value: 8,500 cents

Do not display personal OAuth files, tokens, inbox history, or private ChatGPT conversation content.

### 3:05–3:40 — Why the implementation is non-trivial

Use one concise proof point rather than a tour of every test:
- deterministic event/message tokens prevent silent duplicate work,
- ambiguous Gmail/Calendar outcomes are reconciled rather than blindly retried,
- unexpected reply text fails closed,
- owner-policy exceptions interrupt the routine path instead of being improvised by the agent.

A brief terminal shot of the clean 30-test suite or green CI can support this section, but it should not replace the working demo.

### 3:40–4:15 — Close / impact

Restate the product in practical terms:
- Backfill turns a cancellation from a small emergency into a background workflow.
- It is designed to recover useful appointment capacity while preserving explicit business policy and requiring human attention only when a real decision is needed.
- The current proof is a consenting real-provider test context, not a production customer deployment.

Close with the public repository and **Professional Agents** track.

## Deliverability note

The verified offer reached the consenting recipient's Gmail **Spam** folder. That does not invalidate the end-to-end proof, but it is a real product-readiness risk.

Bounded near-term mitigation:
- keep messages transactional, low-volume, and tied to explicit waitlist consent;
- use one consistent sender identity;
- avoid marketing-list behavior, unnecessary links, attachments, or promotional copy;
- for a real business pilot, prefer the business's authenticated sending domain/provider rather than treating a fresh consumer Gmail account as production infrastructure;
- if Gmail misclassifies a legitimate test message, the recipient can mark it **Not spam**, which Google documents as a signal that helps future classification.

Do not run sending campaigns merely to “warm” the account.

## Presentation guardrails

- Do not call test/fixture recovered value revenue.
- E5 may be claimed only as a **consenting real-provider test-context end-to-end completion**.
- Do not imply a real business/customer recovery has occurred.
- Do not claim E6 until external revenue is independently verified.
- Do not show OAuth secrets, `credentials.json`, token JSON files, personal inbox content, or private ChatGPT conversation content on screen.
- Use only dedicated/controlled Google resources authorized for the demo.
- Describe the current live bridge as a controlled one-process demo path, not production restart durability.

## Remaining human-dependent presentation inputs

- record/edit the <=5-minute public demo video;
- upload it publicly to YouTube or Vimeo;
- enter the final AWS Builder ID;
- select Professional Agents in the final Devpost submission;
- submit the final Devpost project;
- record AWS promotional-credit approval if/when actually received.
