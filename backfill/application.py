from __future__ import annotations
from .domain import Repo, WorkflowState, Offer, OfferStatus
from .providers import CalendarBookingProvider, MessageProvider


class BackfillApplication:
    def __init__(self, repo:Repo, calendar:CalendarBookingProvider, messages:MessageProvider):
        self.repo=repo; self.calendar=calendar; self.messages=messages
    def _eligible(self,c):
        o=self.repo.opening
        if c.service_id is None or c.consent is None or c.conflict is None: return False
        return c.active and c.consent and c.available and not c.conflict and c.service_id==o.service_id
    def _ordered(self):
        return [c for c in sorted(self.repo.candidates.values(),key=lambda x:(x.waitlist_entered_at,x.candidate_id)) if self._eligible(c)]
    def _already_offered(self): return {o.candidate_id for o in self.repo.offers.values()}
    def _pending_offer(self):
        pending=[o for o in self.repo.offers.values() if o.status==OfferStatus.SENT and o.message_id is None]
        if len(pending)>1: raise RuntimeError('multiple pending offer intents')
        return pending[0] if pending else None
    def _send_next(self):
        wf=self.repo.workflow
        if self._pending_offer() is not None: return self.retry_pending_offer_send()
        for c in self._ordered():
            if c.candidate_id in self._already_offered(): continue
            oid=f'offer-{c.candidate_id.lower()}'; token=f'[BF-{wf.workflow_id}-{oid}]'
            off=Offer(oid,c.candidate_id,message_id=None)
            self.repo.offers[oid]=off; wf.active_offer_id=oid
            try:
                mid=self.messages.send(token=token,message_type=f'offer:{c.candidate_id}')
            except Exception:
                self.repo.audit.append(f'offer_send_ambiguous:{token}'); return wf
            off.message_id=mid; wf.state=WorkflowState.WAITING_FOR_REPLIES
            self.repo.audit.append(f'offer:{oid}:{mid}'); return wf
        wf.active_offer_id=None; wf.recovered_value_cents=0; wf.state=WorkflowState.COMPLETED_UNRECOVERED; self.repo.audit.append('unrecovered:exhausted'); return wf
    def retry_pending_offer_send(self):
        wf=self.repo.workflow; off=self._pending_offer()
        if off is None: return wf
        if wf.active_offer_id not in {None,off.offer_id}: raise RuntimeError('pending offer intent mismatch')
        wf.active_offer_id=off.offer_id
        token=f'[BF-{wf.workflow_id}-{off.offer_id}]'
        matches=list(self.messages.find_sent_by_token(token))
        if len(matches)>1: raise RuntimeError('ambiguous duplicate offer token')
        if not matches:
            self.repo.audit.append(f'offer_reconciliation_pending:{token}'); return wf
        mid=matches[0][0]; off.message_id=mid; wf.state=WorkflowState.WAITING_FOR_REPLIES
        self.repo.audit.append(f'offer_reconciled:{off.offer_id}:{mid}'); return wf
    def start(self):
        wf=self.repo.workflow
        if self._pending_offer() is not None: return self.retry_pending_offer_send()
        if wf.state==WorkflowState.NEEDS_OWNER_DECISION and (wf.approved_value_cents is not None or not wf.requested_discount):
            return self._resume_owner_decision()
        if wf.state==WorkflowState.BOOKING:
            if wf.booking_event_id: return self.retry_pending_booking_verification()
            return self.retry_pending_booking_create()
        if wf.state==WorkflowState.BOOKED_NOTIFICATION_PENDING: return self.retry_pending_notification()
        if wf.state!=WorkflowState.OPENING_DETECTED: return wf
        return self._send_next()
    def process_response(self, offer_id:str, response:str, response_id:str, *, discount=False):
        wf=self.repo.workflow; off=self.repo.offers[offer_id]
        if response not in {'DECLINE','ACCEPT'}: raise ValueError(response)
        if wf.state in {WorkflowState.COMPLETED_RECOVERED,WorkflowState.COMPLETED_UNRECOVERED}: return wf
        if off.response_id is None:
            if response=='DECLINE':
                off.status=OfferStatus.DECLINED
            else:
                off.status=OfferStatus.ACCEPTED; wf.requested_discount=bool(discount)
            off.response_id=response_id
        else:
            if off.response_id!=response_id: return wf
            if off.status not in {OfferStatus.DECLINED,OfferStatus.ACCEPTED}: raise RuntimeError('persisted response without resumable offer status')
            if off.status==OfferStatus.DECLINED and response!='DECLINE': raise RuntimeError('response replay mismatch')
            if off.status==OfferStatus.ACCEPTED and response!='ACCEPT': raise RuntimeError('response replay mismatch')
        if off.status==OfferStatus.DECLINED:
            wf.active_offer_id=None; return self._send_next()
        if wf.requested_discount:
            wf.state=WorkflowState.NEEDS_OWNER_DECISION; wf.exception_candidate_id=off.candidate_id; return wf
        return self._book(off.candidate_id,self.repo.opening.value_cents)
    def _resume_owner_decision(self):
        wf=self.repo.workflow
        if wf.state!=WorkflowState.NEEDS_OWNER_DECISION: return wf
        cid=wf.exception_candidate_id
        if wf.approved_value_cents is not None:
            if not cid: raise RuntimeError('approved owner decision missing candidate')
            return self._book(cid,wf.approved_value_cents)
        if not wf.requested_discount:
            if cid:
                for o in self.repo.offers.values():
                    if o.candidate_id==cid and o.status==OfferStatus.ACCEPTED: o.status=OfferStatus.CLOSED
            wf.exception_candidate_id=None; wf.active_offer_id=None
            return self._send_next()
        return wf
    def apply_owner_decision(self, *, approve:bool, approved_value_cents:int|None=None):
        wf=self.repo.workflow
        if wf.state!=WorkflowState.NEEDS_OWNER_DECISION: return wf
        if wf.approved_value_cents is not None:
            if not approve or approved_value_cents!=wf.approved_value_cents: raise RuntimeError('owner decision replay mismatch')
            return self._resume_owner_decision()
        if not wf.requested_discount:
            if approve: raise RuntimeError('owner decision replay mismatch')
            return self._resume_owner_decision()
        if not approve:
            wf.requested_discount=False
            return self._resume_owner_decision()
        if approved_value_cents is None: raise ValueError('explicit approved_value_cents required')
        wf.approved_value_cents=approved_value_cents
        return self._resume_owner_decision()
    def _book(self,cid:str,value_cents:int):
        wf=self.repo.workflow; o=self.repo.opening; wf.state=WorkflowState.BOOKING
        if not self.calendar.verify_slot_open(o.opening_id):
            for off in self.repo.offers.values():
                if off.candidate_id==cid and off.status==OfferStatus.ACCEPTED: off.status=OfferStatus.CLOSED
            wf.active_offer_id=None; wf.state=WorkflowState.COMPLETED_UNRECOVERED; wf.recovered_value_cents=0; self.repo.audit.append('unrecovered:slot_unavailable'); return wf
        booking_key=f'backfill:{wf.workflow_id}:{cid}:{o.opening_id}'
        b=self.calendar.create_booking(booking_key=booking_key,slot_id=o.opening_id,candidate_id=cid,start=o.start,end=o.end)
        wf.booking_event_id=b.event_id
        if not self.calendar.verify_booking(event_id=b.event_id,booking_key=booking_key,slot_id=o.opening_id,candidate_id=cid,start=o.start,end=o.end):
            self.repo.audit.append(f'booking_verification_pending:{b.event_id}'); return wf
        wf.winner_candidate_id=cid; o.open=False
        return self._confirm_and_finish(value_cents)
    def retry_pending_booking_create(self):
        wf=self.repo.workflow; o=self.repo.opening
        if wf.state!=WorkflowState.BOOKING or wf.booking_event_id or not wf.active_offer_id: return wf
        off=self.repo.offers.get(wf.active_offer_id)
        if off is None or off.status!=OfferStatus.ACCEPTED: return wf
        cid=off.candidate_id
        booking_key=f'backfill:{wf.workflow_id}:{cid}:{o.opening_id}'
        matches=list(self.calendar.find_by_booking_key(booking_key))
        if len(matches)>1: raise RuntimeError('ambiguous booking reconciliation')
        if len(matches)==1:
            b=matches[0]
            if not self.calendar.verify_booking(event_id=b.event_id,booking_key=booking_key,slot_id=o.opening_id,candidate_id=cid,start=o.start,end=o.end):
                raise RuntimeError('booking reconciliation mismatch')
            wf.booking_event_id=b.event_id; wf.winner_candidate_id=cid; o.open=False
            value=wf.approved_value_cents if wf.approved_value_cents is not None else o.value_cents
            self.repo.audit.append(f'booking_create_reconciled:{b.event_id}')
            return self._confirm_and_finish(value)
        if not self.calendar.verify_slot_open(o.opening_id):
            wf.recovered_value_cents=0; self.repo.audit.append('booking_create_reconciliation_pending:slot_closed_after_ambiguous_create'); return wf
        value=wf.approved_value_cents if wf.approved_value_cents is not None else o.value_cents
        return self._book(cid,value)
    def retry_pending_booking_verification(self):
        wf=self.repo.workflow; o=self.repo.opening
        if wf.state!=WorkflowState.BOOKING or not wf.booking_event_id or not wf.active_offer_id: return wf
        off=self.repo.offers.get(wf.active_offer_id)
        if off is None or off.status!=OfferStatus.ACCEPTED: return wf
        cid=off.candidate_id
        booking_key=f'backfill:{wf.workflow_id}:{cid}:{o.opening_id}'
        if not self.calendar.verify_booking(event_id=wf.booking_event_id,booking_key=booking_key,slot_id=o.opening_id,candidate_id=cid,start=o.start,end=o.end):
            self.repo.audit.append(f'booking_verification_still_pending:{wf.booking_event_id}'); return wf
        wf.winner_candidate_id=cid; o.open=False
        value=wf.approved_value_cents if wf.approved_value_cents is not None else o.value_cents
        self.repo.audit.append(f'booking_verification_reconciled:{wf.booking_event_id}')
        return self._confirm_and_finish(value)
    def _complete_after_notification(self,value_cents:int):
        wf=self.repo.workflow; cid=wf.winner_candidate_id
        if cid is None: raise RuntimeError('completion missing winner candidate')
        self.repo.candidates[cid].active=False
        for off in self.repo.offers.values():
            if off.candidate_id==cid and off.status==OfferStatus.ACCEPTED: off.status=OfferStatus.CLOSED
        self.repo.ledger.setdefault(wf.workflow_id,value_cents)
        wf.active_offer_id=None; wf.exception_candidate_id=None
        wf.recovered_value_cents=self.repo.ledger[wf.workflow_id]; wf.state=WorkflowState.COMPLETED_RECOVERED; return wf


    def _confirm_and_finish(self,value_cents:int):
        wf=self.repo.workflow; cid=wf.winner_candidate_id; token=f'[BF-{wf.workflow_id}-CONFIRM-{cid}]'
        if token in self.repo.outbox:
            return self._complete_after_notification(value_cents)
        wf.state=WorkflowState.BOOKED_NOTIFICATION_PENDING
        self.repo.audit.append(f'notification_send_intent:{token}')
        try:
            mid=self.messages.send(token=token,message_type=f'confirmation:{cid}')
        except Exception:
            self.repo.audit.append(f'notification_send_ambiguous:{token}'); return wf
        self.repo.outbox[token]=mid
        self.repo.audit.append(f'notification_sent:{token}:{mid}')
        return self._complete_after_notification(value_cents)


    def retry_pending_notification(self):
        wf=self.repo.workflow
        if wf.state!=WorkflowState.BOOKED_NOTIFICATION_PENDING: return wf
        cid=wf.winner_candidate_id; token=f'[BF-{wf.workflow_id}-CONFIRM-{cid}]'
        if token in self.repo.outbox:
            value=wf.approved_value_cents if wf.approved_value_cents is not None else self.repo.opening.value_cents
            self.repo.audit.append(f'notification_outbox_replay:{token}:{self.repo.outbox[token]}')
            return self._complete_after_notification(value)
        matches=list(self.messages.find_sent_by_token(token))
        if len(matches)>1: raise RuntimeError('ambiguous duplicate confirmation token')
        if not matches:
            self.repo.audit.append(f'notification_reconciliation_pending:{token}'); return wf
        mid=matches[0][0]; self.repo.outbox[token]=mid
        value=wf.approved_value_cents if wf.approved_value_cents is not None else self.repo.opening.value_cents
        self.repo.audit.append(f'notification_reconciled:{token}:{mid}')
        return self._complete_after_notification(value)
