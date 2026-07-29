"""
api_v2.py — "agent-shaped" API

Same underlying catalogue, same operations. Four things are different:

  1. Schema over prose: `side` is a required, enumerated field for sided
     part types. The API tells you that in-band via a /capabilities-style
     response, not in separate documentation.
  2. Errors carry the next valid action, not just a code.
  3. Supersession is surfaced automatically, with a confidence score and
     a `requires_confirmation` flag instead of silently returning a
     discontinued part.
  4. Writes require an idempotency key. Retrying the same key returns the
     original result instead of creating a duplicate.
"""

from dataclasses import dataclass
from typing import Optional
import uuid

from catalogue import find_parts, is_sided, all_part_types


@dataclass
class V2Response:
    status: int
    body: dict


class V2Client:
    def __init__(self):
        self._orders: dict[str, dict] = {}   # keyed by idempotency_key

    def capabilities(self) -> V2Response:
        """
        GET /v2/capabilities

        Machine-readable description of what this API needs, so an agent
        never has to guess a valid value.
        """
        return V2Response(200, {
            "part_types": all_part_types(),
            "sided_part_types": [pt for pt in all_part_types() if is_sided(pt)],
            "side_values": ["left", "right"],
            "lookup_requires": {
                "vehicle_id": True,
                "part_type": True,
                "side": "required_if_sided",
            },
        })

    def lookup(self, vehicle_id: str, part_type: str, side: Optional[str] = None) -> V2Response:
        """
        POST /v2/parts/lookup
        """
        if is_sided(part_type) and side is None:
            return V2Response(422, {
                "error": "missing_required_field",
                "field": "side",
                "message": f"'{part_type}' is a sided part. 'side' must be 'left' or 'right'.",
                "next_action": {
                    "type": "resupply_field",
                    "field": "side",
                    "allowed_values": ["left", "right"],
                },
            })

        matches = find_parts(vehicle_id, part_type, side)

        if not matches:
            return V2Response(404, {
                "error": "not_found",
                "message": "No matching part for this vehicle/part_type/side combination.",
                "next_action": {"type": "retry_with_different_query"},
            })

        # Prefer a non-superseded (current) part if one exists.
        current = [p for p in matches if p.superseded_by is None]
        chosen = current[0] if current else matches[0]

        result = {
            "part_number": chosen.part_number,
            "part_type": chosen.part_type,
            "side": chosen.side,
            "confidence": 1.0 if len(matches) == 1 or current else 0.6,
            "requires_confirmation": False,
        }

        if chosen.superseded_by:
            # We only land here if EVERY match for this query is superseded
            # (e.g. agent explicitly asked for the old part number/date range).
            result["requires_confirmation"] = True
            result["confidence"] = 0.4
            result["note"] = (
                f"{chosen.part_number} has been superseded by "
                f"{chosen.superseded_by}. Confirm before ordering the "
                f"discontinued part."
            )

        return V2Response(200, result)

    def order(self, part_number: str, idempotency_key: str,
              simulate_timeout: bool = False) -> V2Response:
        """
        POST /v2/orders
        Headers: Idempotency-Key: <uuid>

        Replaying the same idempotency_key returns the original order
        instead of creating a new one - even if the first response never
        reached the client.
        """
        if idempotency_key in self._orders:
            existing = self._orders[idempotency_key]
            return V2Response(200, {**existing, "replay": True})

        order_id = str(uuid.uuid4())
        record = {"order_id": order_id, "part_number": part_number}
        self._orders[idempotency_key] = record

        if simulate_timeout:
            # Server-side write succeeded and was recorded under this key.
            # A retry with the SAME key will hit the branch above and get
            # the same order_id back, not a duplicate.
            return V2Response(0, {"error": "timeout"})

        return V2Response(201, {**record, "replay": False})

    def order_count_for(self, part_number: str) -> int:
        return sum(1 for o in self._orders.values() if o["part_number"] == part_number)
