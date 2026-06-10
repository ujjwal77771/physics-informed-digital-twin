# training/train.py
# ------------------------------------------------------------------
# Author : Ujjwal Deep
# College: BIT Mesra, Ranchi
# Project: Physics-Informed Digital Twin for RUL Prediction
#
# Main training loop for VibFormer.
# Run this file directly to train the model:
#     python training/train.py
#
# Or with custom config:
#     python training/train.py --dataset FD001 --epochs 150
# ------------------------------------------------------------------

import os
import sys
import argparse
import time

import numpy as np
import torch
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset

# Make sure imports work from repo root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model.vibformer import VibFormer
from model.physics_loss import PhysicsInformedLoss
from training.evaluate import evaluate
from training.early_stopping import EarlyStopping
from training.config import get_config


# ------------------------------------------------------------------
# Argument parser — lets you change settings from command line
# ------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Train VibFormer on NASA C-MAPSS dataset"
    )
    parser.add_argument(
        "--dataset", type=str, default="FD001",
        choices=["FD001", "FD002", "FD003", "FD004"],
        help="Which C-MAPSS sub-dataset to use"
    )
    parser.add_argument(
        "--epochs", type=int, default=100,
        help="Number of training epochs"
    )
    parser.add_argument(
        "--batch_size", type=int, default=64,
        help="Batch size"
    )
    parser.add_argument(
        "--lr", type=float, default=1e-3,
        help="Initial learning rate"
    )
    parser.add_argument(
        "--lambda_phys", type=float, default=0.1,
        help="Weight on Paris Law physics loss term"
    )
    parser.add_argument(
        "--lambda_mono", type=float, default=0.05,
        help="Weight on monotonicity penalty term"
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--save_dir", type=str, default="checkpoints/",
        help="Where to save model checkpoints"
    )
    return parser.parse_args()


# ------------------------------------------------------------------
# Reproducibility — fixes random seeds so results are the same
# every time you run with the same seed
# ------------------------------------------------------------------

def set_seed(seed):
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


# ------------------------------------------------------------------
# Data loading
# Expects preprocessed .npy files in data/processed/
# Run preprocessing/loader.py first to generate these
# ------------------------------------------------------------------

def load_data(dataset_name, config):
    data_dir = os.path.join("data", "processed", dataset_name)

    try:
        X_train = np.load(os.path.join(data_dir, "X_train.npy"))
        y_train = np.load(os.path.join(data_dir, "y_train.npy"))
        X_val   = np.load(os.path.join(data_dir, "X_val.npy"))
        y_val   = np.load(os.path.join(data_dir, "y_val.npy"))
    except FileNotFoundError:
        print(f"\n[ERROR] Processed data not found at {data_dir}/")
        print("Run this first:  python preprocessing/loader.py")
        sys.exit(1)

    # Convert to PyTorch tensors
    X_train = torch.FloatTensor(X_train)
    y_train = torch.FloatTensor(y_train)
    X_val   = torch.FloatTensor(X_val)
    y_val   = torch.FloatTensor(y_val)

    train_loader = DataLoader(
        TensorDataset(X_train, y_train),
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=2,
        pin_memory=True
    )
    val_loader = DataLoader(
        TensorDataset(X_val, y_val),
        batch_size=config.batch_size,
        shuffle=False,
        num_workers=2,
        pin_memory=True
    )

    print(f"  Train samples : {len(X_train)}")
    print(f"  Val samples   : {len(X_val)}")
    print(f"  Input shape   : {X_train.shape}  (batch, seq_len, n_sensors)")

    return train_loader, val_loader


# ------------------------------------------------------------------
# One training epoch
# Returns average loss across all batches
# ------------------------------------------------------------------

def train_one_epoch(model, loader, criterion, optimizer, device):
    model.train()
    total_loss = 0.0
    n_batches = 0

    for X_batch, y_batch in loader:
        X_batch = X_batch.to(device)
        y_batch = y_batch.to(device)

        optimizer.zero_grad()

        pred_rul = model(X_batch)

        # Compute physics-informed loss
        # We pass stress amplitude as the mean sensor reading
        # (simplified proxy — replace with actual vibration amplitude
        # once STFT features are integrated)
        stress_amp  = X_batch.mean(dim=(1, 2))          # (batch,)
        crack_rate  = torch.ones_like(stress_amp) * 1e-6  # placeholder

        loss = criterion(
            pred_rul=pred_rul,
            true_rul=y_batch,
            stress_amp=stress_amp,
            crack_rate=crack_rate
        )

        loss.backward()

        # Gradient clipping — prevents exploding gradients in Transformer
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)

        optimizer.step()

        total_loss += loss.item()
        n_batches  += 1

    return total_loss / n_batches


# ------------------------------------------------------------------
# Main training function
# ------------------------------------------------------------------

def train(args):
    set_seed(args.seed)

    # Pick GPU if available, otherwise CPU
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n{'='*55}")
    print(f"  Physics-Informed Digital Twin — VibFormer Training")
    print(f"  Author  : Ujjwal Deep | BIT Mesra, Ranchi")
    print(f"  Dataset : {args.dataset}")
    print(f"  Device  : {device}")
    print(f"{'='*55}\n")

    # Load config (hyperparameters from config.py)
    config = get_config()
    config.batch_size   = args.batch_size
    config.epochs       = args.epochs
    config.lr           = args.lr
    config.lambda_phys  = args.lambda_phys
    config.lambda_mono  = args.lambda_mono

    # Load data
    print("[1/4] Loading data...")
    train_loader, val_loader = load_data(args.dataset, config)

    # Build model
    print("[2/4] Building VibFormer...")
    model = VibFormer(
        n_sensors=config.n_sensors,
        seq_len=config.seq_len,
        patch_size=config.patch_size,
        d_model=config.d_model,
        n_heads=config.n_heads,
        n_layers=config.n_layers,
        dropout=config.dropout,
    ).to(device)

    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Trainable parameters: {n_params:,}")

    # Loss function
    criterion = PhysicsInformedLoss(
        lambda_phys=config.lambda_phys,
        lambda_mono=config.lambda_mono,
    )

    # Optimiser + scheduler
    # AdamW with cosine annealing — standard for Transformer training
    optimizer = optim.AdamW(
        model.parameters(),
        lr=config.lr,
        weight_decay=1e-4
    )
    scheduler = optim.lr_scheduler.CosineAnnealingLR(
        optimizer,
        T_max=config.epochs,
        eta_min=1e-6
    )

    # Early stopping — stops training if val loss stops improving
    os.makedirs(args.save_dir, exist_ok=True)
    checkpoint_path = os.path.join(
        args.save_dir, f"vibformer_{args.dataset}_best.pth"
    )
    early_stopper = EarlyStopping(
        patience=15,
        path=checkpoint_path,
        verbose=True
    )

    # ------------------------------------------------------------------
    # Training loop
    # ------------------------------------------------------------------
    print("[3/4] Starting training...\n")
    best_rmse = float("inf")
    history   = {"train_loss": [], "val_rmse": [], "val_score": []}

    for epoch in range(1, config.epochs + 1):
        t_start = time.time()

        train_loss = train_one_epoch(
            model, train_loader, criterion, optimizer, device
        )
        val_rmse, val_score = evaluate(model, val_loader, device)

        scheduler.step()

        elapsed = time.time() - t_start
        lr_now  = optimizer.param_groups[0]["lr"]

        # Log every epoch
        print(
            f"Epoch {epoch:>3}/{config.epochs} | "
            f"Loss: {train_loss:.4f} | "
            f"Val RMSE: {val_rmse:.2f} | "
            f"Score: {val_score:.1f} | "
            f"LR: {lr_now:.2e} | "
            f"{elapsed:.1f}s"
        )

        # Track history
        history["train_loss"].append(train_loss)
        history["val_rmse"].append(val_rmse)
        history["val_score"].append(val_score)

        if val_rmse < best_rmse:
            best_rmse = val_rmse

        # Early stopping check — saves best model automatically
        early_stopper(val_rmse, model)
        if early_stopper.early_stop:
            print(f"\nEarly stopping at epoch {epoch}.")
            break

    # ------------------------------------------------------------------
    # Final summary
    # ------------------------------------------------------------------
    print(f"\n{'='*55}")
    print(f"[4/4] Training complete.")
    print(f"  Best Val RMSE : {best_rmse:.4f}")
    print(f"  Checkpoint    : {checkpoint_path}")
    print(f"{'='*55}\n")

    # Save training history for plotting in notebooks
    history_path = os.path.join(
        args.save_dir, f"history_{args.dataset}.npy"
    )
    np.save(history_path, history)
    print(f"  Training history saved to {history_path}")

    return model, history


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    args = parse_args()
    train(args)