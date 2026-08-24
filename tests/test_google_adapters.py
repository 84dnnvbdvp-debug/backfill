import base64
import unittest
from email import policy
from email.parser import BytesParser


from backfill.google_adapters import (
    GmailOutboxAdapter,
    GoogleCalendarBookingAdapter,
    deterministic_google_event_id,
)




class NotFound(Exception):
    pass




class Request:
    def __init__(self, fn):
        self.fn = fn
    def execute(self):
        return self.fn()




class SlotProbe:
    def __init__(self):
        self.open = {}
    def is_open(self, slot_id):
        return self.open.get(slot_id, False)




class FakeCalendarEvents:
    def __init__(self, parent):
        self.parent = parent


    def get(self, *, calendarId, eventId):
        def run():
            if eventId not in self.parent.store:
                raise NotFound(eventId)
            return self.parent.store[eventId]
        return Request(run)


    def insert(self, *, calendarId, body, sendUpdates):
        def run():
            self.parent.insert_calls += 1
            eid = body["id"]
            if eid in self.parent.store:
                raise RuntimeError("409 duplicate")
            event = dict(body)
            event["status"] = "confirmed"
            self.parent.store[eid] = event
            if self.parent.timeout_after_commit_once:
                self.parent.timeout_after_commit_once = False
                raise TimeoutError("calendar timeout after commit")
            if self.parent.timeout_before_commit_once:
                self.parent.timeout_before_commit_once = False
                del self.parent.store[eid]
                raise TimeoutError("calendar timeout before commit")
            return event
        return Request(run)




class FakeCalendarService:
    def __init__(self):
        self.store = {}
        self.insert_calls = 0
        self.timeout_after_commit_once = False
        self.timeout_before_commit_once = False
        self._events = FakeCalendarEvents(self)
    def events(self):
        return self._events




class FakeMessages:
    def __init__(self, parent):
        self.parent = parent


    def list(self, *, userId, q, maxResults):
        token = q.split('"')[1] if '"' in q else q
        def run():
            ids = [
                {"id": mid}
                for mid, item in self.parent.store.items()
                if token in item["raw_text"]
            ]
            return {"messages": ids}
        return Request(run)


    def get(self, *, userId, id, format, metadataHeaders):
        def run():
            return {
                "id": id,
                "payload": {
                    "headers": self.parent.store[id]["headers"],
                },
            }
        return Request(run)


    def send(self, *, userId, body):
        def run():
            self.parent.send_calls += 1
            raw = base64.urlsafe_b64decode(body["raw"].encode("ascii"))
            msg = BytesParser(policy=policy.default).parsebytes(raw)
            headers = [
                {"name": k, "value": str(v)}
                for (k, v) in msg.items()
            ]
            mid = f"m{len(self.parent.store)+1}"
            self.parent.store[mid] = {
                "headers": headers,
                "raw_text": raw.decode("utf-8", errors="replace"),
            }
            if self.parent.timeout_after_commit_once:
                self.parent.timeout_after_commit_once = False
                raise TimeoutError("gmail timeout after commit")
            if self.parent.timeout_before_commit_once:
                self.parent.timeout_before_commit_once = False
                del self.parent.store[mid]
                raise TimeoutError("gmail timeout before commit")
            return {"id": mid}
        return Request(run)




class FakeUsers:
    def __init__(self, parent):
        self._messages = FakeMessages(parent)
    def messages(self):
        return self._messages




class FakeGmailService:
    def __init__(self):
        self.store = {}
        self.send_calls = 0
        self.timeout_after_commit_once = False
        self.timeout_before_commit_once = False
        self._users = FakeUsers(self)
    def users(self):
        return self._users




class GoogleAdapterTests(unittest.TestCase):
    def calendar(self):
        svc = FakeCalendarService()
        probe = SlotProbe()
        probe.open["slot-1"] = True
        adapter = GoogleCalendarBookingAdapter(
            svc,
            calendar_id="backfill-demo@example.test",
            slot_probe=probe,
        )
        return svc, probe, adapter


    def gmail(self):
        svc = FakeGmailService()
        adapter = GmailOutboxAdapter(
            svc,
            sender="backfill-demo@example.test",
            recipient_for_type=lambda _: "client@example.test",
        )
        return svc, adapter


    def test_ga01_event_id_is_stable_and_google_valid(self):
        a = deterministic_google_event_id("backfill:wf001:C3:slot-1")
        b = deterministic_google_event_id("backfill:wf001:C3:slot-1")
        self.assertEqual(a, b)
        self.assertGreaterEqual(len(a), 5)
        self.assertTrue(all(c in "0123456789abcdefghijklmnopqrstuv" for c in a))


    def test_ga02_calendar_replay_uses_same_event_without_second_insert(self):
        svc, probe, adapter = self.calendar()
        kwargs = dict(
            booking_key="backfill:wf001:C3:slot-1",
            slot_id="slot-1",
            candidate_id="C3",
            start="2026-08-28T14:00:00-04:00",
            end="2026-08-28T15:00:00-04:00",
        )
        one = adapter.create_booking(**kwargs)
        two = adapter.create_booking(**kwargs)
        self.assertEqual(one.event_id, two.event_id)
        self.assertEqual(svc.insert_calls, 1)
        self.assertEqual(len(svc.store), 1)


    def test_ga03_calendar_timeout_after_commit_reconciles_exact_id(self):
        svc, probe, adapter = self.calendar()
        svc.timeout_after_commit_once = True
        booking = adapter.create_booking(
            booking_key="backfill:wf001:C3:slot-1",
            slot_id="slot-1",
            candidate_id="C3",
            start="2026-08-28T14:00:00-04:00",
            end="2026-08-28T15:00:00-04:00",
        )
        self.assertEqual(svc.insert_calls, 1)
        self.assertEqual(len(svc.store), 1)
        self.assertTrue(booking.event_id.startswith("bf"))


    def test_ga04_calendar_never_mutates_if_slot_probe_closed(self):
        svc, probe, adapter = self.calendar()
        probe.open["slot-1"] = False
        with self.assertRaises(RuntimeError):
            adapter.create_booking(
                booking_key="backfill:wf001:C3:slot-1",
                slot_id="slot-1",
                candidate_id="C3",
                start="2026-08-28T14:00:00-04:00",
                end="2026-08-28T15:00:00-04:00",
            )
        self.assertEqual(svc.insert_calls, 0)
        self.assertEqual(svc.store, {})


    def test_ga05_verify_booking_checks_backfill_private_metadata(self):
        svc, probe, adapter = self.calendar()
        booking = adapter.create_booking(
            booking_key="backfill:wf001:C3:slot-1",
            slot_id="slot-1",
            candidate_id="C3",
            start="2026-08-28T14:00:00-04:00",
            end="2026-08-28T15:00:00-04:00",
        )
        self.assertTrue(adapter.verify_booking(
            event_id=booking.event_id,
            booking_key=booking.booking_key,
            slot_id="slot-1",
            candidate_id="C3",
            start="2026-08-28T14:00:00-04:00",
            end="2026-08-28T15:00:00-04:00",
        ))
        self.assertFalse(adapter.verify_booking(
            event_id=booking.event_id,
            booking_key=booking.booking_key,
            slot_id="slot-1",
            candidate_id="C2",
            start="2026-08-28T14:00:00-04:00",
            end="2026-08-28T15:00:00-04:00",
        ))


    def test_ga06_gmail_mime_contains_exact_backfill_token_header(self):
        svc, adapter = self.gmail()
        mid = adapter.send(token="[BF-WF001-CONFIRMATION]", message_type="confirmation")
        headers = {
            h["name"].lower(): h["value"]
            for h in svc.store[mid]["headers"]
        }
        self.assertEqual(headers["x-backfill-token"], "[BF-WF001-CONFIRMATION]")
        self.assertEqual(headers["x-backfill-type"], "confirmation")


    def test_ga07_gmail_replay_reconciles_without_second_send(self):
        svc, adapter = self.gmail()
        one = adapter.send(token="[BF-WF001-CONFIRMATION]", message_type="confirmation")
        two = adapter.send(token="[BF-WF001-CONFIRMATION]", message_type="confirmation")
        self.assertEqual(one, two)
        self.assertEqual(svc.send_calls, 1)
        self.assertEqual(len(svc.store), 1)


    def test_ga08_gmail_timeout_after_commit_reconciles_without_duplicate(self):
        svc, adapter = self.gmail()
        svc.timeout_after_commit_once = True
        mid = adapter.send(token="[BF-WF001-CONFIRMATION]", message_type="confirmation")
        self.assertEqual(mid, "m1")
        self.assertEqual(svc.send_calls, 1)
        self.assertEqual(len(svc.store), 1)


    def test_ga09_gmail_search_rejects_false_positive_without_header(self):
        svc, adapter = self.gmail()
        svc.store["foreign"] = {
            "raw_text": 'body contains [BF-WF001-CONFIRMATION]',
            "headers": [{"name": "Subject", "value": "[BF-WF001-CONFIRMATION]"}],
        }
        self.assertEqual(adapter.find_sent_by_token("[BF-WF001-CONFIRMATION]"), [])


    def test_ga10_calendar_booking_key_collision_fails_closed(self):
        svc, probe, adapter = self.calendar()
        key = "backfill:wf001:C3:slot-1"
        eid = deterministic_google_event_id(key)
        svc.store[eid] = {
            "id": eid,
            "status": "confirmed",
            "start": {"dateTime": "2026-08-28T14:00:00-04:00"},
            "end": {"dateTime": "2026-08-28T15:00:00-04:00"},
            "extendedProperties": {
                "private": {
                    "backfill_booking_key": "someone-else",
                    "backfill_slot_id": "slot-other",
                    "backfill_candidate_id": "OTHER",
                }
            },
        }
        with self.assertRaises(RuntimeError):
            adapter.create_booking(
                booking_key=key,
                slot_id="slot-1",
                candidate_id="C3",
                start="2026-08-28T14:00:00-04:00",
                end="2026-08-28T15:00:00-04:00",
            )
        self.assertEqual(svc.insert_calls, 0)




if __name__ == "__main__":
    unittest.main()
