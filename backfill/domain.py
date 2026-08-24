from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional


class WorkflowState(str, Enum):
    OPENING_DETECTED = "OPENING_DETECTED"
    WAITING_FOR_REPLIES = "WAITING_FOR_REPLIES"
    NEEDS_OWNER_DECISION = "NEEDS_OWNER_DECISION"
    BOOKING = "BOOKING"
    BOOKED_NOTIFICATION_PENDING = "BOOKED_NOTIFICATION_PENDING"
    COMPLETED_RECOVERED = "COMPLETED_RECOVERED"
    COMPLETED_UNRECOVERED = "COMPLETED_UNRECOVERED"


class OfferStatus(str, Enum):
    SENT = "SENT"
    DECLINED = "DECLINED"
    ACCEPTED = "ACCEPTED"
    CLOSED = "CLOSED"


@dataclass
class Opening:
    opening_id: str
    provider_id: str
    service_id: str
    start: str
    end: str
    value_cents: int
    open: bool = True


@dataclass
class Candidate:
    candidate_id: str
    service_id: Optional[str]
    available: bool
    waitlist_entered_at: str
    consent: Optional[bool] = True
    active: bool = True
    conflict: Optional[bool] = False


@dataclass
class Offer:
    offer_id: str
    candidate_id: str
    message_id: Optional[str] = None
    status: OfferStatus = OfferStatus.SENT
    response_id: Optional[str] = None


@dataclass
class Workflow:
    workflow_id: str
    opening_id: str
    state: WorkflowState = WorkflowState.OPENING_DETECTED
    active_offer_id: Optional[str] = None
    winner_candidate_id: Optional[str] = None
    booking_event_id: Optional[str] = None
    recovered_value_cents: int = 0
    requested_discount: bool = False
    approved_value_cents: Optional[int] = None
    exception_candidate_id: Optional[str] = None


@dataclass
class Repo:
    opening: Opening
    candidates: Dict[str, Candidate]
    workflow: Workflow
    offers: Dict[str, Offer] = field(default_factory=dict)
    audit: list[str] = field(default_factory=list)
    ledger: Dict[str, int] = field(default_factory=dict)
    outbox: Dict[str, str] = field(default_factory=dict)


def make_demo_repo(*, unknown_consent: bool = False) -> Repo:
    opening = Opening(
        "slot-2026-08-28T14:00",
        "P1",
        "grooming-60",
        "2026-08-28T14:00:00-04:00",
        "2026-08-28T15:00:00-04:00",
        8500,
    )
    candidates = [
        Candidate("C1", "grooming-90", True, "2026-08-01"),
        Candidate(
            "C2",
            "grooming-60",
            True,
            "2026-08-03",
            consent=None if unknown_consent else True,
        ),
        Candidate("C3", "grooming-60", True, "2026-08-05"),
    ]
    return Repo(
        opening=opening,
        candidates={candidate.candidate_id: candidate for candidate in candidates},
        workflow=Workflow("wf-001", opening.opening_id),
    )
