# physics-informed-digital-twin
# Physics-Informed Digital Twin for RUL Prediction
### Multi-Sensor Vibration Analytics · Transformer Networks · Paris Law Physics Constraints

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-red.svg)](https://pytorch.org)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-orange.svg)](https://streamlit.io)
[![Dataset](https://img.shields.io/badge/Dataset-NASA%20C--MAPSS-green.svg)](https://www.nasa.gov/intelligent-systems-division)

---

## What this project does

Standard Transformer models for Remaining Useful Life (RUL) prediction treat machinery as a black box — they learn patterns from sensor data but ignore the physical laws governing how components actually degrade.

This project embeds **Paris Law crack propagation physics** directly into the loss function, forcing the model to make predictions that are not just statistically accurate but physically consistent. The result is a **digital twin** that mirrors real engine degradation behaviour rather than just fitting a curve to training data.

Built on the NASA C-MAPSS turbofan engine dataset. Deployed as a real-time Streamlit dashboard.

---

## For researchers

### The core research problem

Predictive maintenance models based on purely data-driven approaches suffer from a fundamental limitation: they can produce predictions that violate physical constraints. A model might predict RUL increasing over time, or degradation curves that are inconsistent with known material fatigue mechanics. This is particularly problematic in safety-critical industrial systems.

### Proposed contribution

We introduce a **physics-informed loss function** that combines three terms:

```
L_total = L_data + λ_phys · L_paris + λ_mono · L_monotonic
```

Where:

- **L_data** — standard MSE between predicted and true RUL
- **L_paris** — residual penalty from Paris Law: `da/dN = C · (ΔK)^m`  
  Penalises predictions whose implied crack growth rate deviates from Paris Law
- **L_monotonic** — enforces that RUL predictions decrease monotonically over a degradation sequence

### Architecture: VibFormer

```
Input sensors (14 channels, 30 timesteps)
        │
        ▼
  Patch Embedding          ← splits sequence into 6 patches of 5 steps
  (patch_size=5, d=128)      preserves local temporal structure
        │
        ▼
  Positional Encoding      ← learnable, one embedding per patch
        │
        ▼
  Transformer Encoder      ← 4 layers, 8 heads, Pre-LN for stability
  (d_model=128)
        │
        ▼
  Global Average Pool      ← aggregate across all patches
        │
        ▼
  MLP Regression Head      ← Linear(128→64) → GELU → Linear(64→1) → ReLU
        │
        ▼
  Predicted RUL (scalar)
```

### Why patch embedding matters

Standard Transformers apply attention across individual timesteps. For vibration signals, local temporal patterns (e.g., bearing defect harmonics appearing over 3–5 consecutive cycles) carry diagnostic information. Patch embedding groups timesteps before attention runs, preventing the model from treating each timestep as an independent token and losing these local structures.

### Datasets

| Dataset | Source | Engines | Operating conditions | Fault modes |
|---|---|---|---|---|
| C-MAPSS FD001 | NASA | 100 train / 100 test | 1 | 1 |
| C-MAPSS FD002 | NASA | 260 train / 259 test | 6 | 1 |
| C-MAPSS FD003 | NASA | 100 train / 100 test | 1 | 2 |
| C-MAPSS FD004 | NASA | 249 train / 248 test | 6 | 2 |

### Evaluation metrics

**RMSE** — standard regression error  
**NASA Score Function** — asymmetric penalty that punishes late predictions more than early ones (relevant for safety):

```
s = Σ exp(-y/13) - 1   if ŷ < y   (early prediction)
s = Σ exp(y/10) - 1    if ŷ ≥ y   (late prediction — penalised more)
```

### Related work

This project builds on and extends:
- Vaswani et al., "Attention Is All You Need" (NeurIPS 2017)
- Raissi et al., "Physics-Informed Neural Networks" (JCP 2019)
- Li et al., "Remaining Useful Life Estimation Using Transformer" (IEEE TII 2021)
- Paris & Erdogan, "A Critical Analysis of Crack Propagation Laws" (J. Basic Eng. 1963)

---

## For developers / recruiters

### Quick start

```bash
# Clone and install
git clone https://github.com/YOUR-USERNAME/physics-informed-digital-twin.git
cd physics-informed-digital-twin
pip install -r requirements.txt

# Download C-MAPSS dataset
python data/download_cmapss.py

# Train the model
python training/train.py --dataset FD001 --epochs 100

# Launch the dashboard
streamlit run dashboard/app.py
```

### Project structure

```
physics-informed-digital-twin/
│
├── data/
│   ├── raw/                    # NASA C-MAPSS .txt files (downloaded)
│   ├── processed/              # Normalised numpy arrays
│   └── download_cmapss.py      # Auto-download script
│
├── preprocessing/
│   ├── loader.py               # Load and parse C-MAPSS files
│   ├── normalise.py            # Min-max normalisation per sensor
│   ├── stft_features.py        # Short-Time Fourier Transform features
│   └── health_indicator.py     # Composite health index construction
│
├── model/
│   ├── patch_embedding.py      # Patch-based sequence tokenisation
│   ├── positional_encoding.py  # Learnable positional embeddings
│   ├── vibformer.py            # Main Transformer architecture
│   ├── physics_loss.py         # Paris Law + monotonicity loss
│   └── baseline_lstm.py        # LSTM baseline for comparison
│
├── training/
│   ├── train.py                # Full training loop
│   ├── evaluate.py             # RMSE + NASA Score evaluation
│   ├── config.py               # Hyperparameters
│   └── early_stopping.py       # Early stopping callback
│
├── dashboard/
│   ├── app.py                  # Main Streamlit app
│   ├── stream_simulator.py     # Real-time sensor stream simulation
│   └── visualise.py            # Plotly chart components
│
├── notebooks/
│   ├── 01_data_exploration.ipynb
│   ├── 02_feature_engineering.ipynb
│   ├── 03_model_training.ipynb
│   ├── 04_results_analysis.ipynb
│   └── 05_ablation_study.ipynb
│
├── tests/
│   ├── test_physics_loss.py    # Verifies Paris residual = 0 on analytical solution
│   ├── test_vibformer.py       # Forward pass shape checks
│   └── test_preprocessing.py  # Data pipeline unit tests
│
├── requirements.txt
├── setup.py
└── README.md
```

### Key design decisions

**Why not LSTM?** — LSTMs process sequences step-by-step, making parallelisation difficult and limiting the model's ability to capture long-range dependencies across a degradation trajectory. Transformers handle the full sequence in parallel and attend to any timestep from any other.

**Why patch embedding?** — Avoids treating each of 30 timesteps as independent tokens. Groups 5 consecutive steps into patches, preserving local vibration patterns before global attention.

**Why physics loss?** — Pure MSE training allows physically impossible predictions (RUL increasing, step-jumps). The Paris Law term anchors predictions to real crack propagation mechanics. The monotonicity term enforces the basic physical reality that healthy time remaining only decreases.

### Tech stack

| Component | Technology |
|---|---|
| Model training | PyTorch 2.0 |
| Data processing | NumPy, Pandas, SciPy |
| Feature extraction | SciPy STFT |
| Dashboard | Streamlit + Plotly |
| Testing | pytest |

---

## Results (expected)

| Model | FD001 RMSE | FD001 Score | FD002 RMSE |
|---|---|---|---|
| LSTM baseline | ~18.2 | ~320 | ~26.1 |
| Plain Transformer | ~15.8 | ~280 | ~22.4 |
| **VibFormer (ours)** | **~13.1** | **~210** | **~19.7** |

*Results to be updated as experiments complete.*

---

## Author
UJJWAL DEEP
2nd year Mechanical Engineering student  
Motivated by observations during industrial internship with rotating machinery systems.

---

## License

MIT License — see `LICENSE` for details.
