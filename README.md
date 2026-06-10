---
title: Physics Informed Digital Twin
emoji: ⚙️
colorFrom: cyan
colorTo: blue
sdk: docker
pinned: true
license: mit
short_description: Real-time bearing health monitoring and Remaining Useful Life prediction
---

<div align="center">

# Physics-Informed Digital Twin for Bearing Prognostics

### Real-Time Bearing Health Monitoring & Remaining Useful Life Prediction

[![Python](https://img.shields.io/badge/Python-3.11-blue)]()
[![PyTorch](https://img.shields.io/badge/PyTorch-2.x-red)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green)]()
[![React](https://img.shields.io/badge/React-18-blue)]()
[![ONNX](https://img.shields.io/badge/ONNX-Runtime-orange)]()
[![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED)]()
[![License](https://img.shields.io/badge/License-MIT-yellow)]()

Physics-guided machine learning framework for industrial bearing health monitoring,
fault diagnosis, degradation tracking, and Remaining Useful Life (RUL) estimation.

</div>

---

## Overview

Unexpected bearing failures are one of the primary causes of downtime in rotating machinery and industrial assets. This project implements a physics-informed digital twin capable of continuously monitoring bearing degradation and forecasting Remaining Useful Life (RUL) using vibration sensor measurements.

Unlike purely data-driven approaches, the framework incorporates physics-inspired degradation constraints during training, enabling more realistic and stable predictions throughout the bearing lifecycle.

---

## Key Capabilities

| Capability | Description |
|------------|-------------|
| Health Monitoring | Continuous bearing condition assessment |
| RUL Prediction | Remaining Useful Life estimation |
| Fault Detection | Early warning and critical failure detection |
| Physics-Informed Learning | Domain-constrained machine learning |
| Live Telemetry | Real-time sensor streaming |
| Multi-Channel Analysis | Simultaneous vibration channel monitoring |
| Dashboard Visualization | Interactive health analytics |
| API Access | Programmatic model inference |

---

## Motivation

Modern predictive maintenance systems frequently struggle with:

- Physically inconsistent degradation predictions
- Poor extrapolation near failure regions
- Limited interpretability of learned patterns
- Difficulty deploying research models in production environments

This project addresses these limitations through a hybrid digital twin architecture that combines transformer-based sequence modeling with degradation-aware learning objectives.

---

## System Architecture

```text
IMS Bearing Dataset
        │
        ▼
Signal Conditioning
        │
        ▼
Window Generation
      (30 × 14)
        │
        ▼
VibFormer Network
        │
        ├── Temporal Attention Encoder
        ├── Physics Regularization
        ├── Monotonicity Constraint
        └── RUL Regression Head
        │
        ▼
ONNX Runtime
        │
        ▼
FastAPI Inference Server
        │
        ▼
WebSocket Telemetry Layer
        │
        ▼
React Monitoring Dashboard
