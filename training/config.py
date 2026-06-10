# training/config.py
# ------------------------------------------------------------------
# Author : Ujjwal Deep
# College: BIT Mesra, Ranchi
# Project: Physics-Informed Digital Twin for RUL Prediction
#
# All hyperparameters live here in one place.
# Change values here instead of hunting through the codebase.
# ------------------------------------------------------------------


class Config:
    # --- Data ---
    n_sensors   = 14      # C-MAPSS has 14 useful sensor channels
    seq_len     = 30      # rolling window of 30 time steps
    max_rul     = 125     # cap RUL at 125 (piecewise linear target)

    # --- Model architecture ---
    patch_size  = 5       # 30 steps / 5 = 6 patches fed to Transformer
    d_model     = 128     # embedding dimension
    n_heads     = 8       # attention heads (d_model must be divisible)
    n_layers    = 4       # number of Transformer encoder layers
    dropout     = 0.1

    # --- Training ---
    epochs      = 100
    batch_size  = 64
    lr          = 1e-3
    weight_decay= 1e-4

    # --- Physics loss weights ---
    lambda_phys = 0.1     # Paris Law residual penalty weight
    lambda_mono = 0.05    # Monotonicity penalty weight

    # --- Paris Law material constants (steel) ---
    C           = 1e-10
    m           = 3.0

    # --- Early stopping ---
    patience    = 15


def get_config():
    return Config()