# ── Stage 1: Build React frontend ───────────────────────────────
FROM node:20-slim AS frontend-builder

WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build
# Output will be at /frontend/dist

# ── Stage 2: Python runtime ──────────────────────────────────────
FROM python:3.10-slim

# HF Spaces runs as non-root user 1000
RUN useradd -m -u 1000 user
USER user

ENV PATH="/home/user/.local/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install Python dependencies
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy application code
COPY --chown=user src/ ./src/
COPY --chown=user model/ ./model/
COPY --chown=user preprocessing/ ./preprocessing/
COPY --chown=user training/ ./training/

# Copy built React frontend into /app/static
COPY --chown=user --from=frontend-builder /frontend/dist ./static

# HF Spaces requires port 7860
EXPOSE 7860

CMD ["uvicorn", "src.backend.app:app", "--host", "0.0.0.0", "--port", "7860"]
