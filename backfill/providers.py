from __future__ import annotations


from dataclasses import dataclass
from typing import Protocol, Sequence




@dataclass(frozen=True)
class CalendarBooking:
    event_id: str
    booking_key: str
    slot_id: str
    candidate_id: str
    start: str
    end: str




class SlotProbe(Protocol):
    """Authoritative domain-side check that a recoverable slot is still open."""


    def is_open(self, slot_id: str) -> bool:
        ...




class CalendarBookingProvider(Protocol):
    def verify_slot_open(self, slot_id: str) -> bool:
        ...


    def find_by_booking_key(self, booking_key: str) -> Sequence[CalendarBooking]:
        ...


    def create_booking(
        self,
        *,
        booking_key: str,
        slot_id: str,
        candidate_id: str,
        start: str,
        end: str,
    ) -> CalendarBooking:
        ...


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
        ...




class MessageProvider(Protocol):
    def find_sent_by_token(self, token: str):
        ...


    def send(self, *, token: str, message_type: str) -> str:
        ...
