from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DishIdea:
    """One dish idea proposed during the `IDEAS` phase — name and a
    one-line description only, deliberately without ingredients or steps
    (see `app.agent.loop.run_ideas`). Never persisted with its own
    identity: it lives only inside `AgentRun.proposed_ideas_json` while
    awaiting the user's selection, then is either discarded or turned into
    a full `Suggestion` by the `RECIPES` phase.
    """

    dish_name: str
    description: str
    leftover_of_dish_name: str | None = None
    """Exact `dish_name` of another idea in the same shortlist whose
    leftovers this one reuses — see `agent/output_schema.py::IdeeArgs.restes_de`.
    `None` for a standalone idea."""
    transformation_note: str | None = None
    """How the leftovers are transformed into this dish (e.g. "turned into
    a gratin") — see `agent/output_schema.py::IdeeArgs.transformation`. Set
    whenever `leftover_of_dish_name` is."""
