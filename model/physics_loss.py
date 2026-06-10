# model/physics_loss.py
# ------------------------------------------------------------------
# Author : Ujjwal Deep
# College: BIT Mesra, Ranchi
# Project: Physics-Informed Digital Twin for RUL Prediction
# ------------------------------------------------------------------

import torch
import torch.nn as nn

class PhysicsInformedLoss(nn.Module):
    """
    Physics-Informed Loss function that combines:
      1. Data-driven loss (MSE)
      2. Physics residual loss (Paris' Law for crack propagation)
      3. Monotonicity penalty (enforces that RUL only decreases over time)
    """

    def __init__(self, lambda_phys=0.1, lambda_mono=0.05, C=1e-10, m=3.0):
        """
        Args:
            lambda_phys : weight for the Paris Law physics residual
            lambda_mono : weight for the monotonicity penalty
            C           : Paris Law material constant
            m           : Paris Law exponent constant
        """
        super().__init__()
        self.lambda_phys = lambda_phys
        self.lambda_mono = lambda_mono
        self.C = C
        self.m = m

    def paris_residual(self, stress_amp, crack_rate):
        """
        Computes the residual penalty for deviating from Paris' Law:
        da/dN = C * (delta_K)^m
        We approximate delta_K using stress amplitude.
        """
        # Clamp stress_amp to avoid negative values or division by zero issues
        clamped_stress = torch.clamp(stress_amp, min=1e-12)
        paris_rate = self.C * (clamped_stress ** self.m)
        return torch.mean((crack_rate - paris_rate) ** 2)

    def monotonicity_penalty(self, rul_seq):
        """
        Penalizes sequences where RUL increases over time.
        rul_seq can be of shape (batch, seq_len) or (seq_len,)
        """
        if rul_seq.ndim == 1:
            rul_seq = rul_seq.unsqueeze(0)  # shape: (1, seq_len)

        # diff[i] = RUL[i+1] - RUL[i]
        # Since RUL should decrease, diff should be <= 0.
        # Any positive values are violations.
        diff = rul_seq[:, 1:] - rul_seq[:, :-1]
        violations = torch.clamp(diff, min=0.0)
        return torch.mean(violations ** 2)

    def forward(self, pred_rul, true_rul, stress_amp=None, crack_rate=None):
        """
        Computes the total physics-informed loss.
        """
        # Squeeze inputs to ensure shape consistency
        pred_rul = pred_rul.squeeze()
        true_rul = true_rul.squeeze()

        # Data loss (MSE)
        loss_data = torch.mean((pred_rul - true_rul) ** 2)

        # Physics loss (Paris Law)
        loss_phys = 0.0
        if stress_amp is not None and crack_rate is not None:
            stress_amp = stress_amp.squeeze()
            crack_rate = crack_rate.squeeze()
            loss_phys = self.paris_residual(stress_amp, crack_rate)

        # Monotonicity loss
        loss_mono = 0.0
        if self.lambda_mono > 0:
            loss_mono = self.monotonicity_penalty(pred_rul)

        return loss_data + self.lambda_phys * loss_phys + self.lambda_mono * loss_mono
