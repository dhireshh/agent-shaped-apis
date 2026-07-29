"""
catalogue.py

A small, deliberately messy vehicle parts catalogue.

This mirrors the three things that make real parts catalogues hard:
  1. Handedness   - many parts come in mirrored left/right versions
  2. Supersession - a part number gets replaced by a newer one mid-production
  3. Trim splits  - the "same" part differs by trim/spec level

Nothing here is Partly's data. It's invented, small, and just realistic
enough to expose the failure modes we're measuring.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Vehicle:
    vehicle_id: str
    make: str
    model: str
    trim: str
    model_year: int


@dataclass(frozen=True)
class Part:
    part_number: str
    vehicle_id: str
    part_type: str            # e.g. "front_bumper_cover"
    side: Optional[str]       # "left" / "right" / None if not side-specific
    superseded_by: Optional[str] = None   # part_number of the replacement, if any
    notes: str = ""


VEHICLES = [
    Vehicle("HLX18SR5", "Toyota", "Hilux", "SR5", 2018),
    Vehicle("HLX19SR5", "Toyota", "Hilux", "SR5", 2019),   # facelift year
    Vehicle("CX520GSX", "Mazda", "CX-5", "GSX", 2020),
    Vehicle("RGR21XLT", "Ford", "Ranger", "XLT", 2021),
]

PART_TYPES_SIDED = [
    "headlamp",
    "tail_lamp",
    "front_fender",
    "front_door_shell",
    "wing_mirror",
]

PART_TYPES_UNSIDED = [
    "front_bumper_cover",
    "bonnet",
    "radiator_support",
    "windscreen",
    "grille",
]


def _build_catalogue() -> list[Part]:
    parts: list[Part] = []

    for v in VEHICLES:
        for pt in PART_TYPES_SIDED:
            for side in ("left", "right"):
                pn = f"{v.vehicle_id}-{pt.upper()}-{side[0].upper()}"
                parts.append(Part(pn, v.vehicle_id, pt, side))

        for pt in PART_TYPES_UNSIDED:
            pn = f"{v.vehicle_id}-{pt.upper()}"
            parts.append(Part(pn, v.vehicle_id, pt, None))

    # --- Inject a mid-production supersession on the Hilux ---
    # The 2018 SR5 front bumper cover was superseded by a revised part
    # (fog lamp cutout change) that's ALSO used on the 2019 model.
    old_bumper = "HLX18SR5-FRONT_BUMPER_COVER"
    new_bumper = "HLX18SR5-FRONT_BUMPER_COVER-REV2"
    parts = [
        Part(new_bumper, "HLX18SR5", "front_bumper_cover", None,
             notes="Revised fog-lamp cutout, fits 2018 SR5 built after Aug 2018 and all 2019 SR5")
        if p.part_number == old_bumper
        else p
        for p in parts
    ]
    # mark the *original* pre-Aug-2018 part as superseded and still present
    parts.append(
        Part(old_bumper, "HLX18SR5", "front_bumper_cover", None,
             superseded_by=new_bumper,
             notes="Pre-Aug-2018 build only. Superseded by REV2.")
    )

    # --- Inject a headlamp supersession too (common real-world pattern) ---
    old_headlamp_l = "HLX18SR5-HEADLAMP-L"
    new_headlamp_l = "HLX18SR5-HEADLAMP-L-REV2"
    parts.append(
        Part(new_headlamp_l, "HLX18SR5", "headlamp", "left",
             notes="LED-projector revision, fits 2018 SR5 built after Aug 2018 and all 2019 SR5")
    )
    parts = [
        Part(p.part_number, p.vehicle_id, p.part_type, p.side,
             superseded_by=new_headlamp_l,
             notes="Pre-Aug-2018 build only. Superseded by REV2.")
        if p.part_number == old_headlamp_l
        else p
        for p in parts
    ]

    return parts


CATALOGUE: list[Part] = _build_catalogue()


def find_parts(vehicle_id: str, part_type: str, side: Optional[str] = None) -> list[Part]:
    """Raw lookup against the full catalogue, superseded parts included."""
    return [
        p for p in CATALOGUE
        if p.vehicle_id == vehicle_id
        and p.part_type == part_type
        and (side is None or p.side == side)
    ]


def is_sided(part_type: str) -> bool:
    return part_type in PART_TYPES_SIDED


def all_part_types() -> list[str]:
    return PART_TYPES_SIDED + PART_TYPES_UNSIDED


if __name__ == "__main__":
    print(f"{len(CATALOGUE)} parts across {len(VEHICLES)} vehicles")
    superseded = [p for p in CATALOGUE if p.superseded_by]
    print(f"{len(superseded)} parts have an active supersession")
