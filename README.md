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
H(0) ≈ 1.0          (near-nominal at installation)
dH/dt ≤ 0           (monotonic degradation)
H(t_failure) ≈ 0    (failure boundary condition)
```

Standard MSE training on RUL targets does not enforce these constraints. VibFormer injects them as soft penalty terms in the loss function, allowing the model to learn from data while respecting domain physics.

This hybrid approach — physics as *regularizer*, not physics as *simulator* — avoids the brittleness of full mechanistic models while producing outputs that are physically interpretable.

---

## System Architecture

```
IMS Bearing Dataset (raw .csv, 4 channels × ~984 files)
        │
        ▼
┌─────────────────────────────┐
│      Signal Conditioning     │
│  • Bandpass filter (1–10kHz) │
│  • Z-score normalization     │
│  • Artifact rejection        │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│      Feature Extraction      │
│  Time-domain: RMS, kurtosis, │
│  crest factor, skewness      │
│  Frequency: BPFO/BPFI/BSF   │
│  harmonics, spectral entropy │
└────────────┬────────────────┘
             │
             ▼
     Window Generation
     (seq_len=30 × n_features=14)
             │
             ▼
┌──────────────────────────────────────┐
│            VibFormer                  │
│                                      │
│  ┌──────────────────────────────┐    │
│  │  Multi-Head Temporal Attention│    │
│  │  (4 heads, d_model=128)      │    │
│  └──────────────┬───────────────┘    │
│                 │                    │
│  ┌──────────────▼───────────────┐    │
│  │  Feed-Forward Block (×3)     │    │
│  │  + Residual + LayerNorm      │    │
│  └──────────────┬───────────────┘    │
│                 │                    │
│  ┌──────────────▼───────────────┐    │
│  │  Physics Regularization Head │    │
│  │  • Monotonicity penalty      │    │
│  │  • Boundary condition loss   │    │
│  └──────────────┬───────────────┘    │
│                 │                    │
│  ┌──────────────▼───────────────┐    │
│  │  RUL Regression Head         │    │
│  │  (sigmoid-bounded output)    │    │
│  └──────────────────────────────┘    │
└──────────────────┬───────────────────┘
                   │
                   ▼
         ONNX Export + Quantization
         (INT8, ~4× inference speedup)
                   │
                   ▼
         FastAPI Inference Server
         (REST + WebSocket endpoints)
                   │
                   ▼
         React Monitoring Dashboard
         (live telemetry, trend visualization,
          fault classification, RUL display)
```

---

## Model Design: VibFormer

VibFormer is a transformer encoder adapted for multivariate time-series prognostics. Key design decisions:

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Positional encoding | Learnable | Vibration windows lack the strict ordering assumptions of NLP sequences |
| Attention scope | Full sequence (no causal mask) | Health estimation is not autoregressive; future context within a window is available |
| Output activation | Sigmoid | Constrains health index to [0, 1] without manual clipping |
| Sequence aggregation | CLS token | Avoids mean-pooling artifacts on variable-length degradation phases |
| Loss function | MSE + λ₁·L_mono + λ₂·L_boundary | See Physics Constraints below |

**Input:** `(batch, 30, 14)` — 30-timestep windows of 14 hand-engineered vibration features  
**Output:** `(batch, 1)` — scalar health index ∈ [0, 1], where 1.0 = nominal, 0.0 = failure

---

## Physics Constraints

Two penalty terms augment the standard regression loss:

**Monotonicity Loss** — penalizes health index increases between consecutive windows:

```python
def monotonicity_loss(h: Tensor) -> Tensor:
    deltas = h[:, 1:] - h[:, :-1]
    violations = F.relu(deltas)
    return violations.mean()
```

**Boundary Condition Loss** — anchors predictions at known lifecycle endpoints:

```python
def boundary_loss(h_pred: Tensor, lifecycle_position: Tensor) -> Tensor:
    early_mask = lifecycle_position < 0.1
    late_mask  = lifecycle_position > 0.9
    loss  = F.mse_loss(h_pred[early_mask], torch.ones_like(h_pred[early_mask]))
    loss += F.mse_loss(h_pred[late_mask],  torch.zeros_like(h_pred[late_mask]))
    return loss
```

**Combined objective:**

```
L_total = L_MSE + 0.1 · L_mono + 0.05 · L_boundary
```

λ values selected via grid search on validation RMSE.

---

## Dataset

This project uses the **IMS (University of Cincinnati) Bearing Dataset**.

| Property | Value |
|----------|-------|
| Source | NSF I/UCR Center for Intelligent Maintenance Systems |
| Bearings | 4 per test run (Rexnord ZA-2115) |
| Sampling rate | 20 kHz |
| Measurement interval | Every 10 minutes |
| Test runs | 3 run-to-failure experiments |
| Total files | ~984 per run |
| Failure modes | Outer race, inner race, roller element |

Download: [NASA Prognostics Data Repository](https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/)

Place extracted data at `data/raw/IMS/` before running preprocessing.

---

## Project Structure

```
.
├── data/
│   ├── raw/IMS/                   # Raw IMS dataset files
│   └── processed/                 # Windowed feature arrays (.npy)
├── src/
│   ├── preprocessing/
│   │   ├── signal_processing.py   # Filtering, feature extraction
│   │   └── window_generator.py    # Sliding window construction
│   ├── models/
│   │   ├── vibformer.py           # Transformer architecture
│   │   ├── physics_loss.py        # Monotonicity & boundary losses
│   │   └── export.py              # ONNX export + INT8 quantization
│   ├── training/
│   │   ├── train.py               # Training loop
│   │   └── evaluate.py            # RMSE, MAE, monotonicity score
│   └── serving/
│       ├── api.py                 # FastAPI inference server
│       └── telemetry.py           # WebSocket streaming layer
├── frontend/                      # React dashboard (Vite)
├── notebooks/                     # Exploratory analysis, ablations
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Quickstart

**Prerequisites:** Docker ≥ 24 and Docker Compose ≥ 2.20, or Python 3.11.

### Docker (recommended)

```bash
git clone https://github.com/ujjwal77771/physics-informed-digital-twin
cd physics-informed-digital-twin
cp -r /path/to/IMS_dataset data/raw/IMS/
docker compose up --build
```

| Service | URL |
|---------|-----|
| API + inference server | http://localhost:8000 |
| React dashboard | http://localhost:3000 |
| Swagger docs | http://localhost:8000/docs |

### Local Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python src/preprocessing/run_pipeline.py --data-dir data/raw/IMS --out-dir data/processed
python src/training/train.py --config configs/vibformer_base.yaml
python src/models/export.py --checkpoint checkpoints/best.pt --output models/vibformer.onnx
uvicorn src.serving.api:app --reload --port 8000
```

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/predict` | `POST` | Single-window RUL inference |
| `/health-index` | `GET` | Current health index for a bearing ID |
| `/ws/telemetry/{bearing_id}` | `WS` | Live streaming health + feature updates |
| `/model/info` | `GET` | Model metadata, input schema, version |
| `/diagnostics/fault` | `POST` | Fault mode classification (OR/IR/RE) |

**Example:**

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"bearing_id": "B1", "features": [[...]]}'
```

```json
{
  "bearing_id": "B1",
  "health_index": 0.412,
  "rul_cycles_estimate": 183,
  "fault_probability": 0.71,
  "fault_mode": "outer_race",
  "confidence": 0.88,
  "timestamp": "2025-01-15T14:32:01Z"
}
```

---

## Performance

Evaluated on IMS Test Run 3 (held out during training):

| Metric | Value |
|--------|-------|
| RUL RMSE | 18.4 cycles |
| RUL MAE | 12.1 cycles |
| Monotonicity Score | 0.97 (baseline transformer: 0.81) |
| Fault Detection Rate | 94.2% (at 24h horizon) |
| False Alarm Rate | 2.1% |
| Inference latency (ONNX, CPU) | ~3.2 ms / window |
| Inference latency (ONNX, INT8) | ~0.9 ms / window |

---

## Limitations & Future Work

**Current limitations:**

- Trained exclusively on IMS data; transfer to FEMTO/PRONOSTIA requires domain adaptation
- Health index is a learned latent proxy, not a physical quantity — treat RUL estimates as ordinal rankings, not precise calendar predictions
- Monotonicity enforced as a soft constraint; rare violations possible under distribution shift

**Planned:**

- Uncertainty quantification via conformal prediction intervals
- Online Bayesian RUL posterior updates
- Multi-asset fleet modeling with hierarchical priors
- Systematic benchmarking vs. LSTM, TCN, and Informer at matched compute

---

## Citation

```bibtex
@software{physics_informed_digital_twin,
  title   = {Physics-Informed Digital Twin for Bearing Prognostics},
  year    = {2025},
  url     = {https://github.com/ujjwal77771/physics-informed-digital-twin},
  license = {MIT}
}
```

---

## License

MIT — see [LICENSE](LICENSE) for full terms.
