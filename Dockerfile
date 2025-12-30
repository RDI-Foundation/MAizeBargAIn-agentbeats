FROM python:3.11-slim

# Install system dependencies for OpenSpiel build
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        g++ \
        clang \
        cmake \
        git \
        curl \
        python3-dev \
        libffi-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first
COPY pyproject.toml* uv.lock* requirements.txt* ./
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Download OpenSpiel dependencies and build pyspiel
WORKDIR /app/scenarios/bargaining/open_spiel
RUN git clone --depth 1 https://github.com/abseil/abseil-cpp.git abseil-cpp && \
    git clone --depth 1 https://github.com/pybind/pybind11.git pybind11 && \
    export CXX=g++ && \
    python setup.py build_ext --inplace && \
    python setup.py install

WORKDIR /app

# Ensure local src is importable
ENV PYTHONPATH=/app/src:/app/scenarios/bargaining/open_spiel:${PYTHONPATH:-}

# Cloud Run sets PORT; default to 8080 locally
ENV PORT=8080

EXPOSE 8080

CMD ["/bin/sh", "-c", "python -m scenarios.bargaining.bargaining_green serve --host 0.0.0.0 --port ${PORT:-8080} --card-url ${CARD_URL:-http://localhost:${PORT:-8080}/}"]
