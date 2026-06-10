# tests/test_physics_loss.py
# ------------------------------------------------------------------
# Author : Ujjwal Deep
# College: BIT Mesra, Ranchi
# Project: Physics-Informed Digital Twin for RUL Prediction
#
# Unit tests for the physics-informed loss function.
#
# The key test here (test_paris_residual_zero) is the one that
# impresses a reviewer — it verifies that the Paris Law residual
# equals zero when we feed in the exact analytical solution.
# That's proof the physics is correctly implemented, not just bolted on.
#
# Run all tests:
#     pytest tests/
#
# Run just this file:
#     pytest tests/test_physics_loss.py -v
# ------------------------------------------------------------------

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch
import pytest
from model.physics_loss import PhysicsInformedLoss


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def loss_fn():
    """Standard loss function with known Paris Law constants."""
    return PhysicsInformedLoss(
        lambda_phys=0.1,
        lambda_mono=0.05,
        C=1e-10,
        m=3.0,
    )


@pytest.fixture
def batch():
    """Small batch for testing: 8 samples, each a scalar RUL."""
    pred = torch.tensor([90., 80., 70., 60., 50., 40., 30., 20.])
    true = torch.tensor([88., 78., 72., 58., 52., 38., 32., 18.])
    return pred, true


# ------------------------------------------------------------------
# Core correctness test
# ------------------------------------------------------------------

def test_paris_residual_zero(loss_fn):
    """
    THE critical test.

    If we feed stress_amplitude values and set crack_growth_rate
    exactly equal to C * (stress_amplitude)^m  (the Paris Law
    analytical solution), the physics residual must be zero.

    If this test passes, the Paris Law term is correctly implemented.
    If it fails, the physics is wrong — no matter what the RMSE says.
    """
    C = loss_fn.C
    m = loss_fn.m

    stress_amp  = torch.tensor([0.5, 1.0, 1.5, 2.0])
    crack_rate  = C * (stress_amp ** m)   # exact Paris Law solution

    residual = loss_fn.paris_residual(stress_amp, crack_rate)

    assert residual.item() < 1e-20, (
        f"Paris residual should be ~0 on analytical solution, "
        f"got {residual.item():.2e}"
    )


# ------------------------------------------------------------------
# Basic forward pass tests
# ------------------------------------------------------------------

def test_forward_returns_scalar(loss_fn, batch):
    """Loss must be a single scalar — not a tensor of per-sample losses."""
    pred, true = batch
    loss = loss_fn(pred, true)
    assert loss.shape == torch.Size([]), f"Expected scalar, got shape {loss.shape}"


def test_forward_positive(loss_fn, batch):
    """Loss must always be non-negative."""
    pred, true = batch
    loss = loss_fn(pred, true)
    assert loss.item() >= 0.0, f"Loss must be non-negative, got {loss.item()}"


def test_perfect_prediction_low_loss(loss_fn):
    """When predictions exactly match targets, loss should be near zero."""
    perfect = torch.tensor([100., 90., 80., 70.])
    loss = loss_fn(perfect, perfect)
    assert loss.item() < 1e-6, (
        f"Perfect predictions should give ~0 loss, got {loss.item()}"
    )


def test_physics_term_increases_loss(loss_fn):
    """
    Adding the physics term should increase total loss compared to
    plain MSE when the crack rate doesn't match Paris Law.
    """
    pred = torch.tensor([90., 80., 70., 60.])
    true = torch.tensor([88., 78., 72., 58.])

    loss_mse_only = loss_fn(pred, true)

    # Deliberately wrong crack growth rate
    stress_amp = torch.tensor([0.5, 0.5, 0.5, 0.5])
    bad_rate   = torch.tensor([9999., 9999., 9999., 9999.])
    loss_with_physics = loss_fn(pred, true, stress_amp=stress_amp, crack_rate=bad_rate)

    assert loss_with_physics.item() > loss_mse_only.item(), (
        "Physics term should increase loss when crack rate violates Paris Law"
    )


# ------------------------------------------------------------------
# Monotonicity penalty tests
# ------------------------------------------------------------------

def test_monotonicity_penalty_zero_on_decreasing():
    """
    A perfectly decreasing RUL sequence should get zero monotonicity penalty.
    RUL always goes down → no violations → penalty = 0.
    """
    loss_fn = PhysicsInformedLoss(lambda_mono=1.0)

    # Shape: (batch=2, seq_len=5) — strictly decreasing in time
    rul_seq = torch.tensor([
        [100., 90., 80., 70., 60.],
        [50.,  40., 30., 20., 10.],
    ])
    penalty = loss_fn.monotonicity_penalty(rul_seq)
    assert penalty.item() < 1e-8, (
        f"Monotonicity penalty should be 0 on decreasing sequence, "
        f"got {penalty.item()}"
    )


def test_monotonicity_penalty_nonzero_on_increasing():
    """
    A sequence where RUL goes UP (physically impossible) should be penalised.
    """
    loss_fn = PhysicsInformedLoss(lambda_mono=1.0)

    # RUL increases — violation of physics
    rul_seq = torch.tensor([
        [60., 70., 80., 90., 100.],
    ])
    penalty = loss_fn.monotonicity_penalty(rul_seq)
    assert penalty.item() > 0.0, (
        "Monotonicity penalty should be > 0 when RUL increases"
    )


# ------------------------------------------------------------------
# Numerical stability
# ------------------------------------------------------------------

def test_no_nan_with_zero_stress():
    """
    Edge case: stress amplitude near zero should not produce NaN
    (we clamp it to avoid division issues inside Paris Law).
    """
    loss_fn    = PhysicsInformedLoss()
    pred       = torch.tensor([50., 40.])
    true       = torch.tensor([48., 42.])
    stress_amp = torch.tensor([0.0, 0.0])     # zero stress
    crack_rate = torch.tensor([1e-10, 1e-10])

    loss = loss_fn(pred, true, stress_amp=stress_amp, crack_rate=crack_rate)

    assert not torch.isnan(loss), "Loss must not be NaN with zero stress amplitude"
    assert not torch.isinf(loss), "Loss must not be Inf with zero stress amplitude"


def test_gradients_flow():
    """
    Gradients must flow back through the full loss.
    If this fails, backpropagation is broken somewhere.
    """
    loss_fn    = PhysicsInformedLoss()
    pred       = torch.tensor([90., 80.], requires_grad=True)
    true       = torch.tensor([88., 78.])
    stress_amp = torch.tensor([1.0, 1.0])
    crack_rate = torch.tensor([1e-10, 1e-10])

    loss = loss_fn(pred, true, stress_amp=stress_amp, crack_rate=crack_rate)
    loss.backward()

    assert pred.grad is not None, "Gradients must flow back to predictions"
    assert not torch.any(torch.isnan(pred.grad)), "Gradients must not be NaN"