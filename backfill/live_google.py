from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from email.utils import parseaddr
from typing import Any, Dict, Iterable, Optional

CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar.events.owned"]
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


def build_google_service(*, api: str, version: str, token_path: str, scopes: Iterable[str]):
    # Lazy imports keep the canonical zero-credential test suite independent of
    # live-provider dependencies.
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(token_path, list(scopes))
    if not creds.valid:
        raise RuntimeError(
            f"{token_path} is not currently valid; run scripts/google_oauth_bootstrap.py "
            f"for {api} to refresh/re-authorize it."
        )
    return build(api, version, credentials=creds, cache_discovery=False)


@dataclass(frozen=True)
class SlotWindow:
    slot_id: str
    start: str
    end: str


class DedicatedCalendarSlotProbe:
    """Treat the configured dedicated calendar as authoritative for one test slot."""

    def __init__(self, service: Any, *, calendar_id: str, slot: SlotWindow):
        self.service = service
        self.calendar_id = calendar_id
        self.slot = slot

    def is_open(self, slot_id: str) -> bool:
        if slot_id != self.slot.slot_id:
            return False
        result = (
            self.service.events()
            .list(
                calendarId=self.calendar_id,
                timeMin=self.slot.start,
                timeMax=self.slot.end,
                singleEvents=True,
                orderBy="startTime",
                maxResults=20,
            )
            .execute()
        )
        for event in result.get("items", []) or []:
            if event.get("status") == "cancelled":
                continue
            if event.get("transparency") == "transparent":
                continue
            return False
        return True


def _decode_body_data(data: str) -> str:
    if not data:
        return ""
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode("ascii")).decode(
        "utf-8", errors="replace"
    )


def extract_plain_text(payload: Dict[str, Any]) -> str:
    mime_type = payload.get("mimeType", "")
    body = payload.get("body") or {}
    if mime_type == "text/plain" and body.get("data"):
        return _decode_body_data(body["data"])
    for part in payload.get("parts", []) or []:
        text = extract_plain_text(part)
        if text:
            return text
    if body.get("data"):
        return _decode_body_data(body["data"])
    return ""


def classify_exact_reply(body: str) -> Optional[str]:
    """
    Accept only a single first authored line: ACCEPT or DECLINE.
    Quoted reply history is ignored because it occurs after that first line.
    """
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(">"):
            return None
        normalized = line.upper()
        if normalized in {"ACCEPT", "DECLINE"}:
            return normalized
        return None
    return None


class GmailReplyPoller:
    def __init__(
        self,
        service: Any,
        *,
        expected_sender: str,
        poll_seconds: float = 5.0,
        timeout_seconds: float = 900.0,
    ):
        self.service = service
        self.expected_sender = expected_sender.lower()
        self.poll_seconds = poll_seconds
        self.timeout_seconds = timeout_seconds

    @staticmethod
    def _headers(message: Dict[str, Any]) -> Dict[str, str]:
        return {
            str(h.get("name", "")).lower(): str(h.get("value", ""))
            for h in ((message.get("payload") or {}).get("headers") or [])
            if h.get("name")
        }

    def wait_for_reply(self, *, sent_message_id: str) -> tuple[str, str]:
        sent = (
            self.service.users()
            .messages()
            .get(
                userId="me",
                id=sent_message_id,
                format="metadata",
                metadataHeaders=["From", "To", "Subject"],
            )
            .execute()
        )
        thread_id = sent["threadId"]
        deadline = time.monotonic() + self.timeout_seconds
        seen = {sent_message_id}

        while time.monotonic() < deadline:
            thread = (
                self.service.users()
                .threads()
                .get(userId="me", id=thread_id, format="full")
                .execute()
            )
            messages = sorted(
                thread.get("messages", []) or [],
                key=lambda m: int(m.get("internalDate", "0")),
            )
            for message in messages:
                mid = message["id"]
                if mid in seen:
                    continue
                seen.add(mid)
                headers = self._headers(message)
                sender = parseaddr(headers.get("from", ""))[1].lower()
                if sender != self.expected_sender:
                    continue
                response = classify_exact_reply(
                    extract_plain_text(message.get("payload") or {})
                )
                if response is not None:
                    return response, mid
            time.sleep(self.poll_seconds)

        raise TimeoutError("no exact ACCEPT/DECLINE reply observed before timeout")
