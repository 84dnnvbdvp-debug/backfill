# Backfill — Final Devpost Copy

Last grounded against verified project evidence and official Agents for Humans requirements: 2026-08-26.

## Project name

Backfill

## Track

Professional Agents

## One-line pitch

Backfill is a policy-gated AI agent that turns short-notice appointment cancellations into verified bookings by working an eligible waitlist end to end while deterministic code retains authority over consequential business rules.

## Text description

A cancellation creates more work than an empty calendar cell suggests. Someone has to identify eligible waitlist clients, contact them in a fair order, wait for asynchronous replies, avoid duplicate offers and double-booking, update the calendar, confirm the winner, and know whether the slot was actually recovered.

Backfill handles that routine recovery loop for appointment-based small businesses such as salons, spas, groomers, clinics, tutors, and other service providers.

When an opening appears, Backfill deterministically evaluates eligibility and preserves waitlist order. It sends one offer at a time, accepts only an authoritative reply, advances after a decline, and books the first valid acceptance. A successful booking is read back from the provider before the workflow can become `COMPLETED_RECOVERED`. Backfill then sends confirmation, updates workflow state, records an audit trail, and records recovered appointment value only after provider verification.

The architecture deliberately separates agent orchestration from business authority. Strands Agents coordinates bounded actions and agent-facing workflow, while deterministic Backfill code owns eligibility, ordering, policy gates, idempotency, booking verification, terminal-state transitions, and recovered-value accounting. Ambiguous Calendar or Gmail outcomes are reconciled before retry so infrastructure uncertainty does not silently create duplicate bookings or duplicate client messages.

Human judgment remains available where it belongs. A policy exception such as a discount request interrupts the routine path for an owner decision and can then resume deterministically rather than forcing the owner to take the whole workflow back over.

The current public implementation includes a zero-credential judge path and a controlled live Google provider bridge. The zero-credential path installs the pinned Strands SDK, runs the canonical 30-test suite, and exercises the Strands smoke harness without requiring private Google credentials.

On August 26, 2026, a consenting real-provider test completed end to end under the actual Backfill runtime. Backfill sent one offer, received an exact `ACCEPT` reply from the controlled recipient, created and provider-verified the booking in a dedicated Google Calendar, sent confirmation, and reached `COMPLETED_RECOVERED`. Independent post-run Calendar and Gmail readback verified the external booking and confirmation.

That run recorded 8,500 cents of **test appointment value**. It is not a claim of external revenue or a real customer/business recovery. The current live bridge is a controlled one-process demonstration path, not a claim of production deployment or durable restart recovery across separate processes.

One real product-readiness issue also surfaced during the live test: the offer was classified into Gmail Spam. Backfill treats that as a deliverability risk rather than hiding it. A real pilot should use consent-based transactional messaging and an appropriately authenticated business sending identity/provider.

## Why it matters

Small appointment businesses often have valuable short-notice capacity but limited staff attention. Recovering a cancellation is time-sensitive, repetitive, asynchronous, and still policy-sensitive. Backfill turns that small operational emergency into a background responsibility: routine cases progress without constant owner attention, while consequential exceptions still stop for explicit human policy decisions.

## How Strands is used

Strands Agents is the orchestration layer around Backfill's deterministic authority. The project uses the real pinned `strands-agents==1.52.0` SDK. Public CI runs the unit suite and a zero-credential Strands smoke harness, including a normal recovery path and a policy-exception interrupt/resume path.

The design intentionally does not delegate eligibility, waitlist reordering, booking truth, idempotency, or recovered-value accounting to model improvisation.

## Technical highlights

- deterministic waitlist eligibility and ordering;
- one-offer-at-a-time workflow;
- exact authoritative reply handling;
- deterministic external mutation/reconciliation tokens;
- Calendar booking creation plus provider-side verification;
- Gmail send reconciliation before resend;
- replay/crash-boundary hardening for ambiguous outcomes;
- human policy interrupt/resume;
- explicit recovered/unrecovered terminal states;
- recovered-value accounting only after verified booking;
- judge-safe zero-credential test path.

## Verified evidence

- Public repository with MIT license, README, architecture diagram, setup instructions, and judge testing guide.
- Python 3.12 canonical CI with exact `strands-agents==1.52.0`.
- Canonical 30-test suite passes.
- Strands smoke harness prints `STRANDS_SMOKE_OK`.
- Controlled authenticated Calendar and Gmail mutation/readback verified.
- Consenting end-to-end real-provider **test-context** recovery verified under the actual Backfill runtime.
- External revenue remains $0; E6 is not claimed.

## Challenges

The central difficulty was not generating scheduling text. It was defining what “done” means when an agent operates asynchronously across external systems. A send or booking call can fail after the provider has already committed the action. Blind retries can therefore create exactly the duplicate client contact or double-booking the agent is supposed to prevent.

Backfill treats provider truth, idempotency, reconciliation, terminal-state transitions, and business policy as first-class architecture rather than afterthoughts.

A second practical challenge was live-provider identity and permissions. The controlled demo uses separate Google token identities and narrow OAuth scopes so the Calendar account and project mailbox can be authorized without handing the runtime a personal Gmail inbox.

The live test also exposed a non-code problem: transactional deliverability. The offer reached Gmail Spam, which is now explicitly tracked as a product-readiness risk.

## Accomplishments

The project progressed from deterministic fixtures to clean independent Strands execution, authenticated provider integration, and finally a complete real-provider test-context recovery owned by the actual Backfill runtime.

The most important accomplishment is not the existence of a generated message. It is a verifiable terminal state: offer, real reply, booking, provider readback, confirmation, audit, and recovered-value record all agree about the same recovery.

## What we learned

Agent autonomy is more useful when authority is intentionally bounded. Model reasoning is valuable for coordination and interpretation, but commitments that affect people or money benefit from deterministic eligibility, stable ordering, explicit policy, idempotent external actions, and provider verification.

We also learned that “end to end” has to include external reality. A workflow is not complete because an agent says a booking happened; the provider has to agree.

## What's next

The immediate next step is a small consenting real-business pilot after the hackathon submission package is complete. The highest-priority production-readiness work is transactional deliverability and moving from the controlled one-process demo bridge toward durable deployed execution.

Amazon Bedrock AgentCore is not currently claimed as part of the verified implementation.

## Pre-existing work disclosure

Backfill itself was newly created during the hackathon submission period.

The project reused **architectural concepts** explored in an earlier internal prototype called QuietOps, including the general ideas of deterministic policy gating, human interrupt/resume, explicit external-action verification, and keeping consequential authority outside the model. Backfill's cancelled-appointment domain implementation, current application code, Google provider bridge, tests, public repository, demo workflow, and hackathon submission work were built during the submission period.

Standard development tools, open-source libraries, and AI coding assistance were also used as permitted by the hackathon rules.

## Public repository

https://github.com/84dnnvbdvp-debug/backfill

## Judge testing

See `docs/judge-testing.md` in the public repository. The recommended judge path requires no entrant OAuth credentials or personal resources.

## Architecture

See `docs/backfill-architecture.svg` in the public repository.

## Demo video

PENDING — public YouTube or Vimeo URL to be inserted after final upload.

## AWS Builder ID

PENDING — enter in the final Devpost form.

## Final claim guardrails

Do not describe the 8,500-cent test appointment value as revenue.
Do not describe the verified E5 run as a real customer/business recovery.
Do not claim production deployment, AgentCore deployment, or durable cross-process restart recovery unless those are independently added and verified before submission.
