"""SSE event generator for voice dictation.

A plain generator, not a background thread — unlike `streaming_service.py`
(meal suggestions), which genuinely needs a thread+queue to bridge
`agent/client.stream_complete_with_tools`'s synchronous
`reasoning_callback` (firing from deep inside that function's own
blocking network call) into something the outer generator can `yield`
live. Dictation's structuring step used to have the same shape when it
also went through OpenRouter, but now runs against the local `nlp`
service as one plain blocking call with no callback (see
`agent/dictation.py`) — so there's nothing left for a thread to bridge.

The actual "flush each event to the client as it happens" mechanism was
never the thread anyway — it's Starlette's `iterate_in_threadpool` around
the sync generator `controllers/fridge_stock.py` hands to
`StreamingResponse` (see that module's docstring), which already runs
each blocking step here off the event loop and sends each yielded event
before pulling the next. A thread bridging a callback into a queue was
solving a narrower problem (multiple events arriving from *inside* one
blocking call) that no longer exists here.
"""

from collections.abc import Iterator

from app.agent import dictation, stt_client
from app.agent.output_schema import DictatedItemArgs


def _item_to_dict(item: DictatedItemArgs) -> dict[str, object]:
    return {
        "ingredient_name": item.ingredient_name,
        "quantity_value": item.quantity_value,
        "quantity_unit": item.quantity_unit,
        "quantity_raw": item.quantity_raw,
    }


def stream_dictation(*, audio_base64: str, audio_format: str) -> Iterator[dict[str, object]]:
    """Runs the transcribe-then-structure pipeline, yielding event dicts
    as they happen: `transcribing` -> `transcribed` (carries the raw
    text) -> `items` (the final proposal) — or `error` in place of
    `items` if the pipeline fails at either step. Always ends with
    `done`, mirroring `streaming_service.py`'s terminal event.
    """
    try:
        yield {"type": "transcribing"}
        transcript = stt_client.transcribe(audio_base64=audio_base64, audio_format=audio_format)
        yield {"type": "transcribed", "text": transcript}

        items = dictation.parse_transcript(transcript=transcript)
        yield {"type": "items", "items": [_item_to_dict(item) for item in items]}
    except Exception as exc:
        yield {"type": "error", "detail": str(exc)}
    finally:
        yield {"type": "done"}
