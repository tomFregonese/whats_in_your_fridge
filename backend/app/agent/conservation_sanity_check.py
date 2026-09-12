"""Deterministic, code-level guard on the `fridge_days` estimate a dish
comes back with — same stance as `agent/quantity_sanity_check.py`: a
number the model invents is never trusted outright when it's cheap to
bound.

This isn't a food-safety authority (there's no transcript or reference
value to check the estimate against, unlike `quantity_sanity_check.py`) —
just a clamp against an implausible value (e.g. `0`, or `365`) that would
otherwise reach `services/meal_agenda_service.py`'s scheduling math and
produce a nonsensical agenda.
"""

from app.agent.output_schema import PlatArgs

MIN_FRIDGE_DAYS = 1
MAX_FRIDGE_DAYS = 10


def sanitize_fridge_days(plats: list[PlatArgs]) -> None:
    """Mutates each `plat.fridge_days` in place, clamping it to
    `[MIN_FRIDGE_DAYS, MAX_FRIDGE_DAYS]`."""
    for plat in plats:
        plat.fridge_days = max(MIN_FRIDGE_DAYS, min(MAX_FRIDGE_DAYS, plat.fridge_days))
