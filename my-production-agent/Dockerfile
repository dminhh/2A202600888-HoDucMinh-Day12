# ─────────────────────────────────────────────
# STAGE 1: Builder
# Cài dependencies, không deploy stage này
# ─────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# ─────────────────────────────────────────────
# STAGE 2: Runtime
# Chỉ copy những gì cần để chạy
# ─────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Non-root user — security best practice
RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

# Copy installed packages từ builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy source code
COPY app/ ./app/
COPY utils/ ./utils/

RUN chown -R appuser:appuser /app
USER appuser

ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONPATH=/app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
