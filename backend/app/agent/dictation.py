"""One-shot structuring of a dictated fridge update into discrete items,
via the local `nlp` service (see `agent/nlp_client.py`) — grammar-
constrained there, so the response is structurally guaranteed to match
`EnregistrerIngredientsArgs`'s shape, which is why there's no retry loop
here, unlike the OpenRouter tool-calling path this replaces (see git
history: that version needed up to `MAX_ATTEMPTS` round trips because
nothing forced the model to comply with the tool contract).

The transcript itself comes from the local Whisper service (see
`agent/stt_client.py`), same as before this change — audio never left
this machine to begin with. What changed is the *structuring* step: it
used to go out to OpenRouter (the household's configured `:free` chat
model, same one used for meal suggestions); now it's entirely local too,
so voice dictation as a whole no longer needs an OpenRouter token or
internet access at all. Meal suggestions are unaffected — that feature
still uses `agent/loop.py` / `agent/client.py` against OpenRouter.
"""

from pydantic import ValidationError

from app.agent import nlp_client
from app.agent.output_schema import DictatedItemArgs, EnregistrerIngredientsArgs
from app.agent.quantity_sanity_check import sanitize_quantities
from app.services.exceptions import AgentResponseInvalidError


def parse_transcript(*, transcript: str) -> list[DictatedItemArgs]:
    raw = nlp_client.structure(transcript=transcript)
    try:
        items = EnregistrerIngredientsArgs.model_validate(raw).items
    except ValidationError as exc:
        # Only plausible if the `nlp` service's own copy of this shape
        # (see `nlp/main.py`'s `StructureResponse`) has drifted from
        # `EnregistrerIngredientsArgs` — the grammar constraint on the
        # service side already rules out arbitrary malformed JSON.
        raise AgentResponseInvalidError(
            "The local structuring service returned data that didn't match the expected shape."
        ) from exc

    # The shape is trustworthy (validated above); the content isn't —
    # see `quantity_sanity_check.py` for why.
    sanitize_quantities(items, transcript)
    return items
