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

    def find_by_boking_key(self, booking_key):
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
        self.assertEqual(repo.workflow.state, WorkflowState.BOOKED_NOTIFICATION_PENDING
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
    def testk}É•ÍÁ½¹Í•}É•Á±…å}É•ÍÕµ•Í}‘•±¥¹”¡Í•±˜¤è(€€€€€€€É•Á¼°…°°µÍœ°…ÁÀ€ôÍ•±˜¹ÉÕ¹Ñ¥µ” ¤(€€€€€€€…ÁÀ¹ÍÑ…ÉĞ ¤(€€€€€€€½™˜€ôÉ•Á¼¹½™™•ÉÍl‰½™™•ÈµŒÈ‰t(€€€€€€€½™˜¹ÍÑ…ÑÕÌ€ô=™™•ÉMÑ…ÑÕÌ¹1%9(€€€€€€€½™˜¹É•ÍÁ½¹Í•}¥€ô€‰ÈµŒÈˆ(€€€€€€€É•Á¼¹İ½É­™±½Ü¹…Ñ¥Ù•}½™™•É}¥€ô€‰½™™•ÈµŒÈˆ(€€€€€€€…ÁÀ¹ÁÉ½•ÍÍ}É•ÍÁ½¹Í” ‰½™™•ÈµŒÈˆ°€‰1%9ˆ°€‰ÈµŒÈˆ¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑÅÕ…°¡É•Á¼¹İ½É­™±½Ü¹…Ñ¥Ù•}½™™•É}¥°€‰½™™•ÈµŒÌˆ¤((€€€‘•˜Ñ•ÍÑ}É•ÍÁ½¹Í•}É•Á±…å}µ¥Íµ…Ñ¡}™…¥±Í}±½Í•¡Í•±˜¤è(€€€€€€€É•Á¼°…°°µÍœ°…ÁÀ€ôÍ•±˜¹ÉÕ¹Ñ¥µ” ¤(€€€€€€€…ÁÀ¹ÍÑ…ÉĞ ¤(€€€€€€€…ÁÀ¹ÁÉ½•ÍÍ}É•ÍÁ½¹Í” ‰½™™•ÈµŒÈˆ°€‰1%9ˆ°€‰ÈµŒÈˆ¤(€€€€€€€İ¥Ñ Í•±˜¹…ÍÍ•ÉÑI…¥Í•Ì¡IÕ¹Ñ¥µ•ÉÉ½È¤è(€€€€€€€€€€€…ÁÀ¹ÁÉ½•ÍÍ}É•ÍÁ½¹Í” ‰½™™•ÈµŒÈˆ°€‰APˆ°€‰ÈµŒÈˆ¤(€€€‘•˜Ñ•ÍÑ}½İ¹•É}‘•¹¥…±}É•ÍÕµ•Í}¹•áÑ}…¹‘¥‘…Ñ”¡Í•±˜¤è(€€€€€€€É•Á¼°…°°µÍœ°…ÁÀ€ôÍ•±˜¹ÉÕ¹Ñ¥µ” ¤(€€€€€€€…ÁÀ¹ÍÑ…ÉĞ ¤(€€€€€€€…ÁÀ¹ÁÉ½•ÍÍ}É•ÍÁ½¹Í” ‰½™™•ÈµŒÈˆ°€‰APˆ°€‰ÈµŒÈˆ°‘¥Í½Õ¹ĞõQÉÕ”¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑÅÕ…°¡É•Á¼¹İ½É­™±½Ü¹ÍÑ…Ñ”°]½É­™±½İMÑ…Ñ”¹9M}=]9I}%M%=8¤(€€€€€€€…ÁÀ¹…ÁÁ±å}½İ¹•É}‘•¥Í¥½¸¡…ÁÁÉ½Ù”õ…±Í”¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑÅÕ…°¡É•Á¼¹İ½É­™±½Ü¹…Ñ¥Ù•}½™™•É}¥°€‰½™™•ÈµŒÌˆ¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑÅÕ…°¡…°¹É•…Ñ•}…±±Ì°€À¤((€€€‘•˜Ñ•ÍÑ}½İ¹•É}…ÁÁÉ½Ù…±}É•ÅÕ¥É•Í}•áÁ±¥¥Ñ}Ù…±Õ•}…¹‘}¥Í}É•Á±…å}Í…™”¡Í•±˜¤è(€€€€€€€É•Á¼°…°°µÍœ°…ÁÀ€ôÍ•±˜¹ÉÕ¹Ñ¥µ” ¤(€€€€€€€…ÁÀ¹ÍÑ…ÉĞ ¤(€€€€€€€…ÁÀ¹ÁÉ½•ÍÍ}É•ÍÁ½¹Í” ‰½™™•ÈµŒÈˆ°€‰APˆ°€‰ÈµŒÈˆ°‘¥Í½Õ¹ĞõQÉÕ”¤(€€€€€€€İ¥Ñ Í•±˜¹…ÍÍ•ÉÑI…¥Í•Ì¡Y…±Õ•ÉÉ½È¤è(€€€€€€€€€€€…ÁÀ¹…ÁÁ±å}½İ¹•É}‘•¥Í¥½¸¡…ÁÁÉ½Ù”õQÉÕ”¤(€€€€€€€…ÁÀ¹…ÁÁ±å}½İ¹•É}‘•¥Í¥½¸¡…ÁÁÉ½Ù”õQÉÕ”°…ÁÁÉ½Ù•‘}Ù…±Õ•}•¹ÑÌôÜÀÀÀ¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑÅÕ…°¡É•Á¼¹±•‘•Él‰İ˜´ÀÀÄ‰t°€ÜÀÀÀ¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑÅÕ…°¡É•Á¼¹İ½É­™±½Ü¹É•½Ù•É•‘}Ù…±Õ•}•¹ÑÌ°€ÜÀÀÀ¤(€€€€€€€‰•™½É”€ô½Áä¹‘••Á½Áä¡É•Á¼¤(€€€€€€€…ÁÀ¹…ÁÁ±å}½İ¹•É}‘•¥Í¥½¸¡…ÁÁÉ½Ù”õQÉÕ”°…ÁÁÉ½Ù•‘}Ù…±Õ•}•¹ÑÌôÜÀÀÀ¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑÅÕ…°¡É•Á¼°‰•™½É”¤((€€€‘•˜Ñ•ÍÑ}Ñ•Éµ¥¹…±}ÍÑ…Ñ•Í}…‰Í½É‰}É•ÍÁ½¹Í•}É•Á±…ä¡Í•±˜¤è(€€€€€€€É•Á¼°…°°µÍœ°…ÁÀ€ôÍ•±˜¹ÉÕ¹Ñ¥µ” ¤(€€€€€€€Í•±˜¹•Ñ}Ñ½}ŒÌ¡…ÁÀ¤(€€€€€€€…ÁÀ¹ÁÉ½•ÍÍ}É•ÍÁ½¹Í” ‰½™™•ÈµŒÌˆ°€‰APˆ°€‰ÈµŒÌˆ¤(€€€€€€€Í¹…ÁÍ¡½Ğ€ô½Áä¹‘••Á½Áä¡É•Á¼¤(€€€€€€€…ÁÀ¹ÁÉ½•ÍÍ}É•ÍÁ½¹Í” ‰½™™•ÈµŒÌˆ°€‰APˆ°€‰ÈµŒÌˆ¤(€€€€€€€…ÁÀ¹ÁÉ½•ÍÍ}É•ÍÁ½¹Í” ‰½™™•ÈµŒÈˆ°€‰1%9ˆ°€‰ÈµŒÈˆ¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑÅÕ…°¡É•Á¼°Í¹…ÁÍ¡½Ğ¤((€€€‘•˜Ñ•ÍÑ}½µÁ±•Ñ•‘}Õ¹É•½Ù•É•‘}…‰Í½É‰Í}É•Á±…ä¡Í•±˜¤è(€€€€€€€É•Á¼°…°°µÍœ°…ÁÀ€ôÍ•±˜¹ÉÕ¹Ñ¥µ” ¤(€€€€€€€Í•±˜¹•Ñ}Ñ½}ŒÌ¡…ÁÀ¤(€€€€€€€…°¹½Á•¸€ô…±Í”(€€€€€€€…ÁÀ¹ÁÉ½•ÍÍ}É•ÍÁ½¹Í” ‰½™™•ÈµŒÌˆ°€‰APˆ°€‰ÈµŒÌˆ¤(€€€€€€€Í¹…ÁÍ¡½Ğ€ô½Áä¹‘••Á½Áä¡É•Á¼¤(€€€€€€€…ÁÀ¹ÁÉ½•ÍÍ}É•ÍÁ½¹Í” ‰½™™•ÈµŒÌˆ°€‰APˆ°€‰ÈµŒÌˆ¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑÅÕ…°¡É•Á¼°Í¹…ÁÍ¡½Ğ¤((€€€‘•˜Ñ•ÍÑ}¹½Ñ¥™¥…Ñ¥½¹}½ÕÑ‰½á}É•ÍÕµ•}¥Í}¥‘•µÁ½Ñ•¹Ğ¡Í•±˜¤è(€€€€€€€É•Á¼°…°°µÍœ°…ÁÀ€ôÍ•±˜¹ÉÕ¹Ñ¥µ” ¤(€€€€€€€Í•±˜¹•Ñ}Ñ½}ŒÌ¡…ÁÀ¤(€€€€€€€€ŒM¥µÕ±…Ñ”Ù•É¥™¥•‰½½­¥¹œ€¬‘ÕÉ…‰±”½¹™¥Éµ…Ñ¥½¸½ÕÑ‰½à‰•™½É”±½…°™¥¹…±¥é…Ñ¥½¸¸(€€€€€€€½™˜€ôÉ•Á¼¹½™™•ÉÍl‰½™™•ÈµŒÌ‰t(€€€€€€€½™˜¹ÍÑ…ÑÕÌ€ô=™™•ÉMÑ…ÑÕÌ¹AQ(€€€€€€€½™˜¹É•ÍÁ½¹Í•}¥€ô€‰ÈµŒÌˆ(€€€€€€€É•Á¼¹İ½É­™±½Ü¹ÍÑ…Ñ”€ô]½É­™±½İMÑ…Ñ”¹	==-}9=Q%%Q%=9}A9%9(€€€€€€€É•Á¼¹İ½É­™±½Ü¹İ¥¹¹•É}…¹‘¥‘…Ñ•}¥€ô€‰Ìˆ(€€€€€€€É•Á¼¹İ½É­™±½Ü¹‰½½­¥¹}•Ù•¹Ñ}¥€ô€‰•ÙĞµ•á¥ÍÑ¥¹œˆ(€€€€€€€Ñ½­•¸€ô€‰m	µİ˜´ÀÀÄµ=9%I4µÍtˆ(€€€€€€€É•Á¼¹½ÕÑ‰½ámÑ½­•¹t€ô€‰µÍœµ½¹™¥É´ˆ(€€€€€€€…ÁÀ¹ÍÑ…ÉĞ ¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑÅÕ…°¡É•Á¼¹İ½É­™±½Ü¹ÍÑ…Ñ”°]½É­™±½İMÑ…Ñ”¹=5A1Q}I=YI¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑÅÕ…°¡É•Á¼¹±•‘•È°ì‰İ˜´ÀÀÄˆè€àÔÀÁô¤(€€€€€€€…ÁÀ¹ÍÑ…ÉĞ ¤(€€€€€€€Í•±˜¹…ÍÍ•ÉÑÅÕ…°¡É•Á¼¹±•‘•È°ì‰İ˜´ÀÀÄˆè€àÔÀÁô¤()¥˜}}¹…µ•}|€ôô€‰}}µ…¥¹}|ˆè(€€€Õ¹¥ÑÑ•ÍĞ¹µ…¥¸ ¤(