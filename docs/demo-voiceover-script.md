# Backfill — Demo Voiceover Script

Target spoken runtime: about 4:05–4:25 at a natural pace. Keep the final video under 5:00.

## 0:00–0:35 — Problem

A cancelled appointment looks like an empty box on a calendar, but for a small appointment business it creates a time-sensitive job. Someone has to find an eligible client, contact them, wait for a reply, avoid double-booking, update the calendar, and confirm the winner.

Backfill turns that interruption into a background workflow. It is built for appointment-based businesses like salons, spas, groomers, clinics, tutors, and other service providers where short-notice capacity matters but staff attention is limited.

## 0:35–1:05 — Architecture

The important design choice is this split.

Strands Agents orchestrates bounded actions and the agent-facing workflow. Deterministic Backfill code retains authority over eligibility, waitlist order, policy gates, idempotency, booking verification, terminal state, and recovered-value accounting.

That means the agent can coordinate work without improvising the business rules that decide who gets contacted, whether a booking is real, or when value can be counted.

## 1:05–2:55 — Working end-to-end demo

Here is the actual live recovery path.

We start with a dedicated test appointment slot and a controlled consenting recipient.

The real Backfill runtime starts the workflow and sends exactly one offer from the project mailbox. The workflow moves into a waiting state rather than assuming the client accepted.

The recipient replies with an exact `ACCEPT`.

Backfill detects that authoritative response and attempts the booking. It does not mark the slot recovered merely because a booking call was made. It reads provider state back from Google Calendar and verifies that the appointment actually exists.

Once verification succeeds, Backfill sends the confirmation and completes the workflow as `COMPLETED_RECOVERED`.

In the verified test shown here, the external Calendar booking and Gmail confirmation were also read back independently after the runtime finished.

The workflow records an appointment value of eighty-five dollars, but this is test workflow value. It is not project revenue and this is not being presented as a real customer deployment.

## 2:55–3:35 — Why this is non-trivial

The difficult part is not writing a scheduling email. It is staying correct when real providers are asynchronous and uncertain.

A Calendar request can time out after an event was already created. An email send can fail after the provider accepted the message. Blind retries can create duplicate bookings or duplicate client contact.

Backfill uses deterministic identifiers and reconciliation before retry. Unexpected reply text fails closed. Policy exceptions, such as a discount request, interrupt for an explicit owner decision instead of letting the model invent business policy.

The public repository includes a thirty-test canonical suite and a zero-credential Strands smoke harness so judges can verify the core behavior without our private Google credentials.

## 3:35–4:15 — Close

Backfill is designed to turn a cancellation from a small operational emergency into a background responsibility.

Routine recovery work can progress end to end, while consequential decisions remain bounded by explicit policy and human authority.

What is verified today is a consenting real-provider test-context recovery under the actual Backfill runtime, with provider-side booking verification and confirmation.

The current live bridge is a controlled one-process demonstration path, not a production deployment. One real readiness issue also surfaced: the offer landed in Gmail Spam, so transactional deliverability is a priority for a real business pilot.

Backfill is submitted to the Professional Agents track.

The public repository contains the source, MIT license, architecture diagram, setup instructions, evidence boundaries, and judge testing guide.
