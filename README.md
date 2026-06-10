---
title: Physics Informed Digital Twin
emoji: ⚙️
colorFrom: cyan
colorTo: blue
sdk: docker
pinned: true
license: mit
short_description: Real-time bearing health monitoring and RUL prediction dashboard
---

<table align="center">
  <tr>
    <td align="center" width="100%">
      <h1>⚙️ Physics-Informed Digital Twin</h1>
      <h3>Real-Time Bearing Health Monitoring & Remaining Useful Life Prediction</h3>
      <p><b>Physics-guided machine learning for industrial rotating machinery diagnostics</b></p>
      <p>
        <b>Author:</b> Ujjwal Deep &nbsp;•&nbsp;
        <b>Institute:</b> BIT Mesra, Ranchi &nbsp;•&nbsp;
        <b>Project Type:</b> Final Year B.Tech Research Project
      </p>
    </td>
  </tr>
</table>

---

## Abstract

This project presents a **physics-informed digital twin framework** for industrial bearing health monitoring.  
It combines **vibration-based condition assessment**, **Remaining Useful Life (RUL) prediction**, and **physics-constrained deep learning** to support predictive maintenance in rotating machinery systems.

The proposed system ingests multi-channel vibration data, processes it through a sliding-window pipeline, and performs real-time inference using a **VibFormer** architecture augmented with physics-based regularization.

---

## Research Objective

The main goal of this project is to build a practical digital twin for bearings that can:

- estimate degradation trends in real time
- predict Remaining Useful Life
- detect health-state transitions
- incorporate physics constraints into ML predictions
- provide a deployable monitoring dashboard

---

## System Overview

| Stage | Description |
|---|---|
| **Data Source** | IMS Bearing Dataset from the University of Cincinnati |
| **Preprocessing** | Signal cleaning, normalization, and sliding-window segmentation |
| **Feature Learning** | Transformer-based temporal representation learning |
| **Physics Integration** | Degradation constraints inspired by fatigue-growth behavior |
| **Inference** | ONNX-based model execution through FastAPI |
| **Visualization** | React dashboard with live telemetry and health state indicators |

---

## Architecture

```text
IMS Bearing Dataset
        │
        ▼
Signal Preprocessing
        │
        ▼
Sliding Window Formation (30 × 14)
        │
        ▼
VibFormer Model
   ├── Temporal Feature Encoder
   ├── RUL Regression Head
   └── Physics-Informed Loss
        │
        ▼
ONNX Export
        │
        ▼
FastAPI Inference Layer
        │
        ▼
WebSocket Telemetry Stream
        │
        ▼
React Health Monitoring Dashboard
