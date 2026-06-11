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

A physics-guided ML framework for industrial bearing prognostics — combining transformer-based sequence modeling with degradation-aware training objectives to produce monotonically consistent, interpretable RUL estimates across the full bearing lifecycle.

</div>

---

## Table of Contents

- [Motivation & Problem Statement](#motivation--problem-statement)
- [Technical Approach](#technical-approach)
- [System Architecture](#system-architecture)
- [Model Design: VibFormer](#model-design-vibformer)
- [Physics Constraints](#physics-constraints)
- [Dataset](#dataset)
- [Project Structure](#project-structure)
- [Quickstart](#quickstart)
- [API Reference](#api-reference)
- [Performance](#performance)
- [Limitations & Future Work](#limitations--future-work)

---

## Motivation & Problem Statement

Rotating machinery failures account for a disproportionate share of unplanned industrial downtime. Bearings exhibit characteristic multi-stage degradation — from incipient microcracking to spall propagation to catastrophic failure — that produces measurable signatures in vibration spectra well before any physical threshold is breached.

Purely data-driven prognostic models applied to this problem tend to fail in predictable ways:

- **Non-monotonic degradation curves** — health index predictions that improve as bearings approach failure, violating the physics of irreversible damage accumulation
- **Overconfident extrapolation** — poor calibration in the tail of the RUL distribution where training data is sparse
- **Distributional shift sensitivity** — brittle behavior when operating conditions deviate from training regimes
- **Deployment gap** — research models that cannot serve real-time inference at production latency requirements

This project treats all four as first-class engineering constraints, not afterthoughts.

---

## Technical Approach

The core insight is that bearing degradation is not merely a sequence modeling problem — it is a *constrained* sequence modeling problem. The health index `H(t)` must satisfy:

```
