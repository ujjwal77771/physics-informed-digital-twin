# Dockerfile for Physics-Informed Digital Twin API
# ------------------------------------------------------------------
# Production-ready, multi-stage, secure container definition.
# ------------------------------------------------------------------

FROM python:3.10-slim AS builder

WORKDIR /app

# Install build dependencies (compilers needed for some scientific packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies to a local folder
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


FROM python:3.10-slim AS runner

WORKDIR /app

# Copy installed python dependencies from builder stage
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy project files
COPY model/ ./model/
COPY preprocessing/ ./preprocessing/
COPY training/ ./training/
COPY src/ ./src/

# Set Python path to find modules properly
ENV PYTHONPATH=/app

# Expose FastAPI default port
EXPOSE 8000

# Run FastAPI with Uvicorn
CMD ["uvicorn", "src.backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
