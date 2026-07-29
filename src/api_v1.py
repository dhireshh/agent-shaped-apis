"""
api_v1.py — "human-shaped" API

This is how most parts/e-commerce/catalogue APIs work today:
  - Valid values (sides, part types) are described in prose docs, not
    returned in-band
  - Errors are generic HTTP-style codes with a short message
  - No idempotency key on writes -> retries can double-submit an order
  - Supersession is silent: if you ask for a discontinued part number,
    you get it. No warning.
  - No confidence signal. A lookup either returns something or it doesn't.

A human reading the docs before calling this would do fine. An agent
that only sees the runtime responses will not.
"""

from dataclasses import dataclass
from typing import Optional
import uuid

from catalogue import find_parts, CATALOGUE


@dataclass
class V1Response:
    status: int
    body: dict


class V1Client:
    def __init__(self):
        self._orders: list[dict] = []   # no dedup - every call appends

    def lookup(self, vehicle_id: str, part_type: str, side: Optional[str] = None) -> V1Response:
        """
        GET /v1/parts?vehicle_id=...&part_type=...&side=...

        NOTE (docs, not returned by the API):
        - `side` is required for: headlamp, tail_lamp, front_fender,
          front_door_shell, wing_mirror. Valid values: "left", "right".
        - If `side` is omitted for a sided part_type, the API returns
          whichever match it finds first (undefined order).
        - Superseded parts are NOT filtered out. Check supersession
          separately via GET /v1/parts/{part_number}.
        """
        matches = find_parts(vehicle_id, part_type, side)

        if not matches:
            # Generic error - no hint about what a valid value would be
            return V1Response(404, {"error": "not_found", "message": "No matching part."})

        # Undefined-order behaviour when side wasn't specified and the
        # part type actually has sides: just return the first match.
        chosen = matches[0]
        return V1Response(200, {
            "part_number": chosen.part_number,
            "part_type": chosen.part_type,
            "side": chosen.side,
        })

    def order(self, part_number: str, simulate_timeout: bool = False) -> V1Response:
        """
        POST /v1/orders  { "part_number": "..." }

        NOTE: no idempotency key supported. If a client times out and
        retries, a second order is created.
        """
        if simulate_timeout:
            # The order actually succeeded server-side, but the response
            # never reached the client - this is the classic case that
            # causes blind retries.
            self._orders.append({"order_id": str(uuid.uuid4()), "part_number": part_number})
            return V1Response(0, {"error": "timeout"})   # status 0 = no response received

        self._orders.append({"order_id": str(uuid.uuid4()), "part_number": part_number})
        return V1Response(201, {"order_id": self._orders[-1]["order_id"], "part_number": part_number})

    def order_count_for(self, part_number: str) -> int:
        return sum(1 for o in self._orders if o["part_number"] == part_number)
