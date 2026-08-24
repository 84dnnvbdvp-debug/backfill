from __future__ import annotations


import base64
import hashlib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple


from .providers import CalendarBooking, SlotProbe




def deterministic_google_event_id(booking_key: str) -> str:
    """
    Stable Google Calendar event id.


    Google Calendar accepts lowercase base32hex characters (0-9, a-v) and
    lengths from 5 to 1024. A SHA-256 digest gives a fixed, collision-resistant
    value, while the 'bf' prefix keeps Backfill-owned events recognizable.
    """
    digest = hashlib.sha256(booking_key.encode("utf-8")).digest()
    encoded = base64.b32hexencode(digest).decode("ascii").lower().rstrip("=")
    return "bf" + encoded




def _execute(request: Any) -> Dict[str, Any]:
    """Small seam around googleapiclient request.execute() for testability."""
    return request.execute()




class GoogleCalendarBookingAdapter:
    """
    Google Calendar booking adapter with client-created deterministic event IDs.


    `service` is a googleapiclient Calendar v3 service or a compatible test
    double. Slot openness is intentionally supplied by a separate domain probe;
    Calendar is authoritative for the booking mutation, not for waitlist policy.
    """


    def __init__(
        self,
        service: Any,
        *,
        calendar_id: str,
        slot_probe: SlotProbe,
        summary_factory: Optional[Callable[[str, str], str]] = None,
    ):
        self.service = service
        self.calendar_id = calendar_id
        self.slot_probe = slot_probe
        self.summary_factory = summary_factory or (
            lambda slot_id, candidate_id: f"Backfill recovered slot — {candidate_id}"
        )


    def verify_slot_open(self, slot_id: str) -> bool:
        return bool(self.slot_probe.is_open(slot_id))


    @staticmethod
    def _event_to_booking(event: Dict[str, Any]) -> CalendarBooking:
        private = ((event.get("extendedProperties") or {}).get("private") or {})
        return CalendarBooking(
            event_id=event["id"],
            booking_key=private.get("backfill_booking_key", ""),
            slot_id=private.get("backfill_slot_id", ""),
            candidate_id=private.get("backfill_candidate_id", ""),
            start=((event.get("start") or {}).get("dateTime") or ""),
            end=((event.get("end") or {}).get("dateTime") or ""),
        )


    def _get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        try:
            return _execute(
                self.service.events().get(
                    calendarId=self.calendar_id,
                    eventId=event_id,
                )
            )
        except Exception as exc:
            # googleapiclient HttpError is optional here. A compatible double can
            # expose resp.status. Only a not-found result is safely mapped to None.
            status = getattr(getattr(exc, "resp", None), "status", None)
            if status == 404 or exc.__class__.__name__ == "NotFound":
                return None
            raise


    def find_by_booking_key(self, booking_key: str) -> List[CalendarBooking]:
        event_id = deterministic_google_event_id(booking_key)
        event = self._get_event(event_id)
        if not event:
            return []
        booking = self._event_to_booking(event)
        if booking.booking_key != booking_key:
            # A deterministic-ID collision or unrelated preexisting event is a
            # hard ambiguity; caller must not silently overwrite it.
            return [booking]
        return [booking]


    def create_booking(
        self,
        *,
        booking_key: str,
        slot_id: str,
        candidate_id: str,
        start: str,
        end: str,
    ) -> CalendarBooking:
        event_id = deterministic_google_event_id(booking_key)


        # Reconcile first. This makes replay safe and also recovers a prior
        # timeout-after-commit without issuing another insert.
        existing = self._get_event(event_id)
        if existing is not None:
            booking = self._event_to_booking(existing)
            if booking.booking_key != booking_key:
                raise RuntimeError("calendar event id collision")
            return booking


        if not self.verify_slot_open(slot_id):
            raise RuntimeError("slot not open")


        body = {
            "id": event_id,
            "summary": self.summary_factory(slot_id, candidate_id),
            "start": {"dateTime": start},
            "end": {"dateTime": end},
            "extendedProperties": {
                "private": {
                    "backfill_booking_key": booking_key,
                    "backfill_slot_id": slot_id,
                    "backfill_candidate_id": candidate_id,
                }
            },
        }


        try:
            created = _execute(
                self.service.events().insert(
                    calendarId=self.calendar_id,
                    body=body,
                    sendUpdates="none",
                )
            )
            return self._event_to_booking(created)
        except Exception:
            # If the transport failed after the Calendar backend committed,
            # deterministic ID gives us an exact reconciliation read.
            reconciled = self._get_event(event_id)
            if reconciled is not None:
                booking = self._event_to_booking(reconciled)
                if booking.booking_key != booking_key:
                    raise RuntimeError("calendar event id collision after ambiguous insert")
                return booking
            raise


    def verify_booking(
        self,
        *,
        event_id: str,
        booking_key: str,
        slot_id: str,
        candidate_id: str,
        start: str,
        end: str,
    ) -> bool:
        event = self._get_event(event_id)
        if not event:
            return False
        booking = self._event_to_booking(event)
        return (
            booking.event_id == event_id
            and booking.booking_key == booking_key
            and booking.slot_id == slot_id
            and booking.candidate_id == candidate_id
            and booking.start == start
            and booking.end == end
            and event.get("status", "confirmed") != "cancelled"
        )




@dataclass(frozen=True)
class GmailSentMessage:
    message_id: str
    token: str
    message_type: str




class GmailOutboxAdapter:
    """
    Gmail API adapter for Backfill's durable outbox/reconciliation contract.


    Gmail does not expose a caller-chosen provider message id. Therefore this
    adapter embeds a deterministic X-Backfill-Token header and reconciles
    ambiguous sends by searching Sent mail, then verifying the exact header.
    """


    def __init__(
        self,
        service: Any,
        *,
        sender: str,
        recipient_for_type: Callable[[str], str],
        subject_for_type: Optional[Callable[[str], str]] = None,
        body_for_type: Optional[Callable[[str, str], str]] = None,
        user_id: str = "me",
    ):
        self.service = service
        self.sender = sender
        self.recipient_for_type = recipient_for_type
        self.subject_for_type = subject_for_type or (
            lambda message_type: f"Backfill {message_type}"
        )
        self.body_for_type = body_for_type or (
            lambda message_type, token: f"Backfill {message_type}\n\nTracking token: {token}"
        )
        self.user_id = user_id


    def _build_raw(self, *, token: str, message_type: str) -> str:
        msg = EmailMessage()
        msg["To"] = self.recipient_for_type(message_type)
        msg["From"] = self.sender
        msg["Subject"] = self.subject_for_type(message_type)
        msg["X-Backfill-Token"] = token
        msg["X-Backfill-Type"] = message_type
        msg.set_content(self.body_for_type(message_type, token))
        return base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")


    @staticmethod
    def _headers_map(message: Dict[str, Any]) -> Dict[str, str]:
        headers = (((message.get("payload") or {}).get("headers")) or [])
        return {
            str(h.get("name", "")).lower(): str(h.get("value", ""))
            for h in headers
            if h.get("name")
        }


    def find_sent_by_token(self, token: str) -> List[Tuple[str, Dict[str, str]]]:
        # q is only a coarse candidate search. Exact ownership is verified from
        # the custom header on each candidate before the message is accepted.
        result = _execute(
            self.service.users().messages().list(
                userId=self.user_id,
                q=f'in:sent "{token}"',
                maxResults=20,
            )
        )
        matches: List[Tuple[str, Dict[str, str]]] = []
        for item in result.get("messages", []) or []:
            mid = item["id"]
            message = _execute(
                self.service.users().messages().get(
                    userId=self.user_id,
                    id=mid,
                    format="metadata",
                    metadataHeaders=["X-Backfill-Token", "X-Backfill-Type"],
                )
            )
            headers = self._headers_map(message)
            if headers.get("x-backfill-token") == token:
                matches.append(
                    (
                        mid,
                        {
                            "token": token,
                            "type": headers.get("x-backfill-type", ""),
                        },
                    )
                )
        return matches


    def send(self, *, token: str, message_type: str) -> str:
        # Reconcile before sending. The durable coordinator should do the same,
        # but keeping this check here makes direct adapter replay safer.
        matches = self.find_sent_by_token(token)
        if len(matches) == 1:
            return matches[0][0]
        if len(matches) > 1:
            raise RuntimeError("ambiguous duplicate Gmail token")


        raw = self._build_raw(token=token, message_type=message_type)
        try:
            sent = _execute(
                self.service.users().messages().send(
                    userId=self.user_id,
                    body={"raw": raw},
                )
            )
            return sent["id"]
        except Exception:
            # Transport may have failed after Gmail committed the send.
            reconciled = self.find_sent_by_token(token)
            if len(reconciled) == 1:
                return reconciled[0][0]
            if len(reconciled) > 1:
                raise RuntimeError("ambiguous duplicate Gmail token after send failure")
            raise
