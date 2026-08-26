"""Tool schemas for the agent loop.

Exactly two tools, matching the output contract: every final answer must
go through `proposer_plats`; anything ambiguous must go through
`demander_precision` instead of the model guessing (see `agent/prompts.py`
for the instruction that tells it so).
"""

from openai.types.chat import ChatCompletionToolParam

from app.agent.output_schema import DemanderPrecisionArgs, ProposerPlatsArgs

DEMANDER_PRECISION = "demander_precision"
PROPOSER_PLATS = "proposer_plats"


def build_tools() -> list[ChatCompletionToolParam]:
    return [
        {
            "type": "function",
            "function": {
                "name": DEMANDER_PRECISION,
                "description": (
                    "Ask the user a clarifying question instead of guessing when the "
                    "fridge contents or the request are ambiguous."
                ),
                "parameters": DemanderPrecisionArgs.model_json_schema(),
            },
        },
        {
            "type": "function",
            "function": {
                "name": PROPOSER_PLATS,
                "description": "Propose one or more dishes to cook from the fridge contents.",
                "parameters": ProposerPlatsArgs.model_json_schema(),
            },
        },
    ]
