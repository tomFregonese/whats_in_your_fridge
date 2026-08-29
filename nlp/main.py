"""Local NLP structuring service for voice dictation — turns a dictated
grocery-list transcript into structured ingredient+quantity rows using a
small, grammar-constrained local chat model, running as its own Docker
Compose service (see `docker-compose.yml`'s `nlp` service), reachable
only from `api` over Docker's internal network, never exposed to the
host.

Deliberately outside the backend's own layered architecture, same
reasoning as `stt/main.py` — a single-purpose, stateless inference shim
with no business logic and no database (see
`backend/app/agent/nlp_client.py`, the only caller).

Self-contained on purpose, like `stt/main.py` — does NOT import from
`backend/app`. `StructuredItem`/`StructureResponse` below are this
service's own copy of the shape
`backend/app/agent/output_schema.py::DictatedItemArgs`/
`EnregistrerIngredientsArgs` define — keep the two in sync by hand.

Uses grammar-constrained decoding (`response_format={"type":
"json_object", "schema": ...}`, which builds a GBNF grammar from the
schema and constrains every generated token to it) — the model is
structurally incapable of emitting JSON outside this shape, which is why
there's no retry loop here or in the caller (contrast with the old
OpenRouter tool-calling path this replaces, which needed one because
nothing forced the model to comply).

Model: Qwen2.5-1.5B-Instruct, `q4_k_m` GGUF (~1GB) — good French/English
instruction-following at a size that stays fast on CPU for a short
prompt and short JSON output. See `download_model.py` to swap it for a
different one.
"""

import json
import threading

from fastapi import FastAPI, HTTPException
from llama_cpp import Llama
from pydantic import BaseModel, Field

from download_model import load_model

# A dictated list is short — items rarely run past a couple dozen tokens
# of JSON each — so this is generous headroom, not a real ceiling; kept
# low specifically so a stalled/looping generation can't run long.
MAX_OUTPUT_TOKENS = 256

app = FastAPI(title="What's in your fridge? — local dictation structuring")

_model: Llama | None = None
_model_lock = threading.Lock()
# Separate from `_model_lock` on purpose — that one only guards the lazy
# *load*. This one serializes actual inference calls: with segments now
# processed as soon as they're dictated (see the frontend's `WavRecorder`
# silence-based cutting), two `/structure` requests really can land
# concurrently and — since FastAPI runs sync route handlers in a
# threadpool — really can call into the same loaded `Llama` instance from
# two threads at once. `llama-cpp-python` isn't documented as safe for
# concurrent inference calls on one instance (the underlying llama.cpp
# context is mutated during generation), so this isn't a risk worth
# gambling on — each call is short (~1s), so serializing them costs
# little.
_inference_lock = threading.Lock()


def _get_model() -> Llama:
    """Loads (once) and caches the `Llama` instance — safe to call
    concurrently, only ever loads it once. Same lazy-singleton shape as
    `stt/main.py::_get_model`."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:  # re-check: another thread may have won the race
                _model = load_model()
    return _model


class StructureRequest(BaseModel):
    transcript: str = Field(min_length=1)


class StructuredItem(BaseModel):
    """Mirrors `agent/output_schema.py::DictatedItemArgs` field-for-field
    — keep the two in sync by hand."""

    ingredient_name: str = Field(min_length=1)
    quantity_value: float | None = None
    quantity_unit: str | None = None
    quantity_raw: str | None = None


class StructureResponse(BaseModel):
    """Mirrors `agent/output_schema.py::EnregistrerIngredientsArgs`
    field-for-field — keep the two in sync by hand."""

    items: list[StructuredItem] = Field(default_factory=list)


# The JSON schema handed to the model as a grammar constraint (see the
# module docstring) — generated once at import time, not per-request.
_RESPONSE_SCHEMA = StructureResponse.model_json_schema()

_SYSTEM_PROMPT = (
    "You split a dictated grocery list into structured items. The transcript may be in "
    "French, English, or a mix, informally phrased, and may run several items together in "
    "one sentence. Return one entry per distinct ingredient.\n"
    "Set quantity_unit ONLY when the speaker actually said a unit of measurement (kg, g, "
    "L, mL, boîte/can, paquet/pack, ...). A bare count of items (\"dix pommes de terre\", "
    "\"three carrots\") has NO unit — leave quantity_unit null and put the number in "
    "quantity_value. Never invent \"kg\" or any other unit that wasn't said — this is the "
    "single most common mistake, watch for it.\n"
    "If the amount isn't a clear number (\"a couple\", \"une pincée\", \"un peu de\"), leave "
    "quantity_value and quantity_unit both null and put the phrase as-is in quantity_raw.\n"
    "Examples:\n"
    '"dix pommes de terre" -> {"ingredient_name": "pommes de terre", "quantity_value": 10, '
    '"quantity_unit": null, "quantity_raw": null}\n'
    '"2 kg de carottes" -> {"ingredient_name": "carottes", "quantity_value": 2, '
    '"quantity_unit": "kg", "quantity_raw": null}\n'
    '"un peu de beurre" -> {"ingredient_name": "beurre", "quantity_value": null, '
    '"quantity_unit": null, "quantity_raw": "un peu"}\n'
    "Respond with JSON only."
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/structure")
def structure(request: StructureRequest) -> StructureResponse:
    model = _get_model()
    with _inference_lock:
        completion = model.create_chat_completion(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": request.transcript},
            ],
            response_format={"type": "json_object", "schema": _RESPONSE_SCHEMA},
            temperature=0.0,
            max_tokens=MAX_OUTPUT_TOKENS,
        )
    content = completion["choices"][0]["message"]["content"]

    try:
        return StructureResponse.model_validate(json.loads(content))
    except (json.JSONDecodeError, ValueError) as exc:
        # Near-impossible given the grammar constraint above — the one
        # realistic way to still land here is hitting `max_tokens` before
        # the JSON closes. The caller (`agent/nlp_client.py`) treats any
        # non-2xx response the same as "service unreachable".
        raise HTTPException(
            status_code=500, detail=f"Local model produced invalid JSON: {exc}"
        ) from exc
