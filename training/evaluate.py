# training/evaluate.py
# ------------------------------------------------------------------
# Author : Ujjwal Deep
# College: BIT Mesra, Ranchi
# Project: Physics-Informed Digital Twin for RUL Prediction

# Two evaluation metrics used in C-MAPSS literature:
#   1. RMSE  — standard regression error
#   2. NASA Score Function — asymmetric, penalises late predictions
#      more than early ones (critical for safety applications

import numpy as np
import torch


def nasa_score(y_true, y_pred):
    """
    NASA asymmetric score function from the PHM08 challenge.

    For each engine:
      d = predicted_RUL - true_RUL
      score = exp(-d/13) - 1   if d < 0  (predicted early — less penalty)
      score = exp(d/10)  - 1   if d >= 0 (predicted late  — more penalty)

    Lower is better. A perfect prediction scores 0.
    """
    d = y_pred - y_true
    scores = np.where(d < 0, np.exp(-d / 13) - 1, np.exp(d / 10) - 1)
    return float(np.sum(scores))


def evaluate(model, loader, device):
    """
    Run the model on a DataLoader and return RMSE + NASA Score.

    Args:
        model   : trained VibFormer
        loader  : DataLoader with (X, y_true) batches
        device  : torch device

    Returns:
        rmse    : float
        score   : float (NASA Score)
    """
    model.eval()
    all_preds  = []
    all_labels = []

    with torch.no_grad():
        for X_batch, y_batch in loader:
            X_batch = X_batch.to(device)
            preds   = model(X_batch).cpu().numpy()
            labels  = y_batch.numpy()

            all_preds.append(preds)
            all_labels.append(labels)

    y_pred = np.concatenate(all_preds)
    y_true = np.concatenate(all_labels)

    rmse  = float(np.sqrt(np.mean((y_pred - y_true) ** 2)))
    score = nasa_score(y_true, y_pred)

    return rmse, score