"""Deterministic batch-cooking agenda scheduler — pure Python, no LLM
involved (see the project plan's "never let the model do the arithmetic"
stance, same as `agent/allergy_check.py`/`agent/equipment_check.py`).

Every *root* dish (one that doesn't transform another's leftovers) is
assumed cooked together, in one batch-cooking session on day 0 — this
decides which day each one is *eaten* on, prioritizing the most perishable
for the earliest days and falling back to the freezer (bounded by household
capacity) for anything that would otherwise spoil before its turn. A dish
that transforms a previous one's leftovers (see
`DishForAgenda.leftover_of_suggestion_id`) is instead its own, separate
cooking effort, freshly made on the day it's placed — always right after
the dish it reuses. A dish repeated verbatim to fill out remaining days (no
transformation was proposed for it) is always flagged with an explicit
warning — eating an unchanged dish again is never a silent fallback, see
the project's batch-cooking-leftovers requirement.
"""

from dataclasses import dataclass

from app.domain.suggestion import AgendaEntry, AgendaStorage


@dataclass
class DishForAgenda:
    """The only inputs `build_agenda` needs from a persisted `Suggestion`
    — kept separate from the BO itself so this module stays independently
    testable without constructing a full `Suggestion`."""

    suggestion_id: int
    dish_name: str
    fridge_days: int
    freezer_friendly: bool
    leftover_of_suggestion_id: int | None = None
    """Mirrors `Suggestion.leftover_of_suggestion_id` — another dish in
    this same batch (by id) whose leftovers this one transforms. Sanitized
    defensively here (dangling/self/cyclical/fanned-out references are
    dropped, degrading the dish to a root) since it ultimately comes from
    an LLM's by-name reference, resolved elsewhere."""


def build_agenda(
    dishes: list[DishForAgenda], days: int, freezer_capacity_slots: int | None
) -> list[AgendaEntry]:
    """Assigns a dish to eat on each day in `range(days)`.

    - Dishes are grouped into leftover-transformation chains (a root dish
      followed by whichever other dish transforms its leftovers, and so on
      — see `DishForAgenda.leftover_of_suggestion_id`), each chain ordered
      root-first. Chains (roots, for dishes with no incoming link) are then
      sorted by the root's ascending `fridge_days` (most perishable first)
      and flattened into one list — with no chains at all, this is exactly
      today's plain `sorted(dishes, key=fridge_days)`.
    - The schedule has `max(len(flattened), days)` slots: one entry per day
      when they match, several sharing a day when there are more entries
      than days, and the flattened list cycling back to its start when
      there are fewer entries than days. Every entry from a second pass
      onward is a **literal repeat** of that chain's last dish (never a
      fresh variant) and always carries an explicit warning saying so —
      see the module docstring.
    - A root dish's "cooked" day is always day 0 (the single batch-cooking
      session), regardless of which day it's actually eaten on; a
      transformation dish's "cooked" day is its own placement day (its own,
      separate cooking effort). Either way, that day is `FRESH`; each day
      after it is `FRESH` while `day_index - cooked_day <= fridge_days`,
      then needs the freezer to survive: `FROZEN` if `freezer_friendly` and
      freezer budget remains (`freezer_capacity_slots`, `None` = unlimited),
      else `AT_RISK` with an explanatory `warning`. A repeat keeps counting
      from its dish's original "cooked" day, same as any other occurrence
      of it.

    Returns entries sorted by `day_index` (stable, so dishes sharing a day
    keep their chain/perishability order). Empty `dishes` or non-positive
    `days` yields an empty agenda.
    """
    if not dishes or days <= 0:
        return []

    parent_of = _sanitize_leftover_links(dishes)
    ordered = _flatten_chains(dishes, parent_of)
    freezer_budget = freezer_capacity_slots
    total_slots = max(len(ordered), days)

    prepared_day_by_id: dict[int, int] = {}

    entries: list[AgendaEntry] = []
    for index in range(total_slots):
        dish = ordered[index % len(ordered)]
        day_index = index % days
        is_repeat = index >= len(ordered)

        if is_repeat:
            prepared_day = prepared_day_by_id[dish.suggestion_id]
        elif dish.suggestion_id in parent_of:
            # A transformation is its own cooking effort, freshly made the
            # day it's placed.
            prepared_day = day_index
        else:
            # Every root is cooked together in the single batch-cooking
            # session on day 0, however far off its own turn to be eaten.
            prepared_day = 0
        prepared_day_by_id.setdefault(dish.suggestion_id, prepared_day)

        storage: AgendaStorage
        warning: str | None = None

        if day_index - prepared_day <= dish.fridge_days:
            storage = AgendaStorage.FRESH
        elif dish.freezer_friendly and (freezer_budget is None or freezer_budget > 0):
            storage = AgendaStorage.FROZEN
            if freezer_budget is not None:
                freezer_budget -= 1
        else:
            storage = AgendaStorage.AT_RISK
            reason = (
                "no freezer space left" if dish.freezer_friendly else "it doesn't freeze well"
            )
            warning = (
                f"This dish keeps {dish.fridge_days} day(s) in the fridge but is scheduled "
                f"for day {day_index}, and {reason} — eat it earlier or reorder the agenda."
            )

        if is_repeat:
            repeat_warning = (
                f'No new variant was proposed for this day — this repeats "{dish.dish_name}" '
                "exactly, with no transformation."
            )
            warning = f"{repeat_warning} {warning}" if warning else repeat_warning

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


def _sanitize_leftover_links(dishes: list[DishForAgenda]) -> dict[int, int]:
    """Validates `DishForAgenda.leftover_of_suggestion_id` into a
    `child_id -> parent_id` map, dropping (degrading the dish to a root)
    any self-reference, reference to a dish outside this batch, reference
    that would close a cycle, or every claim on a parent beyond the first
    (by ascending `suggestion_id`, for determinism) — the product's ask is
    one linear reuse chain per dish, not a tree.
    """
    by_id = {dish.suggestion_id: dish for dish in dishes}
    parent_of: dict[int, int] = {}
    claimed_parents: set[int] = set()

    for dish in sorted(dishes, key=lambda d: d.suggestion_id):
        parent_id = dish.leftover_of_suggestion_id
        if parent_id is None or parent_id == dish.suggestion_id or parent_id not in by_id:
            continue
        if parent_id in claimed_parents:
            continue

        visited = {dish.suggestion_id}
        cursor: int | None = parent_id
        cyclical = False
        while cursor is not None:
            if cursor in visited:
                cyclical = True
                break
            visited.add(cursor)
            cursor = parent_of.get(cursor)
        if cyclical:
            continue

        parent_of[dish.suggestion_id] = parent_id
        claimed_parents.add(parent_id)

    return parent_of


def _flatten_chains(
    dishes: list[DishForAgenda], parent_of: dict[int, int]
) -> list[DishForAgenda]:
    """Root dishes (no parent, after sanitizing) sorted by ascending
    `fridge_days`, each immediately followed by its full chain of
    transformations in order — with no chains at all, this is exactly
    `sorted(dishes, key=fridge_days)`.
    """
    by_id = {dish.suggestion_id: dish for dish in dishes}
    child_of_parent = {parent_id: child_id for child_id, parent_id in parent_of.items()}

    roots = [dish for dish in dishes if dish.suggestion_id not in parent_of]
    roots.sort(key=lambda dish: dish.fridge_days)

    ordered: list[DishForAgenda] = []
    for root in roots:
        cursor: DishForAgenda | None = root
        while cursor is not None:
            ordered.append(cursor)
            next_id = child_of_parent.get(cursor.suggestion_id)
            cursor = by_id.get(next_id) if next_id is not None else None
    return ordered
