"""Downloads and loads the GGUF model this service bakes into its image
at build time (see `Dockerfile`) — kept in its own file, separate from
`main.py`, so `RUN python download_model.py` only reruns when *this*
file's content changes. Before this split, the download lived in
`main.py` itself, so editing anything there at all (the system prompt,
`n_threads`, the endpoint...) busted the same Docker layer and forced a
redundant ~1GB re-download on every unrelated change — expensive on a
slow connection, which is exactly when it hurts most.

`main.py` imports `load_model()` and the model constants from here
rather than duplicating them, so there's exactly one place that knows
how this model gets loaded. Swap `MODEL_REPO`/`MODEL_FILENAME` here for
a different HF GGUF repo (e.g. the 0.5B variant for more speed, or a 3B
for more accuracy) — nothing else needs to change.
"""

import os

from huggingface_hub import hf_hub_download
from llama_cpp import Llama

MODEL_REPO = "Qwen/Qwen2.5-1.5B-Instruct-GGUF"
MODEL_FILENAME = "qwen2.5-1.5b-instruct-q4_k_m.gguf"
MODEL_DOWNLOAD_ROOT = "/models"
CONTEXT_SIZE = 2048


def load_model() -> Llama:
    """Downloads (a no-op once baked into the image at build time) then
    loads the GGUF file."""
    model_path = hf_hub_download(
        repo_id=MODEL_REPO, filename=MODEL_FILENAME, local_dir=MODEL_DOWNLOAD_ROOT
    )
    # `llama-cpp-python` otherwise defaults `n_threads` to roughly half
    # the visible CPU count, not all of it — measured ~5x slower on this
    # container's default vs. explicitly using every core it's actually
    # given. This container does nothing else, so there's no reason to
    # hold any back.
    return Llama(
        model_path=model_path,
        n_ctx=CONTEXT_SIZE,
        n_threads=os.cpu_count() or 4,
        verbose=False,
    )


# Bakes the model into the image at build time (see Dockerfile) — run
# once, standalone, *before* `main.py` is even copied into the image, so
# editing application code afterwards never reruns this step.
if __name__ == "__main__":
    load_model()
