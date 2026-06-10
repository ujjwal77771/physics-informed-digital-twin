# src/backend/app.py
# ------------------------------------------------------------------
# Author : Ujjwal Deep
# College: BIT Mesra, Ranchi
# Project: Physics-Informed Digital Twin for RUL Prediction
# ------------------------------------------------------------------

import os
import sys
import asyncio
import numpy as np
from typing import List
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator, Field

# Load ONNX Runtime
try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

app = FastAPI(
    title="Physics-Informed Digital Twin API",
    description="Production-ready API for fault diagnosis and Remaining Useful Life (RUL) prediction of industrial bearings.",
    version="1.0.0"
)

# Enable CORS for frontend dashboard connection
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to the exported ONNX model
MODEL_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "model", "vibformer.onnx"
)

# Global inference session
ort_session = None

def init_onnx_session():
    global ort_session
    if not ONNX_AVAILABLE:
        print("[WARNING] onnxruntime is not installed. Inference will not be available.")
        return
    if os.path.exists(MODEL_PATH):
        try:
            ort_session = ort.InferenceSession(MODEL_PATH, providers=['CPUExecutionProvider'])
            print(f"[INFO] ONNX model successfully loaded from {MODEL_PATH}")
        except Exception as e:
            print(f"[ERROR] Failed to load ONNX model: {e}")
    else:
        print(f"[WARNING] ONNX model file not found at {MODEL_PATH}. Run 'python model/export_onnx.py' first.")

@app.on_event("startup")
async def startup_event():
    init_onnx_session()


# ------------------------------------------------------------------
# Pydantic Data Schemas (Input Validation & Protection)
# ------------------------------------------------------------------

class TelemetryWindow(BaseModel):
    # Expects a 2D list of shape (30, 14) representing 30 time steps of 14 sensor values
    sequence: List[List[float]] = Field(
        ..., 
        description="A 2D array of shape (30, 14) containing 30 time steps of 14 sensor readings."
    )

    @validator('sequence')
    def validate_dimensions(cls, v):
        if len(v) != 30:
            raise ValueError("The sequence must contain exactly 30 time steps.")
        for idx, step in enumerate(v):
            if len(step) != 14:
                raise ValueError(f"Time step {idx} must contain exactly 14 sensor readings.")
        return v


class PredictionResponse(BaseModel):
    predicted_rul: float
    health_index: float
    status: str
    recommendation: str


# ------------------------------------------------------------------
# REST Endpoints
# ------------------------------------------------------------------

@app.get("/health", tags=["System"])
def health_check():
    """System health check endpoint."""
    model_loaded = ort_session is not None
    return {
        "status": "healthy",
        "onnx_available": ONNX_AVAILABLE,
        "model_loaded": model_loaded,
        "api_version": "1.0.0"
    }

@app.post("/predict", response_model=PredictionResponse, tags=["Inference"])
def predict_rul(payload: TelemetryWindow):
    """
    Predicts the Remaining Useful Life (RUL) of the bearing based on a 30-timestep sliding window of 14 sensors.
    """
    global ort_session
    
    # Reload session if it hasn't been initialized yet
    if ort_session is None:
        init_onnx_session()
        if ort_session is None:
            raise HTTPException(
                status_code=503, 
                detail="Model inference session is not initialized. Please ensure the ONNX model is exported."
            )

    try:
        # Convert input sequence to numpy float32 array and add batch dimension: (1, 30, 14)
        input_data = np.array(payload.sequence, dtype=np.float32)[np.newaxis, :, :]

        # Run inference in ONNX Runtime
        input_name = ort_session.get_inputs()[0].name
        output_name = ort_session.get_outputs()[0].name
        
        raw_out = ort_session.run([output_name], {input_name: input_data})
        predicted_val = float(raw_out[0][0])
        
        # Calculate a normalized health index based on maximum theoretical RUL (125)
        health_index = min(1.0, max(0.0, predicted_val / 125.0))
        
        # Determine status and actions
        if health_index > 0.6:
            status = "NORMAL"
            recommendation = "Machine is operating within safe parameters. Continue scheduled operations."
        elif health_index > 0.25:
            status = "WARNING"
            recommendation = "Minor degradation detected. Increase monitoring frequency and schedule inspection within 24 operating hours."
        else:
            status = "CRITICAL"
            recommendation = "Severe degradation / fault detected. IMMEDIATE maintenance shutdown recommended to prevent catastrophic failure."

        return PredictionResponse(
            predicted_rul=predicted_val,
            health_index=health_index,
            status=status,
            recommendation=recommendation
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference error: {str(e)}")


# ------------------------------------------------------------------
# WebSocket Endpoint (Real-time Telemetry Stream)
# ------------------------------------------------------------------

@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    """
    Simulates real-time streaming of bearing vibration and operating telemetry.
    Streams prediction updates back to the dashboard client.
    """
    await websocket.accept()
    print("[WS] Client connected to telemetry stream.")
    
    try:
        # We simulate a run-to-failure sequence
        step = 0
        max_steps = 150
        
        while True:
            # 1. Simulate new incoming sensor window (30, 14)
            # As time goes on, we add noise and increase amplitude to simulate a failing bearing
            degradation_factor = step / max_steps
            base_noise = np.random.normal(0.5, 0.1, (30, 14))
            vibration_spike = np.random.normal(1.5, 0.5, (30, 14)) * (degradation_factor ** 3)
            simulated_window = (base_noise + vibration_spike).tolist()

            # 2. Simulate true and predicted RUL decreasing
            true_rul = max(0.0, float(125.0 - step))
            # Model prediction with realistic model error/variance
            pred_noise = np.random.normal(0.0, 5.0)
            predicted_rul = max(0.0, true_rul + pred_noise)
            
            # Calculate metrics
            health_index = min(1.0, max(0.0, predicted_rul / 125.0))
            if health_index > 0.6:
                status = "NORMAL"
            elif health_index > 0.25:
                status = "WARNING"
            else:
                status = "CRITICAL"

            # 3. Send payload to client
            payload = {
                "step": step,
                "sensors": simulated_window[-1], # send current values for charts
                "true_rul": true_rul,
                "predicted_rul": round(predicted_rul, 2),
                "health_index": round(health_index, 4),
                "status": status
            }
            
            await websocket.send_json(payload)
            
            # Advance time step
            step = (step + 1) % max_steps
            await asyncio.sleep(1.0)  # Stream once every second
            
    except WebSocketDisconnect:
        print("[WS] Client disconnected from telemetry stream.")
    except Exception as e:
        print(f"[WS] WebSocket error: {e}")
        try:
            await websocket.close()
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
