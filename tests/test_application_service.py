import copy
import unittest

from backfill.application import BackfillApplication
from backfill.domain import OfferStatus, WorkflowState, make_demo_repo
from backfill.providers import CalendarBooking


class FakeCalendar:
    def __init__(self, slot_id):
        self.slot_id = slot_id
        self.open = True
        self.bookings = {}
        self.create_calls = 0
        self.verify_visible = True
        self.lookup_visible = True
        self.commit_then_raise = False
        self.raise_before_commit = False

    def verify_slot_open(self, slot_id):
        return self.open and slot_id == self.slot_id

    def find_by_booking_key(self, booking_key):
        if not self.lookup_visible:
            return []
        booking = self.bookings.get(booking_key)
        return [] if booking is None else [booking]

    def create_booking(self, *, booking_key, slot_id, candidate_id, start, end):
        if self.raise_before_commit:
            raise RuntimeError("transport-before-commit")
        if booking_key in self.bookings:
            return self.bookings[booking_key]
        if not self.verify_slot_open(slot_id):
            raise RuntimeError("slot not open")
        self.create_calls += 1
        booking = CalendarBooking(
            f"evt-{self.create_calls}", booking_key, slot_id, candidate_id, start, end
        )
        self.bookings[booking_key] = booking
        self.open = False
        if self.commit_then_raise:
            self.commit_then_raise = False
            raise RuntimeError("timeout-after-commit")
        return booking

    def verify_booking(self, *, event_id, booking_key, slot_id, candidate_id, start, end):
        if not self.verify_visible:
            return False
        return self.bookings.get(booking_key) == CalendarBooking(
            event_id, booking_key, slot_id, candidate_id, start, end
        )


class FakeMessages:
    def __init__(self):
        self.sent = {}
        self.send_calls = 0
        self.visible = True
        self.commit_then_raise_for = set()

    def send(self, *, token, message_type):
        if token in self.sent:
            return self.sent[token]
        self.send_calls += 1
        message_id = f"msg-{self.send_calls}"
        self.sent[token] = message_id
        if message_type in self.commit_then_raise_for:
            self.commit_then_raise_for.remove(message_type)
            raise RuntimeError("timeout-after-commit")
        return message_id

    def find_sent_by_token(self, token):
        if not self.visible or token not in self.sent:
            return []
        return [(self.sent[token], token)]


class BackfillApplicationTests(unittest.TestCase):
    def runtime(self, *, unknown_consent=False):
        repo = make_demo_repo(unknown_consent=unknown_consent)
        cal = FakeCalendar(repo.opening.opening_id)
        msg = FakeMessages()
        return repo, cal, msg, BackfillApplication(repo, cal, msg)

    def get_to_c3(self, app):
        app.start()
        app.process_response("offer-c2", "DECLINE", "r-c2")
        return app.repo.offers["offer-c3"]

    def test_happy_path(self):
        repo, cal, msg, app = self.runtime()
        self.get_to_c3(app)
        app.process_response("offer-c3", "ACCEPT", "r-c3")
        self.assertEqual(repo.workflow.state, WorkflowState.COMPLETED_RECOVERED)
        self.assertEqual(repo.workflow.recovered_value_cents, 8500)
        self.assertEqual(repo.ledger, {"wf-001": 8500})
        self.assertEqual(cal.create_calls, 1)
        self.assertEqual(msg.send_calls, 3)  # C2 offer, C3 offer, confirmation
        self.assertFalse(repo.candidates["C3"].active)
        self.assertEqual(repo.offers["offer-c3"].status, OfferStatus.CLOSED)
        self.assertIsNone(repo.workflow.active_offer_id)

    def test_unknown_required_candidate_data_fails_closed(self):
        repo, cal, msg, app = self.runtime(unknown_consent=True)
        app.start()
        self.assertEqual(repo.workflow.active_offer_id, "offer-c3")
        self.assertNotIn("offer-c2", repo.offers)

    def test_slot_lost_before_booking_is_unrecovered(self):
        repo, cal, msg, app = self.runtime()
        self.get_to_c3(app)
        cal.open = False
        app.process_response("offer-c3", "ACCEPT", "r-c3")
        self.assertEqual(repo.workflow.state, WorkflowState.COMPLETED_UNRECOVERED)
        self.assertEqual(repo.workflow.recovered_value_cents, 0)
        self.assertEqual(repo.ledger, {})
        self.assertEqual(cal.create_calls, 0)

    def test_invalid_response_is_nonmutating(self):
        repo, cal, msg, app = self.runtime()
        app.start()
        before = copy.deepcopy(repo)
        with self.assertRaises(ValueError):
            app.process_response("offer-c2", "MAYBE", "r-bad")
        self.assertEqual(repo, before)

    def test_booking_verification_resume(self):
        repo, cal, msg, app = self.runtime()
        self.get_to_c3(app)
        cal.verify_visible = False
        app.process_response("offer-c3", "ACCEPT", "r-c3")
        self.assertEqual(repo.workflow.state, WorkflowState.BOOKING)
        self.assertIsNotNone(repo.workflow.booking_event_id)
        self.assertEqual(repo.ledger, {})
        cal.verify_visible = True
        app.start()
        self.assertEqual(repo.workflow.state, WorkflowState.COMPLETED_RECOVERED)
        self.assertEqual(cal.create_calls, 1)

    def test_ambiguous_create_reconciles_without_duplicate(self):
        repo, cal, msg, app = self.runtime()
        self.get_to_c3(app)
        cal.commit_then_raise = True
        with self.assertRaises(RuntimeError):
            app.process_response("offer-c3", "ACCEPT", "r-c3")
        self.assertEqual(repo.workflow.state, WorkflowState.BOOKING)
        self.assertIsNone(repo.workflow.booking_event_id)
        app.start()
        self.assertEqual(repo.workflow.state, WorkflowState.COMPLETED_RECOVERED)
        self.assertEqual(cal.create_calls, 1)

    def test_false_terminal_after_ambiguous_create_stays_pending(self):
        repo, cal, msg, app = self.runtime()
        self.get_to_c3(app)
        cal.commit_then_raise = True
        with self.assertRaises(RuntimeError):
            app.process_response("offer-c3", "ACCEPT", "r-c3")
        cal.lookup_visible = False
        app.start()
        self.assertEqual(repo.workflow.state, WorkflowState.BOOKING)
        self.assertEqual(repo.workflow.recovered_value_cents, 0)
        self.assertEqual(cal.create_calls, 1)
        cal.lookup_visible = True
        app.start()
        self.assertEqual(repo.workflow.state, WorkflowState.COMPLETED_RECOVERED)
        self.assertEqual(cal.create_calls, 1)

    def test_confirmation_ambiguity_is_reconciliation_only(self):
        repo, cal, msg, app = self.runtime()
        self.get_to_c3(app)
        msg.commit_then_raise_for.add("confirmation:C3")
        msg.visible = False
        app.process_response("offer-c3", "ACCEPT", "r-c3")
        self.assertEqual(repo.workflow.state, WorkflowState.BOOKED_NOTIFICATION_PENDING)
        calls = msg.send_calls
        app.start()
        self.assertEqual(msg.send_calls, calls)
        self.assertEqual(repo.ledger, {})
        msg.visible = True
        app.start()
        self.assertEqual(repo.workflow.state, WorkflowState.COMPLETED_RECOVERED)
        self.assertEqual(msg.send_calls, calls)

    def test_offer_ambiguity_is_reconciliation_only_and_order_preserving(self):
        repo, cal, msg, app = self.runtime()
        msg.commit_then_raise_for.add("offer:C2")
        msg.visible = False
        app.start()
        self.assertEqual(repo.workflow.active_offer_id, "offer-c2")
        self.assertIsNone(repo.offers["offer-c2"].message_id)
        calls = msg.send_calls
        app.start()
        self.assertEqual(msg.send_calls, calls)
        self.assertNotIn("offer-c3", repo.offers)
        msg.visible = True
        app.start()
        self.assertEqual(repo.workflow.state, WorkflowState.WAITING_FOR_REPLIES)
        self.assertEqual(msg.send_calls, calls)

    def test_response_replay_resumes_decline(self):
        repo, cal, msg, app = self.runtime()
        app.start()
        off = repo.offers["offer-c2"]
        off.status = OfferStatus.DECLINED
        off.response_id = "r-c2"
        repo.workflow.active_offer_id = "offer-c2"
        app.process_response("offer-c2", "DECLINE", "r-c2")
        self.assertEqual(repo.workflow.active_offer_id, "offer-c3")

    def test_response_replay_mismatch_fails_closed(self):
        repo, cal, msg, app = self.runtime()
        app.start()
        app.process_response("offer-c2", "DECLINE", "r-c2")
        with self.assertRaises(RuntimeError):
            app.process_response("offer-c2", "ACCEPT", "r-c2")

    def test_owner_denial_resumes_next_candidate(self):
        repo, cal, msg, app = self.runtime()
        app.start()
        app.process_response("offer-c2", "ACCEPT", "r-c2", discount=True)
        self.assertEqual(repo.workflow.state, WorkflowState.NEEDS_OWNER_DECISION)
        app.apply_owner_decision(approve=False)
        self.assertEqual(repo.workflow.active_offer_id, "offer-c3")
        self.assertEqual(cal.create_calls, 0)

    def test_owner_approval_requires_explicit_value_and_is_replay_safe(self):
        repo, cal, msg, app = self.runtime()
        app.start()
        app.process_response("offer-c2", "ACCEPT", "r-c2", discount=True)
        with self.assertRaises(ValueError):
            app.apply_owner_decision(approve=True)
        app.apply_owner_decision(approve=True, approved_value_cents=7000)
        self.assertEqual(repo.ledger["wf-001"], 7000)
        self.assertEqual(repo.workflow.recovered_value_cents, 7000)
        before = copy.deepcopy(repo)
        app.apply_owner_decision(approve=True, approved_value_cents=7000)
        self.assertEqual(repo, before)

    def test_terminal_states_absorb_response_replay(self):
        repo, cal, msg, app = self.runtime()
        self.get_to_c3(app)
        app.process_response("offer-c3", "ACCEPT", "r-c3")
        snapshot = copy.deepcopy(repo)
        app.process_response("offer-c3", "ACCEPT", "r-c3")
        app.process_response("offer-c2", "DECLINE", "r-c2")
        self.assertEqual(repo, snapshot)

    def test_completed_unrecovered_absorbs_replay(self):
        repo, cal, msg, app = self.runtime()
        self.get_to_c3(app)
        cal.open = False
        app.process_response("offer-c3", "ACCEPT", "r-c3")
        snapshot = copy.deepcopy(repo)
        app.process_response("offer-c3", "ACCEPT", "r-c3")
        self.assertEqual(repo, snapshot)

    def test_notification_outbox_resume_is_idempotent(self):
        repo, cal, msg, app = self.runtime()
        self.get_to_c3(app)
        # Simulate verified booking + durable confirmation outbox before local finalization.
        off = repo.offers["offer-c3"]
        off.status = OfferStatus.ACCEPTED
        off.response_id = "r-c3"
        repo.workflow.state = WorkflowState.BOOKED_NOTIFICATION_PENDING
        repo.workflow.winner_candidate_id = "C3"
        repo.workflow.booking_event_id = "evt-existing"
        token = "[BF-wf-001-CONFIRM-C3]"
        repo.outbox[token] = "msg-confirm"
        app.start()
        self.assertEqual(repo.workflow.state, WorkflowState.COMPLETED_RECOVERED)
        self.assertEqual(repo.ledger, {"wf-001": 8500})
        app.start()
        self.assertEqual(repo.ledger, {"wf-001": 8500})


if __name__ == "__main__":
    unittest.main()
