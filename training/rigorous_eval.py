import os
import sys
import json
import torch
import torch.nn as nn
import numpy as np
from torch.utils.data import DataLoader, TensorDataset
from sklearn.metrics import mean_squared_error, mean_absolute_error

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model.vibformer import VibFormer
from model.physics_loss import PhysicsInformedLoss

class LSTMBaseline(nn.Module):
    def __init__(self, input_dim=14, hidden_dim=64, num_layers=2):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_dim, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])

def evaluate_model(model, dataloader, device):
    model.eval()
    all_preds, all_targets = [], []
    with torch.no_grad():
        for x, y in dataloader:
            x, y = x.to(device), y.to(device)
            preds = model(x)
            all_preds.extend(preds.cpu().numpy().flatten())
            all_targets.extend(y.cpu().numpy().flatten())
    all_preds = np.array(all_preds)
    all_targets = np.array(all_targets)
    rmse = np.sqrt(mean_squared_error(all_targets, all_preds))
    mae = mean_absolute_error(all_targets, all_preds)
    diffs = all_preds[1:] - all_preds[:-1]
    monotonic_steps = np.sum(diffs <= 0)
    monotonicity_score = monotonic_steps / len(diffs) if len(diffs) > 0 else 0
    return rmse, mae, monotonicity_score

def load_combined_data(dataset_names, batch_size=64, shuffle=True):
    X_list, y_list = [], []
    for d in dataset_names:
        d_path = os.path.join("data", "processed", d)
        if not os.path.exists(d_path): continue
        X_list.append(np.load(os.path.join(d_path, "X_train.npy")))
        y_list.append(np.load(os.path.join(d_path, "y_train.npy")))
    if not X_list: return None
    dataset = TensorDataset(torch.FloatTensor(np.concatenate(X_list, axis=0)), torch.FloatTensor(np.concatenate(y_list, axis=0)))
    return DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)

def run_experiment():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    runs = ["FD001", "FD002", "FD003"]
    variants = [
        {"name": "LSTM_Baseline", "is_vibformer": False, "use_phys": False, "use_mono": False},
        {"name": "VibFormer_Data_Only", "is_vibformer": True, "use_phys": False, "use_mono": False},
        {"name": "VibFormer_Physics_Only", "is_vibformer": True, "use_phys": True, "use_mono": False},
        {"name": "VibFormer_Mono_Only", "is_vibformer": True, "use_phys": False, "use_mono": True},
        {"name": "VibFormer_Full", "is_vibformer": True, "use_phys": True, "use_mono": True},
    ]
    results = {v["name"]: {"rmse": [], "mae": [], "mono": []} for v in variants}
    epochs = 5
    
    for test_run_idx in range(3):
        test_run = runs[test_run_idx]
        train_runs = [r for i, r in enumerate(runs) if i != test_run_idx]
        print(f"\n--- Fold {test_run_idx+1}/3 | Train: {train_runs} | Test: {test_run} ---")
        train_loader = load_combined_data(train_runs, batch_size=64, shuffle=True)
        test_loader = load_combined_data([test_run], batch_size=64, shuffle=False)
        if not train_loader or not test_loader: continue
            
        for variant in variants:
            print(f"Training {variant['name']}...")
            model = VibFormer(n_sensors=14, seq_len=30, patch_size=5).to(device) if variant["is_vibformer"] else LSTMBaseline(input_dim=14).to(device)
            optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
            criterion = PhysicsInformedLoss(lambda_phys=0.1 if variant["use_phys"] else 0.0, lambda_mono=0.05 if variant["use_mono"] else 0.0, C=1.5e-11, m=3.0)
            
            model.train()
            for epoch in range(epochs):
                for X_batch, y_batch in train_loader:
                    X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                    optimizer.zero_grad()
                    preds = model(X_batch)
                    if variant["is_vibformer"]:
                        loss = criterion(preds, y_batch, X_batch.mean(dim=(1, 2)), torch.ones_like(X_batch.mean(dim=(1, 2))) * 1e-6)
                    else:
                        loss = nn.MSELoss()(preds.squeeze(), y_batch.squeeze())
                    loss.backward()
                    optimizer.step()
                    
            rmse, mae, mono = evaluate_model(model, test_loader, device)
            print(f"  -> RMSE: {rmse:.2f} | MAE: {mae:.2f} | Mono: {mono:.3f}")
            results[variant["name"]]["rmse"].append(float(rmse))
            results[variant["name"]]["mae"].append(float(mae))
            results[variant["name"]]["mono"].append(float(mono))

    for name, metrics in results.items():
        if not metrics["rmse"]: continue
        rmse_mean = np.mean(metrics['rmse'])
        rmse_std  = np.std(metrics['rmse'], ddof=1)   # sample std (ddof=1), correct for n=3
        mae_mean  = np.mean(metrics['mae'])
        print(f"\n{name}:")
        print(f"  RMSE (mean): {rmse_mean:.2f}")
        print(f"  RMSE (sample std, ddof=1): {rmse_std:.2f}")
        print(f"  MAE  (mean): {mae_mean:.2f}")
        print(f"  Per-fold RMSE: {[round(v,2) for v in metrics['rmse']]}")
        
if __name__ == "__main__":
    run_experiment()
