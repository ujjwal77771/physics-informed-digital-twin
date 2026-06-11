# src/backend/app.py
# ------------------------------------------------------------------
# Author : Ujjwal Deep
# College: BIT Mesra, Ranchi
# Project: Physics-Informed Digital Twin for RUL Prediction
# ------------------------------------------------------------------

import os
import sys
import asyncio
import logging
import numpy as np
from pathlib import Path
from typing import List
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, validator, Field

# ── Logging (no internal paths in messages) ────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("vibformer")

# ── ONNX Runtime ───────────────────────────────────────────────────
try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    logger.warning("onnxruntime not installed — inference unavailable.")

# ── FastAPI app ────────────────────────────────────────────────────
app = FastAPI(
    title="Physics-Informed Digital Twin API",
    description="Production-ready API for fault diagnosis and RUL prediction of industrial bearings.",
    version="1.0.0",
    # Hide /docs and /openapi.json in production if desired
    # docs_url=None, redoc_url=None,
)

# ── CORS ──────────────────────────────────────────────────────────
# FIX: allow_credentials=True is incompatible with allow_origins=["*"].
# List explicit origins. For HF Spaces / local dev both are included.
ALLOWED_ORIGINS = [
    "http://localhost:5173",       # Vite dev server
    "http://localhost:8000",       # FastAPI itself (SPA served from backend)
    "http://127.0.0.1:8000",
    "https://huggingface.co",      # HF Spaces parent frame
]
# In development you can override via env var:
# ALLOWED_ORIGINS_EXTRA=https://my-space.hf.space
if extra := os.environ.get("ALLOWED_ORIGINS_EXTRA"):
    ALLOWED_ORIGINS.extend(extra.split(","))

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,       # FIX: set to False unless you use cookies/auth
    allow_methods=["GET", "POST"], # FIX: only what you actually use
    allow_headers=["Content-Type"],
)

# ── Rate limiting (simple in-memory token bucket per IP) ───────────
# For production use SlowAPI or a Redis-backed limiter.
# This lightweight version blocks >60 req/min per IP on /predict.
from collections import defaultdict
import time

_rate_counters: dict = defaultdict(lambda: {"count": 0, "window_start": 0.0})
RATE_LIMIT = 60          # max requests
RATE_WINDOW = 60.0       # per N seconds

def check_rate_limit(client_ip: str) -> bool:
    """Returns True if request is allowed, False if rate-limited."""
    now = time.monotonic()
    bucket = _rate_counters[client_ip]
    if now - bucket["window_start"] > RATE_WINDOW:
        bucket["count"] = 0
        bucket["window_start"] = now
    bucket["count"] += 1
    return bucket["count"] <= RATE_LIMIT

# ── Model path (never logged fully) ───────────────────────────────
MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "model", "vibformer.onnx"
)

ort_session = None

def init_onnx_session():
    global ort_session
    if not ONNX_AVAILABLE:
        return
    if os.path.exists(MODEL_PATH):
        try:
            ort_session = ort.InferenceSession(
                MODEL_PATH, providers=["CPUExecutionProvider"]
            )
            logger.info("ONNX model loaded successfully.")  # FIX: no path in log
        except Exception:
            logger.exception("Failed to load ONNX model.")  # stack trace in server logs only
    else:
        logger.warning("ONNX model not found. Run model/export_onnx.py first.")

@app.on_event("startup")
async def startup_event():
    init_onnx_session()
    static_dir = Path(__file__).parent.parent.parent / "static"
    if static_dir.exists():
        assets_dir = static_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
            logger.info("React frontend assets mounted.")

# ── SPA fallback ───────────────────────────────────────────────────
_API_PREFIXES = ("health", "predict", "ws", "docs", "openapi", "assets", "redoc")

@app.get("/", include_in_schema=False)
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str = ""):
    static_dir = Path(__file__).parent.parent.parent / "static"
    index = static_dir / "index.html"
    if index.exists() and not full_path.startswith(_API_PREFIXES):
        return FileResponse(str(index))
    raise HTTPException(status_code=404, detail="Not found")


# ── Pydantic Schemas ───────────────────────────────────────────────

# FIX: add value bounds — reject NaN / Inf / extreme values
SENSOR_MIN = -100.0
SENSOR_MAX =  100.0

class TelemetryWindow(BaseModel):
    sequence: List[List[float]] = Field(
        ...,
        description="Shape (30, 14): 30 time steps × 14 sensor readings."
    )

    @validator("sequence")
    def validate_dimensions(cls, v):
        if len(v) != 30:
            raise ValueError("Sequence must contain exactly 30 time steps.")
        for idx, step in enumerate(v):
            if len(step) != 14:
                raise ValueError(f"Time step {idx} must contain exactly 14 sensor readings.")
            for val in step:
                # FIX: reject NaN, Inf, and out-of-range values
                if val != val:  # NaN check (float("nan") != float("nan"))
                    raise ValueError(f"NaN detected at time step {idx}.")
                if abs(val) == float("inf"):
                    raise ValueError(f"Inf detected at time step {idx}.")
                if not (SENSOR_MIN <= val <= SENSOR_MAX):
                    raise ValueError(
                        f"Sensor value {val} at step {idx} is out of allowed range "
                        f"[{SENSOR_MIN}, {SENSOR_MAX}]."
                    )
        return v


class PredictionResponse(BaseModel):
    predicted_rul: float
    health_index: float
    status: str
    recommendation: str


# ── REST Endpoints ─────────────────────────────────────────────────

@app.get("/health", tags=["System"])
def health_check():
    """System health check. Safe to expose publicly."""
    return {
        "status": "healthy",
        "onnx_available": ONNX_AVAILABLE,
        "model_loaded": ort_session is not None,
        "api_version": "1.0.0",
    }


@app.post("/predict", response_model=PredictionResponse, tags=["Inference"])
def predict_rul(payload: TelemetryWindow, request: Request):
    """
    Predicts RUL from a 30-step × 14-feature sensor window.
    Rate-limited to 60 requests/minute per client IP.
    """
    # FIX: rate limiting
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Max 60 requests per minute.",
        )

    global ort_session
    if ort_session is None:
        init_onnx_session()
        if ort_session is None:
            raise HTTPException(
                status_code=503,
                detail="Inference model not ready.",  # FIX: no internal details
            )

    try:
        input_data = np.array(payload.sequence, dtype=np.float32)[np.newaxis, :, :]
        input_name  = ort_session.get_inputs()[0].name
        output_name = ort_session.get_outputs()[0].name
        raw_out = ort_session.run([output_name], {input_name: input_data})
        predicted_val = float(raw_out[0][0])

        health_index = min(1.0, max(0.0, predicted_val / 125.0))

        if health_index > 0.6:
            status_str = "NORMAL"
            recommendation = "Operating within safe parameters. Continue scheduled operations."
        elif health_index > 0.25:
            status_str = "WARNING"
            recommendation = "Minor degradation detected. Schedule inspection within 24 operating hours."
        else:
            status_str = "CRITICAL"
            recommendation = "Severe degradation detected. Immediate maintenance recommended."

        return PredictionResponse(
            predicted_rul=predicted_val,
            health_index=health_index,
            status=status_str,
            recommendation=recommendation,
        )

    except HTTPException:
        raise  # re-raise our own HTTP errors
    except Exception:
        # FIX: log full traceback server-side but return a generic message to client
        logger.exception("Inference error on /predict")
        raise HTTPException(status_code=500, detail="Inference failed. Check server logs.")


# ── WebSocket Endpoint ─────────────────────────────────────────────

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    """
    Streams simulated bearing telemetry at 1Hz.
    FIX: basic origin check added.
    """
    # FIX: check Origin header — reject connections from unknown origins
    origin = websocket.headers.get("origin", "")
    allowed_ws_origins = ALLOWED_ORIGINS + [""]  # empty = same-origin tools like wscat
    if origin and not any(origin.startswith(o) for o in allowed_ws_origins):
        await websocket.close(code=4003)
        logger.warning("WebSocket rejected from origin: %s", origin)
        return

    await websocket.accept()
    logger.info("WebSocket client connected.")

    step = 0
    max_steps = 150

    try:
        while True:
            degradation_factor = step / max_steps
            base_noise        = np.random.normal(0.5, 0.1,  (30, 14))
            vibration_spike   = np.random.normal(1.5, 0.5,  (30, 14)) * (degradation_factor ** 3)
            simulated_window  = (base_noise + vibration_spike).tolist()

            true_rul      = max(0.0, float(125.0 - step))
            pred_noise    = np.random.normal(0.0, 5.0)
            predicted_rul = max(0.0, true_rul + pred_noise)
            health_index  = min(1.0, max(0.0, predicted_rul / 125.0))

            status_str = (
                "NORMAL"   if health_index > 0.6  else
                "WARNING"  if health_index > 0.25 else
                "CRITICAL"
            )

            await websocket.send_json({
                "step":          step,
                "sensors":       simulated_window[-1],
                "true_rul":      true_rul,
                "predicted_rul": round(predicted_rul, 2),
                "health_index":  round(health_index, 4),
                "status":        status_str,
            })

            step = (step + 1) % max_steps
            await asyncio.sleep(1.0)

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected.")
    except Exception:
        # FIX: named exception, proper logging
        logger.exception("WebSocket stream error.")
        try:
            await websocket.close()
        except Exception:
            pass  # already closed — acceptable


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
