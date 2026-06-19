# src/backend/app.py
# ------------------------------------------------------------------
# Author : Ujjwal Deep — BIT Mesra
# Project: Physics-Informed Digital Twin — Industry-Grade Fleet Monitor
# ------------------------------------------------------------------

import os
import csv
import time
import asyncio
import logging
import sqlite3
import numpy as np
import io
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from collections import defaultdict
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, validator, Field

# ── Logging ────────────────────────────────────────────────────────
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

# ── FastAPI ────────────────────────────────────────────────────────
app = FastAPI(
    title="Physics-Informed Digital Twin — Fleet API",
    description="Industry-grade predictive digital twin: fleet monitoring, RUL prediction, alert history, CSV export.",
    version="2.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────
ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "https://huggingface.co",
    "https://*.hf.space",
]
if extra := os.environ.get("ALLOWED_ORIGINS_EXTRA"):
    ALLOWED_ORIGINS.extend(extra.split(","))

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# ── Rate limiting ──────────────────────────────────────────────────
_rate_buckets: dict = defaultdict(lambda: {"count": 0, "window_start": 0.0})
RATE_LIMIT, RATE_WINDOW = 60, 60.0

def check_rate_limit(ip: str) -> bool:
    now = time.monotonic()
    b = _rate_buckets[ip]
    if now - b["window_start"] > RATE_WINDOW:
        b["count"] = 0; b["window_start"] = now
    b["count"] += 1
    return b["count"] <= RATE_LIMIT

# ── Model ─────────────────────────────────────────────────────────
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
            ort_session = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])
            logger.info("ONNX model loaded.")
        except Exception:
            logger.exception("Failed to load ONNX model.")
    else:
        logger.warning("ONNX model not found. Using simulation mode.")

# ══════════════════════════════════════════════════════════════════
# DATABASE — SQLite time-series store
# ══════════════════════════════════════════════════════════════════

DB_PATH = Path(__file__).parent.parent.parent / "data" / "telemetry.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def get_db():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS bearings (
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            location    TEXT NOT NULL,
            description TEXT,
            install_date TEXT DEFAULT (date('now'))
        );

        CREATE TABLE IF NOT EXISTS telemetry (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            bearing_id  TEXT NOT NULL,
            ts          DATETIME DEFAULT (datetime('now')),
            step        INTEGER,
            health_index REAL,
            predicted_rul REAL,
            true_rul    REAL,
            status      TEXT,
            FOREIGN KEY (bearing_id) REFERENCES bearings(id)
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            bearing_id  TEXT NOT NULL,
            ts          DATETIME DEFAULT (datetime('now')),
            from_status TEXT,
            to_status   TEXT,
            health_index REAL,
            predicted_rul REAL,
            acknowledged INTEGER DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_telemetry_bearing ON telemetry(bearing_id, ts);
        CREATE INDEX IF NOT EXISTS idx_alerts_bearing    ON alerts(bearing_id, ts);
    """)
    # Seed bearing metadata
    bearings = [
        ("B1", "Bearing 1 — Drive End",  "Line A · Station 3",  "Primary drive-end bearing, Rexnord ZA-2115"),
        ("B2", "Bearing 2 — Fan End",    "Line A · Station 3",  "Fan-end bearing, showing degradation trend"),
        ("B3", "Bearing 3 — Drive End",  "Line B · Station 1",  "Secondary drive-end bearing, near end-of-life"),
        ("B4", "Bearing 4 — Fan End",    "Line B · Station 1",  "New fan-end bearing, recently replaced"),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO bearings (id, name, location, description) VALUES (?,?,?,?)",
        bearings
    )
    conn.commit()
    conn.close()
    logger.info("Database initialised at %s", DB_PATH.name)


def db_store_telemetry(bearing_id, step, health_index, predicted_rul, true_rul, status):
    conn = get_db()
    conn.execute(
        "INSERT INTO telemetry (bearing_id,step,health_index,predicted_rul,true_rul,status) VALUES (?,?,?,?,?,?)",
        (bearing_id, step, health_index, predicted_rul, true_rul, status)
    )
    # Keep only last 5000 rows per bearing to avoid unbounded growth
    conn.execute("""
        DELETE FROM telemetry WHERE bearing_id=? AND id NOT IN (
            SELECT id FROM telemetry WHERE bearing_id=? ORDER BY id DESC LIMIT 5000
        )
    """, (bearing_id, bearing_id))
    conn.commit()
    conn.close()


def db_store_alert(bearing_id, from_status, to_status, health_index, predicted_rul):
    conn = get_db()
    conn.execute(
        "INSERT INTO alerts (bearing_id,from_status,to_status,health_index,predicted_rul) VALUES (?,?,?,?,?)",
        (bearing_id, from_status, to_status, health_index, predicted_rul)
    )
    conn.commit()
    conn.close()


# ══════════════════════════════════════════════════════════════════
# FLEET SIMULATION — 4 independent bearing state machines
# ══════════════════════════════════════════════════════════════════

class BearingSimulator:
    """Independent run-to-failure simulation for one bearing."""

    CONFIGS = {
        "B1": {"start_rul": 105, "max_rul": 125, "noise_std": 4.0,  "speed": 1},
        "B2": {"start_rul":  56, "max_rul": 125, "noise_std": 5.5,  "speed": 1},
        "B3": {"start_rul":  22, "max_rul": 125, "noise_std": 6.0,  "speed": 1},
        "B4": {"start_rul": 118, "max_rul": 125, "noise_std": 3.0,  "speed": 1},
    }

    def __init__(self, bearing_id: str):
        cfg = self.CONFIGS[bearing_id]
        self.bearing_id = bearing_id
        self.step = 0
        self.true_rul = float(cfg["start_rul"])
        self.max_rul = cfg["max_rul"]
        self.noise_std = cfg["noise_std"]
        self.prev_status: Optional[str] = None

    def tick(self) -> dict:
        # True RUL degrades by 1 per step, wraps back to max after failure
        self.true_rul = max(0.0, self.true_rul - 1.0)
        if self.true_rul == 0.0:
            self.true_rul = float(self.max_rul)

        # Predicted RUL has realistic model noise
        pred_rul = max(0.0, self.true_rul + np.random.normal(0, self.noise_std))
        health_index = round(min(1.0, max(0.0, pred_rul / self.max_rul)), 4)

        # Status thresholds
        if health_index > 0.6:
            new_status = "NORMAL"
        elif health_index > 0.25:
            new_status = "WARNING"
        else:
            new_status = "CRITICAL"

        # Simulate 14-channel sensor window
        deg = 1.0 - health_index
        base  = np.random.normal(0.5, 0.1, (30, 14))
        spike = np.random.normal(1.5, 0.5, (30, 14)) * (deg ** 2)
        sensors = (base + spike).tolist()

        result = {
            "bearing_id":    self.bearing_id,
            "step":          self.step,
            "sensors":       [round(v, 4) for v in sensors[-1]],
            "true_rul":      round(self.true_rul, 1),
            "predicted_rul": round(pred_rul, 2),
            "health_index":  health_index,
            "status":        new_status,
            "ts":            datetime.utcnow().isoformat() + "Z",
        }

        # Persist to DB (async-safe via dedicated thread in WS handler)
        try:
            db_store_telemetry(
                self.bearing_id, self.step, health_index,
                pred_rul, self.true_rul, new_status
            )
            if self.prev_status and self.prev_status != new_status:
                db_store_alert(
                    self.bearing_id, self.prev_status, new_status,
                    health_index, pred_rul
                )
        except Exception:
            logger.exception("DB write error for %s", self.bearing_id)

        self.prev_status = new_status
        self.step += 1
        return result


# Global simulators — one per bearing
_simulators: dict[str, BearingSimulator] = {}
# Active WebSocket connections per bearing (for fanout)
_ws_connections: dict[str, list] = defaultdict(list)


# ══════════════════════════════════════════════════════════════════
# STARTUP
# ══════════════════════════════════════════════════════════════════

@app.on_event("startup")
async def startup_event():
    init_onnx_session()
    init_db()
    for bid in ["B1", "B2", "B3", "B4"]:
        _simulators[bid] = BearingSimulator(bid)

    # Static files are mounted at module level below

    # Start background simulation tickers
    for bid in ["B1", "B2", "B3", "B4"]:
        asyncio.create_task(bearing_ticker(bid))


async def bearing_ticker(bearing_id: str):
    """Background task: ticks one bearing every second and fans out to WS clients."""
    while True:
        await asyncio.sleep(1.0)
        try:
            payload = _simulators[bearing_id].tick()
            # Fan out to all connected WebSocket clients for this bearing
            dead = []
            for ws in _ws_connections[bearing_id]:
                try:
                    await ws.send_json(payload)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                _ws_connections[bearing_id].remove(ws)
        except Exception:
            logger.exception("Ticker error for %s", bearing_id)


# ── Static files & SPA fallback ────────────────────────────────────
_STATIC_DIR = Path(__file__).parent.parent.parent / "static"

# Mount /assets BEFORE defining the SPA catch-all so JS/CSS/fonts load correctly
if _STATIC_DIR.exists() and (_STATIC_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(_STATIC_DIR / "assets")), name="assets")
    logger.info("React frontend assets mounted from %s", _STATIC_DIR / "assets")

_API_PREFIXES = ("health", "predict", "ws", "docs", "openapi", "assets",
                 "redoc", "fleet", "history", "alerts", "export")

@app.get("/", include_in_schema=False)
async def serve_root():
    index = _STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return JSONResponse({"status": "running", "frontend": "not built"})

@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str = ""):
    index = _STATIC_DIR / "index.html"
    if full_path.startswith(_API_PREFIXES):
        raise HTTPException(status_code=404, detail="Not found")
    if index.exists():
        return FileResponse(str(index))
    raise HTTPException(status_code=404, detail="Not found")


# ══════════════════════════════════════════════════════════════════
# SCHEMAS
# ══════════════════════════════════════════════════════════════════

SENSOR_MIN, SENSOR_MAX = -100.0, 100.0

class TelemetryWindow(BaseModel):
    sequence: List[List[float]] = Field(..., description="Shape (30, 14): 30 steps × 14 sensors.")

    @validator("sequence")
    def validate_dimensions(cls, v):
        if len(v) != 30:
            raise ValueError("Sequence must contain exactly 30 time steps.")
        for idx, step in enumerate(v):
            if len(step) != 14:
                raise ValueError(f"Step {idx} must have 14 readings.")
            for val in step:
                if val != val or abs(val) == float("inf"):
                    raise ValueError(f"NaN/Inf at step {idx}.")
                if not (SENSOR_MIN <= val <= SENSOR_MAX):
                    raise ValueError(f"Value {val} at step {idx} out of range [{SENSOR_MIN},{SENSOR_MAX}].")
        return v

class PredictionResponse(BaseModel):
    predicted_rul: float
    health_index: float
    status: str
    recommendation: str


# ══════════════════════════════════════════════════════════════════
# REST ENDPOINTS
# ══════════════════════════════════════════════════════════════════

@app.get("/health", tags=["System"])
def health_check():
    """Server + model health. Safe to expose publicly."""
    return {
        "status": "healthy",
        "onnx_available": ONNX_AVAILABLE,
        "model_loaded": ort_session is not None,
        "api_version": "2.0.0",
        "fleet_size": len(_simulators),
    }


@app.get("/fleet", tags=["Fleet"])
def get_fleet():
    """
    Current health snapshot of all 4 bearings.
    Returns the latest stored telemetry row per bearing.
    """
    conn = get_db()
    rows = conn.execute("""
        SELECT t.bearing_id, b.name, b.location, b.description,
               t.step, t.health_index, t.predicted_rul, t.true_rul, t.status, t.ts
        FROM telemetry t
        JOIN bearings b ON b.id = t.bearing_id
        WHERE t.id IN (
            SELECT MAX(id) FROM telemetry GROUP BY bearing_id
        )
        ORDER BY t.bearing_id
    """).fetchall()
    conn.close()

    # Fallback: if DB not yet populated, return from simulators directly
    if not rows:
        return [
            {
                "bearing_id":    bid,
                "name":          BearingSimulator.CONFIGS[bid].get("name", bid),
                "health_index":  round(_simulators[bid].true_rul / 125.0, 4),
                "predicted_rul": _simulators[bid].true_rul,
                "status":        "NORMAL",
            }
            for bid in ["B1", "B2", "B3", "B4"]
        ]

    return [dict(r) for r in rows]


@app.get("/history/{bearing_id}", tags=["Fleet"])
def get_history(bearing_id: str, limit: int = 200):
    """
    Returns the last `limit` telemetry readings for a bearing.
    Max 1000 rows per request.
    """
    if bearing_id not in ["B1", "B2", "B3", "B4"]:
        raise HTTPException(status_code=404, detail="Unknown bearing ID.")
    limit = min(limit, 1000)
    conn = get_db()
    rows = conn.execute("""
        SELECT step, health_index, predicted_rul, true_rul, status, ts
        FROM telemetry
        WHERE bearing_id = ?
        ORDER BY id DESC LIMIT ?
    """, (bearing_id, limit)).fetchall()
    conn.close()
    return list(reversed([dict(r) for r in rows]))


@app.get("/alerts", tags=["Fleet"])
def get_alerts(bearing_id: Optional[str] = None, limit: int = 100):
    """
    Returns alert history (status transitions).
    Optionally filter by bearing_id.
    """
    limit = min(limit, 500)
    conn = get_db()
    if bearing_id:
        if bearing_id not in ["B1", "B2", "B3", "B4"]:
            raise HTTPException(status_code=404, detail="Unknown bearing ID.")
        rows = conn.execute("""
            SELECT a.*, b.name AS bearing_name
            FROM alerts a JOIN bearings b ON b.id = a.bearing_id
            WHERE a.bearing_id = ?
            ORDER BY a.id DESC LIMIT ?
        """, (bearing_id, limit)).fetchall()
    else:
        rows = conn.execute("""
            SELECT a.*, b.name AS bearing_name
            FROM alerts a JOIN bearings b ON b.id = a.bearing_id
            ORDER BY a.id DESC LIMIT ?
        """, (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/export/{bearing_id}", tags=["Fleet"])
def export_csv(bearing_id: str, request: Request):
    """
    Download full telemetry history for a bearing as CSV.
    Rate-limited to 60 req/min per IP.
    """
    if bearing_id not in ["B1", "B2", "B3", "B4"]:
        raise HTTPException(status_code=404, detail="Unknown bearing ID.")
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded.")

    conn = get_db()
    rows = conn.execute("""
        SELECT ts, step, health_index, predicted_rul, true_rul, status
        FROM telemetry WHERE bearing_id = ? ORDER BY id ASC
    """, (bearing_id,)).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["timestamp", "step", "health_index", "predicted_rul", "true_rul", "status"])
    for r in rows:
        writer.writerow([r["ts"], r["step"], r["health_index"],
                         r["predicted_rul"], r["true_rul"], r["status"]])
    output.seek(0)

    filename = f"bearing_{bearing_id}_telemetry_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.post("/predict", response_model=PredictionResponse, tags=["Inference"])
def predict_rul(payload: TelemetryWindow, request: Request):
    """Manual RUL prediction from a 30×14 sensor window."""
    client_ip = request.client.host if request.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Max 60 req/min.")

    global ort_session
    if ort_session is None:
        init_onnx_session()
        if ort_session is None:
            raise HTTPException(status_code=503, detail="Inference model not ready.")

    try:
        input_data  = np.array(payload.sequence, dtype=np.float32)[np.newaxis, :, :]
        input_name  = ort_session.get_inputs()[0].name
        output_name = ort_session.get_outputs()[0].name
        raw_out     = ort_session.run([output_name], {input_name: input_data})
        pred_val    = float(raw_out[0][0])
        hi          = min(1.0, max(0.0, pred_val / 125.0))

        if hi > 0.6:
            st, rec = "NORMAL",   "Operating within safe parameters."
        elif hi > 0.25:
            st, rec = "WARNING",  "Minor degradation. Schedule inspection within 24h."
        else:
            st, rec = "CRITICAL", "Severe degradation. Immediate maintenance recommended."

        return PredictionResponse(predicted_rul=pred_val, health_index=hi,
                                   status=st, recommendation=rec)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Inference error on /predict")
        raise HTTPException(status_code=500, detail="Inference failed.")


# ══════════════════════════════════════════════════════════════════
# WEBSOCKET — per-bearing real-time stream
# ══════════════════════════════════════════════════════════════════

VALID_BEARINGS = {"B1", "B2", "B3", "B4"}

@app.websocket("/ws/telemetry/{bearing_id}")
async def ws_bearing(websocket: WebSocket, bearing_id: str):
    """
    Real-time telemetry stream for one bearing.
    Connect to /ws/telemetry/B1, /ws/telemetry/B2, etc.
    """
    if bearing_id not in VALID_BEARINGS:
        await websocket.close(code=4004)
        return

    origin = websocket.headers.get("origin", "")
    if origin and not any(origin.startswith(o) for o in ALLOWED_ORIGINS + [""]):
        await websocket.close(code=4003)
        logger.warning("WS rejected from origin: %s", origin)
        return

    await websocket.accept()
    _ws_connections[bearing_id].append(websocket)
    logger.info("WS connected: %s (active: %d)", bearing_id, len(_ws_connections[bearing_id]))

    try:
        # Send last 60 history rows immediately on connect (so charts populate)
        conn = get_db()
        hist = conn.execute("""
            SELECT step, health_index, predicted_rul, true_rul, status, ts
            FROM telemetry WHERE bearing_id=? ORDER BY id DESC LIMIT 60
        """, (bearing_id,)).fetchall()
        conn.close()
        if hist:
            await websocket.send_json({
                "type": "history",
                "bearing_id": bearing_id,
                "data": list(reversed([dict(r) for r in hist]))
            })

        # Keep connection open — ticker pushes data
        while True:
            await asyncio.sleep(30)   # send a keepalive ping every 30s
            await websocket.send_json({"type": "ping"})

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("WS error for %s", bearing_id)
    finally:
        try:
            _ws_connections[bearing_id].remove(websocket)
        except ValueError:
            pass
        logger.info("WS disconnected: %s", bearing_id)


# Legacy single-bearing endpoint (backwards compat)
@app.websocket("/ws/telemetry")
async def ws_legacy(websocket: WebSocket):
    await ws_bearing(websocket, "B1")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
