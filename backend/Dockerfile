FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /tmp/
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r /tmp/requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install "optuna>=4.0"

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install "openai>=1.0"

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install "torch>=2.0" --index-url https://download.pytorch.org/whl/cpu

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
