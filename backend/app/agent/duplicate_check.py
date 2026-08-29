"""Validates the local `nlp` service's `/find-duplicates` response into
typed args — same "trust the shape once validated, not before" role
`agent/dictation.py::parse_transcript` plays for `/structure`. A distinct
module rather than added to `dictation.py`: this is a different
capability (fridge-stock consistency, not dictation) that happens to
share the same underlying model/service.

Matching real fridge-stock items to the names this returns, and deciding
what to do with a group (dismissed pairs, quantity merging, ...) is the
service layer's job (`services/fridge_stock_service.py`) — this module
only ever sees names, never `FridgeStockItem`s.
"""

from pydantic import BaseModel, Field, ValidationError

from app.agent import nlp_client
from app.services.exceptions import AgentResponseInvalidError


class DuplicateGroupArgs(BaseModel):
    # No `min_length` here — mirrors `nlp/main.py::DuplicateGroup`'s own
    # relaxation: the grammar constraint doesn't actually enforce array
    # length, so a stray one-name "group" is a real possibility, and
    # `FridgeStockService.find_merge_suggestions` already turns a group
    # with fewer than 2 resolvable names into zero merge pairs on its
    # own — no need to fail the whole response over one bad group.
    names: list[str] = Field(default_factory=list)
    suggested_name: str


class FindDuplicatesResponseArgs(BaseModel):
    groups: list[DuplicateGroupArgs] = Field(default_factory=list)


def find_duplicate_groups(*, ingredient_names: list[str]) -> list[DuplicateGroupArgs]:
    if len(ingredient_names) < 2:
        return []

    raw = nlp_client.find_duplicates(ingredient_names=ingredient_names)
    try:
        return FindDuplicatesResponseArgs.model_validate(raw).groups
    except ValidationError as exc:
        raise AgentResponseInvalidError(
            "The local duplicate-check service returned data that didn't match the "
            "expected shape."
        ) from exc
