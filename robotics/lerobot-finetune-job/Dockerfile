# CUDA 12.6 runtime on Ubuntu 22.04.
# uv manages Python 3.12 and all Python dependencies,
# following https://huggingface.co/docs/lerobot/installation (v0.5.1, uv path).
FROM nvidia/cuda:12.6.3-cudnn-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive

# Build dependencies, video decoding, and headless rendering for LeRobot.
RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake \
    build-essential \
    python3-dev \
    pkg-config \
    git \
    ffmpeg \
    libevdev-dev \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    libavfilter-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# ── uv ───────────────────────────────────────────────────────────────────────
# Docs: recommended package manager for the non-conda path.
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /lerobot
RUN mkdir -p outputs

# ── Copy dependency files early for layer caching ─────────────────────────────
COPY pyproject.toml ./

# ── Python 3.12 virtual environment via uv ────────────────────────────────────
RUN uv python install 3.12 && uv venv --python 3.12 .venv
ENV VIRTUAL_ENV=/lerobot/.venv
ENV PATH="/lerobot/.venv/bin:$PATH"

# ── Sync dependencies (runtime only) ─────────────────────────────────────────
ENV UV_INDEX_STRATEGY=unsafe-best-match
RUN uv sync --no-dev --python 3.12 --index-strategy unsafe-best-match

# ── Entrypoint assets ─────────────────────────────────────────────────────────
COPY train/ ./train/
COPY configs/ ./configs/

ENTRYPOINT ["python", "-m", "train.run"]
