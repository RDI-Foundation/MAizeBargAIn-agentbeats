FROM python:3.11-slim

# Install system dependencies for OpenSpiel build and MILP solvers
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        g++ \
        clang \
        cmake \
        git \
        curl \
        python3-dev \
        libffi-dev \
        libglpk-dev \
        glpk-utils && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first
COPY pyproject.toml* uv.lock* requirements.txt* ./
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Download OpenSpiel dependencies to correct locations and build
WORKDIR /app/scenarios/bargaining/open_spiel
RUN echo "=== Cloning dependencies ===" && \
    git clone --depth 1 https://github.com/abseil/abseil-cpp.git open_spiel/abseil-cpp && \
    git clone --depth 1 https://github.com/pybind/pybind11.git pybind11 && \
    git clone --depth 1 https://github.com/pybind/pybind11_abseil.git open_spiel/pybind11_abseil && \
    git clone -b develop --depth 1 https://github.com/jblespiau/dds.git open_spiel/games/bridge/double_dummy_solver && \
    echo "=== Building OpenSpiel ===" && \
    export CXX=g++ && \
    python setup.py build_ext --inplace 2>&1 && \
    python setup.py install

WORKDIR /app

# Ensure local src is importable
ENV PYTHONPATH=/app/src:/app/scenarios/bargaining/open_spiel

# Cloud Run sets PORT; default to 8080 locally
ENV PORT=8080

EXPOSE 8080

# Use ENTRYPOINT so compose commands append to it
ENTRYPOINT ["python", "-m", "scenarios.bargaining.bargaining_green", "serve"]
CMD ["--host", "0.0.0.0", "--port", "8080"]
