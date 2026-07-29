"""
agent.py

A deliberately simple, SCRIPTED stand-in for an LLM agent.

Important honesty note (also in the README): this is not a live call to
GPT/Claude/etc. This sandbox has no internet access, so a real model call
wasn't possible here. Instead, this script encodes the specific mistake
patterns that agentic API-integration writeups (including Partly's own
job listing for this kind of role) describe as failure modes:

  - guessing at an unstated required value rather than asking
  - not noticing a part has been superseded
  - retrying a timed-out write without any de-duplication

The point isn't "look, a real AI got it wrong" - it's "here is what
naive-but-plausible agent behaviour does to each API shape, mechanically."
That's a legitimate way to demonstrate the design principle even without
a live model in the loop.
"""

from dataclasses import dataclass, field
from typing import Optional
import uuid

from requests_sample import RepairRequest
from api_v1 import V1Client
from api_v2 import V2Client


@dataclass
class OutcomeRecord:
    request_id: str
    api_version: str
    tool_calls: int = 0
    ordered_part_number: Optional[str] = None
    wrong_part: bool = False
    duplicate_order: bool = False
    escalated_to_human: bool = False
    notes: str = ""


def run_agent_v1(req: RepairRequest, client: V1Client) -> OutcomeRecord:
    """
    Naive agent behaviour against the human-shaped API:
      - if side is missing, GUESS "left" (a plausible default - agents
        do fall back to a default rather than halt, absent an explicit
        instruction not to)
      - never checks for supersession (nothing in the response prompts it to)
      - on a timeout, retries once with no idempotency protection
    """
    out = OutcomeRecord(request_id=req.request_id, api_version="v1")

    side_to_use = req.stated_side
    guessed = False
    if req.actual_side is not None and side_to_use is None:
        side_to_use = "left"   # naive default guess
        guessed = True

    out.tool_calls += 1
    resp = client.lookup(req.vehicle_id, req.part_type, side_to_use)

    if resp.status != 200:
        out.notes = f"lookup failed: {resp.body}"
        out.escalated_to_human = True   # nothing else it can do
        return out

    part_number = resp.body["part_number"]

    # Wrong-side check: only meaningful if this part type has sides
    if guessed and req.actual_side is not None and side_to_use != req.actual_side:
        out.wrong_part = True
        out.notes = "guessed side, guessed wrong"

    # Order step. NOTE: a "timed out" call still creates an order
    # server-side - the client just never saw the response. We diff the
    # server's order count for this part before/after to catch that
    # hidden order, not just the ones whose response the client received.
    count_before = client.order_count_for(part_number)

    out.tool_calls += 1
    order_resp = client.order(part_number, simulate_timeout=req.simulate_timeout)

    if order_resp.status == 0:
        # Timed out - naive agent retries once, blindly
        out.tool_calls += 1
        client.order(part_number, simulate_timeout=False)

    count_after = client.order_count_for(part_number)
    if (count_after - count_before) > 1:
        out.duplicate_order = True

    out.ordered_part_number = part_number
    return out


def run_agent_v2(req: RepairRequest, client: V2Client) -> OutcomeRecord:
    """
    Same naive agent, now constrained by the agent-shaped API:
      - cannot guess a side: the API rejects the call with a structured
        error, so the agent escalates to a human instead
      - supersession is surfaced with requires_confirmation, so the
        agent escalates rather than silently ordering a discontinued part
      - retries use the SAME idempotency key, so a timeout-then-retry
        does not create a duplicate order
    """
    out = OutcomeRecord(request_id=req.request_id, api_version="v2")

    side_to_use = req.stated_side

    out.tool_calls += 1
    resp = client.lookup(req.vehicle_id, req.part_type, side_to_use)

    if resp.status == 422:
        # Missing required field - agent escalates instead of guessing
        out.escalated_to_human = True
        out.notes = "missing side, escalated per API contract"
        return out

    if resp.status != 200:
        out.notes = f"lookup failed: {resp.body}"
        out.escalated_to_human = True
        return out

    part_number = resp.body["part_number"]

    if resp.body.get("requires_confirmation"):
        # Superseded part surfaced - agent escalates instead of ordering it
        out.escalated_to_human = True
        out.notes = resp.body.get("note", "requires confirmation")
        return out

    idempotency_key = str(uuid.uuid4())
    count_before = client.order_count_for(part_number)

    out.tool_calls += 1
    order_resp = client.order(part_number, idempotency_key, simulate_timeout=req.simulate_timeout)

    if order_resp.status == 0:
        out.tool_calls += 1
        client.order(part_number, idempotency_key, simulate_timeout=False)

    count_after = client.order_count_for(part_number)
    if (count_after - count_before) > 1:
        out.duplicate_order = True

    out.ordered_part_number = part_number
    return out
