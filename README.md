---
title: Physics Informed Digital Twin
emoji: ⚙️
colorFrom: cyan
colorTo: blue
sdk: docker
pinned: true
license: mit
short_description: Real-time bearing health monitoring & RUL prediction dashboard
---

# ⚙️ Physics-Informed Digital Twin — Bearing Health Monitor

**Real-time industrial bearing fault diagnosis and Remaining Useful Life (RUL) prediction powered by physics-informed machine learning.**

> Built by **Ujjwal Deep** · BIT Mesra, Ranchi  


---

## 🎯 What This Does

This platform simulates a real-world **industrial digital twin** for rotating machinery:

| Feature | Description |
|:---|:---|
| **Live Dashboard** | Real-time bearing health monitoring with animated charts |
| **RUL Prediction** | Predicts remaining useful life in operating cycles |
| **Fault Detection** | NORMAL → WARNING → CRITICAL status transitions |
| **Physics-Informed ML** | VibFormer model trained with Paris Law physics constraints |
| **14-Channel Sensors** | All sensor channels visualized live |

---

## 🧠 Technical Architecture

```
IMS Bearing Dataset (20,000+ vibration samples)
        ↓
Preprocessing → Sliding Window (30 × 14)
        ↓
VibFormer (Transformer + Physics Loss)
  - Paris Law constraint: da/dN = C·ΔK^m
  - Monotonicity penalty
  - MSE prediction loss
        ↓
ONNX Export → FastAPI Backend (port 7860)
        ↓
WebSocket Stream → React Dashboard
```

---

## 🚀 How to Use

1. **Open the app** — the dashboard loads automatically
2. **Watch the live stream** — the telemetry WebSocket updates every second
3. **Monitor status** — NORMAL (green) → WARNING (yellow) → CRITICAL (red)
4. **Use the REST API** — visit `/docs` for the Swagger UI

### REST API Endpoints

| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/health` | System health check |
| `POST` | `/predict` | RUL prediction from sensor window |
| `WS` | `/ws/telemetry` | Real-time telemetry stream |

---

## 📦 Tech Stack

- **ML:** PyTorch, Physics-Informed Neural Networks (PINN)
- **Inference:** ONNX Runtime
- **Backend:** FastAPI + WebSockets
- **Frontend:** React + Vite + Recharts
- **Deploy:** Docker on Hugging Face Spaces

---

## 📊 Dataset

**IMS Bearing Dataset** (University of Cincinnati)
- 20,000+ vibration samples across 4 bearing channels
- Run-to-failure experiments at 2000 RPM under 6000 lbs load
- Sampled at 20 kHz

---

## 📄 License

MIT License — open source for educational and research use.
