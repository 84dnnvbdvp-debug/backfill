from __future__ import annotations

import argparse
from datetime import datetime

from backfill.application import BackfillApplication
from backfill.domain import Candidate, Opening, Repo, Workflow
from backfill.google_adapters import GoogleCalendarBookingAdapter, GmailOutboxAdapter
from backfill.live_google import (
    CALENDAR_SCOPES,
    GMAIL_SCOPES,
    DedicatedCalendarSlotProbe,
    GmailReplyPoller,
    SlotWindow,
    build_google_service,
)


def _subject(message_type: str) -> str:
    if message_type.startswith("offer:"):
        return "Backfill appointment opening — reply ACCEPT or DECLINE"
    if message_type.startswith("confirmation:"):
        return "Backfill appointment confirmed"
    return f"Backfill {message_type}"


def _body_factory(start: str, end: str):
    def build(message_type: str, token: str) -> str:
        if message_type.startswith("offer:"):
            return (
                "A one-off Backfill test appointment is available.\n\n"
                f"Start: {start}\nEnd: {end}\n\n"
                "Reply with exactly one word on the first line: ACCEPT or DECLINE.\n"
                "No signup or mailing list is involved.\n\n"
                f"Tracking token: {token}\n"
            )
        if message_type.startswith("confirmation:"):
            return (
                "Backfill booked and provider-verified the test appointment.\n\n"
                f"Start: {start}\nEnd: {end}\n\n"
                f"Tracking token: {token}\n"
            )
        return f"Backfill {message_type}\n\nTracking token: {token}\n"

    return build


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run one live Backfill offer->reply->booking->confirmation workflow."
    )
    parser.add_argument("--calendar-id", required=True)
    parser.add_argument("--calendar-token", default="calendar-token.json")
    parser.add_argument("--gmail-token", default="gmail-token.json")
    parser.add_argument("--gmail-sender", required=True)
    parser.add_argument("--candidate-email", required=True)
    parser.add_argument("--slot-id", required=True)
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--value-cents", type=int, default=8500)
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    parser.add_argument("--timeout-seconds", type=float, default=900.0)
    args = parser.parse_args()

    # Fail early on malformed timestamps before touching providers.
    datetime.fromisoformat(args.start)
    datetime.fromisoformat(args.end)

    calendar_service = build_google_service(
        api="calendar",
        version="v3",
        token_path=args.calendar_token,
        scopes=CALENDAR_SCOPES,
    )
    gmail_service = build_google_service(
        api="gmail",
        version="v1",
        token_path=args.gmail_token,
        scopes=GMAIL_SCOPES,
    )
    profile = gmail_service.users().getProfile(userId="me").execute()
    actual_sender = str(profile.get("emailAddress", "")).lower()
    if actual_sender != args.gmail_sender.lower():
        raise RuntimeError(
            f"gmail token account mismatch: expected {args.gmail_sender}, got {actual_sender}"
        )

    slot = SlotWindow(args.slot_id, args.start, args.end)
    probe = DedicatedCalendarSlotProbe(
        calendar_service, calendar_id=args.calendar_id, slot=slot
    )
    calendar = GoogleCalendarBookingAdapter(
        calendar_service,
        calendar_id=args.calendar_id,
        slot_probe=probe,
        summary_factory=lambda slot_id, candidate_id: (
            f"Backfill recovered test slot — {candidate_id}"
        ),
    )
    messages = GmailOutboxAdapter(
        gmail_service,
        sender=args.gmail_sender,
        recipient_for_type=lambda _message_type: args.candidate_email,
        subject_for_type=_subject,
        body_for_type=_body_factory(args.start, args.end),
    )

    opening = Opening(
        args.slot_id,
        "google-calendar",
        "backfill-live-test",
        args.start,
        args.end,
        args.value_cents,
    )
    candidate = Candidate(
        "C1",
        "backfill-live-test",
        True,
        "2026-08-24T00:00:00-04:00",
        consent=True,
        active=True,
        conflict=False,
    )
    repo = Repo(
        opening=opening,
        candidates={"C1": candidate},
        workflow=Workflow(f"live-{args.slot_id}", args.slot_id),
    )
    app = BackfillApplication(repo, calendar, messages)

    wf = app.start()
    offer = repo.offers.get("offer-c1")
    if offer is None or offer.message_id is None:
        raise RuntimeError("offer was not durably reconciled to one Gmail message")
    print(f"OFFER_SENT message_id={offer.message_id} state={wf.state.value}")

    poller = GmailReplyPoller(
        gmail_service,
        expected_sender=args.candidate_email,
        poll_seconds=args.poll_seconds,
        timeout_seconds=args.timeout_seconds,
    )
    response, response_id = poller.wait_for_reply(sent_message_id=offer.message_id)
    print(f"RESPONSE_RECEIVED response={response} message_id={response_id}")

    wf = app.process_response(offer.offer_id, response, response_id)
    print(
        "WORKFLOW_FINAL "
        f"state={wf.state.value} booking_event_id={wf.booking_event_id} "
        f"winner={wf.winner_candidate_id} recovered_value_cents={wf.recovered_value_cents}"
    )
    print("AUDIT")
    for entry in repo.audit:
        print(entry)

    if wf.state.value != "COMPLETED_RECOVERED":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
