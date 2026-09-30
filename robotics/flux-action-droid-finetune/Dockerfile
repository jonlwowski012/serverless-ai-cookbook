FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive UV_PYTHON=python3.12
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates ffmpeg git python3.12 python3.12-venv && \
    rm -rf /var/lib/apt/lists/*
RUN python3.12 -m venv /opt/uv && /opt/uv/bin/pip install --no-cache-dir uv==0.11.23
ENV PATH="/app/.venv/bin:/opt/uv/bin:${PATH}" HF_HOME=/workspace/run/hf

# The cookbook builds from its own directory. Pin the trainer source and its lockfile.
RUN git clone https://github.com/black-forest-labs/flux-action.git /app && \
    cd /app && git checkout --detach e2dd1d8dbc5977b54315d61f7548c63c043d6d4f && \
    test "$(git rev-parse HEAD)" = e2dd1d8dbc5977b54315d61f7548c63c043d6d4f
WORKDIR /app
RUN uv sync --no-cache --locked --no-dev --extra encoders --extra data && \
    uv pip install --no-cache --no-deps --python .venv/bin/python \
      'natten==0.21.6+torch2100cu128' -f https://whl.natten.org/

COPY run_full.py stage_full.py check_export.py train.json train-smoke.json /app/cookbook/
