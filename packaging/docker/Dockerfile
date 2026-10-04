FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

ARG BUNDLED_OPENAI_KEY=""

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
RUN mkdir -p src/iaula/web/js src/iaula/web/styles && pip install --no-cache-dir -e ".[dev]" && \
    pip install --no-cache-dir playwright && \
    playwright install chromium --with-deps && \
    rm -rf /root/.cache/pip

COPY src/iaula src/iaula
COPY scripts scripts
COPY packaging/run_iaula.py .

RUN if [ -n "$BUNDLED_OPENAI_KEY" ]; then \
      mkdir -p /app/data && \
      printf '[chat]\napi_key = "%s"\n' "$BUNDLED_OPENAI_KEY" > /app/data/config.local.toml; \
    fi

EXPOSE 7800
ENV PORT=7800
ENV IAULA_HOME=/app/data
ENV HOME=/root

VOLUME ["/app/data"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python /app/healthcheck.py

ENTRYPOINT ["python", "-m", "iaula", "gui", "--port", "7800"]
