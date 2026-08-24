from __future__ import annotations


import json
from collections.abc import AsyncGenerator
from typing import Any, override


from strands import Agent, tool
from strands.hooks import BeforeToolCallEvent, HookProvider, HookRegistry
from strands.models import Model
from strands.types.content import Messages
from strands.types.streaming import StreamEvent
from strands.types.tools import ToolSpec


from backfill.application import BackfillApplication
from backfill.domain import WorkflowState, make_demo_repo
from backfill.providers import CalendarBooking


class MemoryCalendar:
    def __init__(self, open_slot_id: str):
        self.open_slot_id = open_slot_id; self.open = True; self.bookings = {}; self.create_calls = 0
    def verify_slot_open(self, slot_id: str) -> bool:
        return self.open and slot_id == self.open_slot_id
    def create_booking(self, *, booking_key: str, slot_id: str, candidate_id: str, start: str, end: str) -> CalendarBooking:
        if booking_key in self.bookings: return self.bookings[booking_key]
        if not self.verify_slot_open(slot_id): raise RuntimeError('slot not open')
        self.create_calls += 1
        booking = CalendarBooking('fixture-booking-001', booking_key, slot_id, candidate_id, start, end)
        self.bookings[booking_key] = booking; self.open = False; return booking
    def verify_booking(self, *, event_id: str, booking_key: str, slot_id: str, candidate_id: str, start: str, end: str) -> bool:
        return self.bookings.get(booking_key) == CalendarBooking(event_id, booking_key, slot_id, candidate_id, start, end)


class MemoryMessages:
    def __init__(self): self.sent = {}; self.send_calls = 0
    def send(self, *, token: str, message_type: str) -> str:
        if token in self.sent: return self.sent[token]
        self.send_calls += 1; mid=f'fixture-message-{self.send_calls:03d}'; self.sent[token]=mid; return mid


class ScriptedToolModel(Model):
    def __init__(self, steps: list[dict[str, Any]]):
        self.steps=steps; self.turn=0; self.config={'model_id':'backfill-scripted-smoke'}
    @override
    def update_config(self, **model_config: Any) -> None: self.config.update(model_config)
    @override
    def get_config(self) -> dict[str, Any]: return dict(self.config)
    @override
    def structured_output(self, output_model: Any, prompt: Messages, system_prompt: str | None = None, **kwargs: Any): raise NotImplementedError
    @override
    async def stream(self, messages: Messages, tool_specs: list[ToolSpec] | None = None, system_prompt: str | None = None, **kwargs: Any) -> AsyncGenerator[StreamEvent, None]:
        if self.turn >= len(self.steps): raise RuntimeError('scripted model exhausted')
        step=self.steps[self.turn]; self.turn += 1
        yield {'messageStart': {'role': 'assistant'}}
        if 'tool' in step:
            tid=f'scripted-{self.turn}'
            yield {'contentBlockStart': {'start': {'toolUse': {'name': step['tool'], 'toolUseId': tid}}}}
            yield {'contentBlockDelta': {'delta': {'toolUse': {'input': json.dumps(step.get('input', {}), separators=(',',':'))}}}}
            yield {'contentBlockStop': {}}
            yield {'messageStop': {'stopReason': 'tool_use'}}
        else:
            yield {'contentBlockStart': {'start': {}}}
            yield {'contentBlockDelta': {'delta': {'text': step.get('text','done')}}}
            yield {'contentBlockStop': {}}
            yield {'messageStop': {'stopReason': 'end_turn'}}
        yield {'metadata': {'usage': {'inputTokens':0,'outputTokens':0,'totalTokens':0}, 'metrics': {'latencyMs':0}}}


def make_runtime():
    r=make_demo_repo(); c=MemoryCalendar(r.opening.opening_id); m=MemoryMessages(); a=BackfillApplication(r,c,m); return r,c,m,a
repo, calendar, messages, app = make_runtime()


@tool
def start_backfill() -> dict[str, Any]:
    """Start Backfill's deterministic waitlist recovery workflow."""
    wf=app.start(); return {'state':wf.state.value,'active_offer_id':wf.active_offer_id}


@tool
def apply_offer_response(offer_id: str, response: str, response_id: str, discount: bool = False) -> dict[str, Any]:
    """Apply one externally observed response to the deterministic Backfill service."""
    wf=app.process_response(offer_id,response,response_id,discount=discount)
    return {'state':wf.state.value,'active_offer_id':wf.active_offer_id,'booking_event_id':wf.booking_event_id,'recovered_value_cents':wf.recovered_value_cents}


class OwnerPolicyHook(HookProvider):
    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None: registry.add_callback(BeforeToolCallEvent,self.approve)
    def approve(self,event:BeforeToolCallEvent)->None:
        if event.tool_use['name']!='apply_offer_response': return
        p=event.tool_use['input']
        if p.get('response')!='ACCEPT' or not p.get('discount'): return
        approval=event.interrupt('backfill-discount-approval',reason={'offer_id':p.get('offer_id'),'requested_discount':True})
        if str(approval).lower() not in {'approve','y','yes'}: event.cancel_tool='Owner denied discount exception'


def reset_runtime():
    global repo,calendar,messages,app
    repo,calendar,messages,app=make_runtime()


def run_happy_path():
    reset_runtime()
    model=ScriptedToolModel([
        {'tool':'start_backfill'},
        {'tool':'apply_offer_response','input':{'offer_id':'offer-c2','response':'DECLINE','response_id':'resp-c2'}},
        {'tool':'apply_offer_response','input':{'offer_id':'offer-c3','response':'ACCEPT','response_id':'resp-c3'}},
        {'text':'Backfill complete'}])
    agent=Agent(agent_id='backfill-smoke-happy',model=model,tools=[start_backfill,apply_offer_response],callback_handler=None)
    result=agent('Recover the open appointment end to end.')
    assert result.stop_reason=='end_turn'
    assert repo.workflow.state==WorkflowState.COMPLETED_RECOVERED
    assert repo.workflow.recovered_value_cents==8500
    assert repo.workflow.booking_event_id=='fixture-booking-001'
    assert len(calendar.bookings)==1 and calendar.create_calls==1
    assert repo.ledger=={'wf-001':8500}


def run_interrupt_path():
    reset_runtime()
    model=ScriptedToolModel([
        {'tool':'start_backfill'},
        {'tool':'apply_offer_response','input':{'offer_id':'offer-c2','response':'ACCEPT','response_id':'resp-c2','discount':True}},
        {'text':'Backfill exception resolved'}])
    agent=Agent(agent_id='backfill-smoke-interrupt',model=model,tools=[start_backfill,apply_offer_response],hooks=[OwnerPolicyHook()],callback_handler=None)
    result=agent('Recover the opening while respecting owner policy.')
    assert result.stop_reason=='interrupt' and len(result.interrupts)==1
    assert len(calendar.bookings)==0 and repo.ledger=={}
    intr=result.interrupts[0]
    result=agent([{'interruptResponse':{'interruptId':intr.id,'response':'deny'}}])
    assert result.stop_reason=='end_turn'
    assert len(calendar.bookings)==0 and calendar.create_calls==0 and repo.ledger=={}


if __name__=='__main__':
    run_happy_path(); run_interrupt_path(); print('STRANDS_SMOKE_OK')
