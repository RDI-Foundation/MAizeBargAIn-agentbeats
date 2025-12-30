FROM python:3.11-slim

# Install minimal system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        git \
        curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps including open-spiel from PyPI
COPY pyproject.toml* uv.lock* requirements.txt* ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir open-spiel

# Copy source
COPY . .

# Ensure local src is importable
ENV PYTHONPATH=/app/src:/app/scenarios/bargaining/open_spiel:${PYTHONPATH:-}

# Cloud Run sets PORT; default to 8080 locally
ENV PORT=8080

# Expose for clarity (Cloud Run does not require EXPOSE)
EXPOSE 8080

# Start the bargaining green agent server (PORT comes from env, default 8080)
CMD ["/bin/sh", "-c", "python -m scenarios.bargaining.bargaining_green serve --host 0.0.0.0 --port ${PORT:-8080} --card-url ${CARD_URL:-http://localhost:${PORT:-8080}/}"]
