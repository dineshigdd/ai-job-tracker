# --- Stage 1: Build virtual environment ---
FROM python:3.10-slim as builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# --- Stage 2: Final Runtime ---
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 1. Install curl for health checks in the final runtime stage
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# 2. Create non-root user
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /app

# 3. Copy dependencies and application code
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app /app
COPY . .

# 4. Set permissions for non-root user
RUN chown -R appuser:appuser /app
USER appuser

ENV PATH="/opt/venv/bin:$PATH"

EXPOSE 8000

# 5. Health Check using Python natively (No curl dependency needed, but curl is installed if needed)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:' + os.getenv('PORT', '8000') + '/docs')" || exit 1

# 6. Dynamically bind port using shell syntax so Render's $PORT environment variable works
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]