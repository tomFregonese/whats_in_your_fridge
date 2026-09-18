FROM python:3.12-slim

# `upgrade` pulls in any Debian security patches released since this
# base image was built — otherwise the image stays pinned to whatever was
# current the day python:3.12-slim was last published.
RUN apt-get update \
    && apt-get upgrade -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY download_model.py ./

# Bakes the "base" Whisper model (see download_model.py's MODEL_SIZE)
# into the image at build time, so the container works immediately and
# offline from first boot — never downloaded at request time.
# `download_model.py` is copied in and run *before* `main.py`
# specifically so this layer's cache only busts when the model choice
# itself changes, not on every application-code edit.
RUN python download_model.py

COPY main.py ./

EXPOSE 8001

# No `curl` in the slim base image — the stdlib avoids adding a package
# just for this.
HEALTHCHECK --interval=10s --timeout=5s --retries=5 --start-period=30s \
    CMD python -c "import urllib.request as u; u.urlopen('http://localhost:8001/health', timeout=3)" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
