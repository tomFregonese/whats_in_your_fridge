FROM python:3.12-slim

# llama-cpp-python doesn't ship a prebuilt wheel for every platform this
# image might get built on (notably arm64 hosts, e.g. building directly
# on Apple Silicon) — build tooling is installed unconditionally so
# `pip install` below always succeeds, compiling from source when no
# prebuilt wheel matches, at the cost of a slower first build.
# `upgrade` pulls in any Debian security patches released since this
# base image was built — otherwise the image stays pinned to whatever was
# current the day python:3.12-slim was last published.
RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends build-essential cmake git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
# A timeout well above pip's 15s default, set as an env var (not just a
# `--timeout` flag) so it also reaches the isolated build environment's
# own nested `pip install` for `llama-cpp-python`'s build dependencies
# (scikit-build-core, cmake, ...) — that subprocess doesn't inherit CLI
# flags from the outer command. `llama-cpp-python` ships no prebuilt
# wheel for every platform this gets built on (see the note atop this
# file), so pip falls back to a ~75MB sdist download + a from-source
# compile — both slow enough on a modest link to need this.
ENV PIP_DEFAULT_TIMEOUT=180
# Compiling llama.cpp/ggml (ggml-org/llama.cpp, vendored by
# llama-cpp-python) is memory-hungry — several of its ~300 translation
# units at -O3 are heavy enough that letting cmake/ninja run one `cc1plus`
# per core in parallel can exceed available memory on a modest build
# host (observed OOM-killing the compiler on a 2-core/2GB build VM).
# Capped to 1 to trade build time for reliability — this only affects the
# build step, not runtime.
ENV CMAKE_BUILD_PARALLEL_LEVEL=1
RUN pip install --no-cache-dir -r requirements.txt

COPY download_model.py ./

# Bakes the Qwen2.5-1.5B-Instruct GGUF (see download_model.py's
# MODEL_REPO/MODEL_FILENAME) into the image at build time, so the
# container works immediately and offline from first boot — never
# downloaded at request time. This is the slow, network-heavy part of
# the build (~1GB) — `download_model.py` is copied in and run *before*
# `main.py` specifically so this layer's cache only busts when the model
# choice itself changes, not on every application-code edit (the system
# prompt, `n_threads`, the endpoint, ...) — those used to live in the
# same file and re-triggered this download on every unrelated change.
RUN python download_model.py

COPY main.py ./

EXPOSE 8002

# No `curl` in the slim base image — the stdlib avoids adding a package
# just for this.
HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=30s \
    CMD python -c "import urllib.request as u; u.urlopen('http://localhost:8002/health', timeout=3)" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
