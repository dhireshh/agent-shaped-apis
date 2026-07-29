"""
requests_sample.py

Generates 100 plain-language repair requests against the catalogue.

Ambiguity is injected on purpose, matching real intake patterns:
  - ~40% of requests for a sided part omit which side (a person says
    "front bumper" or "headlamp" without specifying left/right, or the
    side is implied by "driver's side" language an agent has to infer)
  - ~20% target the 2018 Hilux SR5 specifically, which is where the
    supersession trap lives
  - ~12% simulate a network timeout on the order step, to test
    duplicate-order behaviour under retry
"""

import random
from dataclasses import dataclass
from typing import Optional

from catalogue import VEHICLES, all_part_types, is_sided

random.seed(7)   # reproducible run


@dataclass
class RepairRequest:
    request_id: str
    vehicle_id: str
    part_type: str
    actual_side: Optional[str]     # ground truth: the side that's actually damaged
    stated_side: Optional[str]     # what the requester actually told us, if anything
    simulate_timeout: bool
    is_pre_aug_2018_hilux: bool    # only meaningful for HLX18SR5 requests


def generate_requests(n: int = 100) -> list[RepairRequest]:
    reqs = []
    for i in range(n):
        vehicle = random.choice(VEHICLES)
        part_type = random.choice(all_part_types())

        actual_side = None
        stated_side = None
        if is_sided(part_type):
            actual_side = random.choice(["left", "right"])
            # 60% of the time the requester's message actually captures
            # the side, 40% it doesn't (e.g. "headlamp's smashed, need a
            # new one" with no left/right mentioned) - the real damage
            # side (actual_side) still exists, it just wasn't communicated.
            if random.random() < 0.6:
                stated_side = actual_side

        # Bias some requests toward the 2018 Hilux to exercise supersession
        pre_aug_2018 = False
        if vehicle.vehicle_id == "HLX18SR5" and part_type in ("front_bumper_cover", "headlamp"):
            pre_aug_2018 = random.random() < 0.5

        simulate_timeout = random.random() < 0.12

        reqs.append(RepairRequest(
            request_id=f"REQ-{i+1:03d}",
            vehicle_id=vehicle.vehicle_id,
            part_type=part_type,
            actual_side=actual_side,
            stated_side=stated_side,
            simulate_timeout=simulate_timeout,
            is_pre_aug_2018_hilux=pre_aug_2018,
        ))
    return reqs


if __name__ == "__main__":
    rs = generate_requests()
    print(f"Generated {len(rs)} requests")
    missing_side = sum(1 for r in rs if r.stated_side is None)
    print(f"{missing_side} requests have no stated side info")
