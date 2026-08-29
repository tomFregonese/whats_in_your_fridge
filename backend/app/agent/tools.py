"""Tool schemas for the agent loop.

`demander_precision` is available in both phases. Which "final answer"
tool is offered alongside it depends on the phase (see `AgentRunPhase`):
`proposer_idees` in `IDEAS` (a shortlist of names + descriptions, no
ingredients/steps) or `proposer_plats` in `RECIPES` (the full recipe for
whichever idea(s) the user already picked) — see `agent/prompts.py` for
the phase-specific instructions that tell the model so.

Voice dictation used to have a third tool here (`enregistrer_ingredients`)
for its own OpenRouter tool-calling loop — that loop now runs against a
local, grammar-constrained model instead (see `agent/dictation.py`),
which doesn't go through OpenAI-style tool-calling at all, so there's
nothing to declare here for it any more.
"""

from openai.types.chat import ChatCompletionToolParam

from app.agent.output_schema import (
    DemanderPrecisionArgs,
    ProposerIdeesArgs,
    ProposerPlatsArgs,
)
from app.domain.agent_run import AgentRunPhase

DEMANDER_PRECISION = "demander_precision"
PROPOSER_IDEES = "proposer_idees"
PROPOSER_PLATS = "proposer_plats"

_DEMANDER_PRECISION_TOOL: ChatCompletionToolParam = {
    "type": "function",
    "function": {
        "name": DEMANDER_PRECISION,
        "description": (
            "Ask the user a clarifying question instead of guessing when the "
            "fridge contents or the request are ambiguous."
        ),
        "parameters": DemanderPrecisionArgs.model_json_schema(),
    },
}

_PROPOSER_IDEES_TOOL: ChatCompletionToolParam = {
    "type": "function",
    "function": {
        "name": PROPOSER_IDEES,
        "description": (
            "Propose a shortlist of dish ideas — name and a one-line description "
            "only, no ingredients or steps yet — for the user to choose from."
        ),
        "parameters": ProposerIdeesArgs.model_json_schema(),
    },
}

_PROPOSER_PLATS_TOOL: ChatCompletionToolParam = {
    "type": "function",
    "function": {
        "name": PROPOSER_PLATS,
        "description": (
            "Generate the full recipe (ingredients and steps) for the dish(es) "
            "the user has already selected."
        ),
        "parameters": ProposerPlatsArgs.model_json_schema(),
    },
}


def build_tools(phase: AgentRunPhase) -> list[ChatCompletionToolParam]:
    final_tool = _PROPOSER_IDEES_TOOL if phase == AgentRunPhase.IDEAS else _PROPOSER_PLATS_TOOL
    return [_DEMANDER_PRECISION_TOOL, final_tool]
