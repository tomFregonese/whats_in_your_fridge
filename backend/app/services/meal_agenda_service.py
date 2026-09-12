"""Deterministic batch-cooking agenda scheduler — pure Python, no LLM
involved (see the project plan's "never let the model do the arithmetic"
stance, same as `agent/allergy_check.py`/`agent/equipment_check.py`).

Every dish is assumed cooked in one session on day 0; this decides which
day each dish is *eaten* on, prioritizing the most perishable dishes for
the earliest days and falling back to the freezer (bounded by household
capacity) for anything that would otherwise spoil before its turn.
"""

from dataclasses import dataclass

from app.domain.suggestion import AgendaEntry, AgendaStorage


@dataclass
class DishForAgenda:
    """The only inputs `build_agenda` needs from a persisted `Suggestion`
    — kept separate from the BO itself so this module stays independently
    testable without constructing a full `Suggestion`."""

    suggestion_id: int
    fridge_days: int
    freezer_friendly: bool


def build_agenda(
    dishes: list[DishForAgenda], days: int, freezer_capacity_slots: int | None
) -> list[AgendaEntry]:
    """Assigns a dish to eat on each day in `range(days)`.

    - Dishes are sorted by ascending `fridge_days` (most perishable
      first). The schedule has `max(len(dishes), days)` slots — one dish
      per day when they match, several dishes sharing a day when there
      are more dishes than days, and the sorted dish list cycling back to
      its start to refill the remaining days when there are fewer dishes
      than days (a single dish batch gets an entry on every day).
    - A dish assigned to `day_index <= fridge_days` stays `FRESH`.
      Otherwise it needs the freezer to survive to its day: `FROZEN` if
      `freezer_friendly` and freezer budget remains (`freezer_capacity_slots`,
      `None` = unlimited), else `AT_RISK` with an explanatory `warning`.

    Returns entries sorted by `day_index` (stable, so dishes sharing a day
    keep their perishability order). Empty `dishes` or non-positive `days`
    yields an empty agenda.
    """
    if not dishes or days <= 0:
        return []

    ordered = sorted(dishes, key=lambda dish: dish.fridge_days)
    freezer_budget = freezer_capacity_slots
    total_slots = max(len(ordered), days)

    entries: list[AgendaEntry] = []
    for index in range(total_slots):
        dish = ordered[index % len(ordered)]
        day_index = index % days
        storage: AgendaStorage
        warning: str | None = None

        if day_index <= dish.fridge_days:
            storage = AgendaStorage.FRESH
        elif dish.freezer_friendly and (freezer_budget is None or freezer_budget > 0):
            storage = AgendaStorage.FROZEN
            if freezer_budget is not None:
                freezer_budget -= 1
        else:
            storage = AgendaStorage.AT_RISK
            reason = (
                "no freezer space left"
                if dish.freezer_friendly
                else "it doesn't freeze well"
            )
            warning = (
                f"This dish keeps {dish.fridge_days} day(s) in the fridge but is scheduled "
                f"for day {day_index}, and {reason} — eat it earlier or reorder the agenda."
            )

        entries.append(
            AgendaEntry(
                id=None,
                meal_plan_id=None,
                day_index=day_index,
                suggestion_id=dish.suggestion_id,
                storage=storage,
                warning=warning,
            )
        )

    entries.sort(key=lambda entry: entry.day_index)
    return entries
