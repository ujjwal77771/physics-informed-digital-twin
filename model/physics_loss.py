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
      2. Physics residual loss (Power-Law degradation rate)
      3. Monotonicity penalty (enforces that RUL only decreases over time)
    """

    def __init__(self, lambda_phys=0.1, lambda_mono=0.05, C=1e-10, m=3.0):
        """
        Args:
            lambda_phys : weight for the Power-Law physics residual
            lambda_mono : weight for the monotonicity penalty
            C           : Power-Law scale constant
            m           : Power-Law exponent constant
        """
        super().__init__()
        self.lambda_phys = lambda_phys
        self.lambda_mono = lambda_mono
        self.C = C
        self.m = m

    def power_law_residual(self, sensor_health_index, observed_wear_rate):
        """
        Computes the residual penalty for deviating from a standard Power-Law
        degradation curve: wear_rate = C * (sensor_health_index)^m
        """
        # Clamp index to avoid negative values or division by zero issues
        clamped_index = torch.clamp(sensor_health_index, min=1e-12)
        power_law_rate = self.C * (clamped_index ** self.m)
        return torch.mean((observed_wear_rate - power_law_rate) ** 2)

    def monotonicity_penalty(self, rul_seq):
        """
        Penalizes sequences where RUL increases over time.
        rul_seq can be of shape (batch, seq_len) or (seq_len,)
        """
        if rul_seq.ndim == 1:
            rul_seq = rul_seq.unsqueeze(0)  # shape: (1, seq_len)

        diff = rul_seq[:, 1:] - rul_seq[:, :-1]
        violations = torch.clamp(diff, min=0.0)
        return torch.mean(violations ** 2)

    def forward(self, pred_rul, true_rul, sensor_health_index=None, observed_wear_rate=None):
        """
        Computes the total physics-informed loss.
        """
        pred_rul = pred_rul.squeeze()
        true_rul = true_rul.squeeze()

        loss_data = torch.mean((pred_rul - true_rul) ** 2)

        loss_phys = 0.0
        if sensor_health_index is not None and observed_wear_rate is not None:
            sensor_health_index = sensor_health_index.squeeze()
            observed_wear_rate = observed_wear_rate.squeeze()
            loss_phys = self.power_law_residual(sensor_health_index, observed_wear_rate)

        loss_mono = 0.0
        if self.lambda_mono > 0:
            loss_mono = self.monotonicity_penalty(pred_rul)

        return loss_data + self.lambda_phys * loss_phys + self.lambda_mono * loss_mono
