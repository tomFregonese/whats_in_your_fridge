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
