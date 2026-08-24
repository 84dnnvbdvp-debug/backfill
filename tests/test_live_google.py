from __future__ import annotations

import base64
import unittest

from backfill.live_google import (
    DedicatedCalendarSlotProbe,
    SlotWindow,
    classify_exact_reply,
    extract_plain_text,
)


class _Request:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


class _Events:
    def __init__(self, payload):
        self.payload = payload

    def list(self, **_kwargs):
        return _Request(self.payload)


class _CalendarService:
    def __init__(self, payload):
        self.payload = payload

    def events(self):
        return _Events(self.payload)


class LiveGooglePureTests(unittest.TestCase):
    def test_exact_reply_accept(self):
        self.assertEqual(classify_exact_reply("\n ACCEPT \n\n> quoted"), "ACCEPT")

    def test_exact_reply_rejects_extra_text(self):
        self.assertIsNone(classify_exact_reply("ACCEPT please"))

    def test_extract_plain_text_base64url(self):
        body = "DECLINE\r\n"
        encoded = base64.urlsafe_b64encode(body.encode()).decode().rstrip("=")
        payload = {"mimeType": "text/plain", "body": {"data": encoded}}
        self.assertEqual(extract_plain_text(payload), body)

    def test_slot_probe_ignores_transparent_but_blocks_opaque(self):
        slot = SlotWindow(
            "slot",
            "2026-08-25T17:00:00-04:00",
            "2026-08-25T17:30:00-04:00",
        )
        transparent = DedicatedCalendarSlotProbe(
            _CalendarService(
                {"items": [{"status": "confirmed", "transparency": "transparent"}]}
            ),
            calendar_id="demo",
            slot=slot,
        )
        self.assertTrue(transparent.is_open("slot"))

        opaque = DedicatedCalendarSlotProbe(
            _CalendarService({"items": [{"status": "confirmed"}]}),
            calendar_id="demo",
            slot=slot,
        )
        self.assertFalse(opaque.is_open("slot"))


if __name__ == "__main__":
    unittest.main()
