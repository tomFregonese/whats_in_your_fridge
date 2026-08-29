"""Downloads and loads the Whisper model this service bakes into its
image at build time (see `Dockerfile`) — kept in its own file, separate
from `main.py`, so `RUN python download_model.py` only reruns when
*this* file's content changes, not on every unrelated edit to `main.py`
(the transcription endpoint, the health check, ...).

`main.py` imports `load_model()`/`MODEL_SIZE` from here rather than
duplicating them, so there's exactly one place that knows how this model
gets loaded.
"""

from faster_whisper import WhisperModel

# The best speed/accuracy tradeoff of the three sizes tried (`tiny`
# mis-transcribed enough to matter, `small` was ~3x slower for barely
# better accuracy on a short grocery list), so there's nothing to choose
# and no setting for it.
MODEL_SIZE = "base"
MODEL_DOWNLOAD_ROOT = "/models"


def load_model() -> WhisperModel:
    return WhisperModel(
        MODEL_SIZE, download_root=MODEL_DOWNLOAD_ROOT, device="cpu", compute_type="int8"
    )


# Bakes the model into the image at build time (see Dockerfile) — run
# once, standalone, *before* `main.py` is even copied into the image, so
# editing application code afterwards never reruns this step.
if __name__ == "__main__":
    load_model()
