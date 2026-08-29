"""Local speech-to-text service — a thin FastAPI wrapper around
`faster-whisper`, running as its own Docker Compose service (see
`docker-compose.yml`'s `stt` service), reachable only from the `api`
service over Docker's internal network, never exposed to the host.

Deliberately outside the backend's own layered architecture
(dto/domain/persistence/services/controllers): this is a single-purpose,
stateless inference shim with no business logic and no database — the
`api` service is where the app's actual layering lives (see
`backend/app/agent/stt_client.py`, the only caller of this service).

Baked into the Docker image at build time (see `Dockerfile` and
`download_model.py`) so the container works offline from first boot —
never downloaded at request time. Loaded into memory lazily, on first
request, and kept cached afterward.
"""

import base64
import binascii
import tempfile
import threading

from fastapi import FastAPI, HTTPException
from faster_whisper import WhisperModel
from pydantic import BaseModel, Field

from download_model import load_model

# Whisper "base" has no idea this audio is a grocery list — left to
# guess cold, it reliably favors a more common word over the right one
# when they sound alike (empirically: "carrots" -> "carats"). Passed as
# `initial_prompt` below, this biases it toward food vocabulary in the
# two languages this household actually dictates in, which measurably
# fixes that class of mistake — for free: no bigger/slower model needed,
# same latency. Deliberately not exhaustive (the point is nudging the
# language model's priors, not enumerating every ingredient) and
# deliberately bilingual rather than tied to one detected language,
# since `language=None` below means either could come up.
INITIAL_PROMPT = (
    "Grocery list: potatoes, carrots, onions, tomatoes, milk, pasta, rice, bread, "
    "cheese, eggs, chicken, apples, bananas. "
    "Liste de courses : pommes de terre, carottes, oignons, tomates, lait, pâtes, "
    "riz, pain, fromage, œufs, poulet, pommes, bananes."
)

app = FastAPI(title="What's in your fridge? — local speech-to-text")

_model: WhisperModel | None = None
_model_lock = threading.Lock()
# Separate from `_model_lock` on purpose — that one only guards the lazy
# *load*. This one serializes actual inference calls: with dictation now
# split into segments as they're spoken (see the frontend's `WavRecorder`
# silence-based cutting), two `/transcribe` requests really can land
# concurrently and — since FastAPI runs sync route handlers in a
# threadpool — really can call into the same loaded `WhisperModel`
# instance from two threads at once. Not something to gamble on without
# checking `faster-whisper`'s exact concurrent-call contract; each call
# is short, so serializing them costs little.
_inference_lock = threading.Lock()


def _get_model() -> WhisperModel:
    """Loads (once) and caches the `WhisperModel` — safe to call
    concurrently, only ever loads it once."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:  # re-check: another thread may have won the race
                _model = load_model()
    return _model


class TranscribeRequest(BaseModel):
    audio_base64: str = Field(min_length=1)
    audio_format: str = Field(min_length=1)


class TranscribeResponse(BaseModel):
    text: str


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/transcribe")
def transcribe(request: TranscribeRequest) -> TranscribeResponse:
    try:
        audio_bytes = base64.b64decode(request.audio_base64)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid base64 audio: {exc}") from exc

    model = _get_model()

    with tempfile.NamedTemporaryFile(suffix=f".{request.audio_format}") as tmp:
        tmp.write(audio_bytes)
        tmp.flush()
        # `language=None` autodetects — dictation may be in any language,
        # not necessarily whatever the browser's UI happens to be in.
        #
        # `model.transcribe(...)` returns `segments` as a *generator* —
        # the actual decoding happens while it's iterated, not at this
        # call site — so the lock has to wrap the join below too, or it
        # silently protects nothing while looking correct.
        with _inference_lock:
            segments, _info = model.transcribe(
                tmp.name, language=None, initial_prompt=INITIAL_PROMPT
            )
            text = " ".join(segment.text.strip() for segment in segments).strip()

    return TranscribeResponse(text=text)
