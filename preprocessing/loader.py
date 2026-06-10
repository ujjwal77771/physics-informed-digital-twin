# preprocessing/loader.py
# ------------------------------------------------------------------
# Author : Ujjwal Deep
# College: BIT Mesra, Ranchi
# Project: Physics-Informed Digital Twin for RUL Prediction
#
# Reads raw NASA C-MAPSS .txt files and converts them into
# clean numpy arrays that train.py can load directly.
#
# Run this BEFORE training:
#     python preprocessing/loader.py --dataset FD001
#
# Output saved to:
#     data/processed/FD001/X_train.npy
#     data/processed/FD001/y_train.npy
#     data/processed/FD001/X_val.npy
#     data/processed/FD001/y_val.npy
#     data/processed/FD001/X_test.npy
#     data/processed/FD001/y_test.npy
# ------------------------------------------------------------------

import os
import sys
import argparse

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ------------------------------------------------------------------
# C-MAPSS column names (from the dataset README)
# ------------------------------------------------------------------

COLUMNS = (
    ["unit_id", "cycle", "op1", "op2", "op3"]
    + [f"sensor_{i}" for i in range(1, 22)]
)

# These 14 sensors carry useful signal — the rest are near-constant
# and add noise. Identified by the research community (Saxena 2008).
USEFUL_SENSORS = [
    "sensor_2",  "sensor_3",  "sensor_4",  "sensor_7",
    "sensor_8",  "sensor_9",  "sensor_11", "sensor_12",
    "sensor_13", "sensor_14", "sensor_15", "sensor_17",
    "sensor_20", "sensor_21",
]


# ------------------------------------------------------------------
# Load raw .txt file into a DataFrame
# ------------------------------------------------------------------

def load_raw(filepath):
    """
    C-MAPSS files are space-separated with no header row.
    Each row = one engine cycle reading.
    """
    df = pd.read_csv(
        filepath,
        sep=r"\s+",
        header=None,
        names=COLUMNS,
    )
    df = df.dropna(axis=1)   # drop empty trailing columns
    return df


# ------------------------------------------------------------------
# Build piecewise-linear RUL targets
# ------------------------------------------------------------------

def build_rul_targets(df, max_rul=125):
    """
    For each engine, compute remaining useful life at each cycle.

    We use a piecewise linear target (standard in the literature):
      - RUL is capped at max_rul in the early healthy phase
      - then decreases linearly as the engine approaches failure

    This stops the model from being penalised for the healthy phase
    where sensor readings look identical regardless of remaining life.

    Args:
        df      : raw DataFrame with unit_id and cycle columns
        max_rul : cap value (default 125, used in most papers)

    Returns:
        df with a new 'RUL' column added
    """
    # Max cycle for each engine = that engine's failure cycle
    max_cycles = df.groupby("unit_id")["cycle"].max().reset_index()
    max_cycles.columns = ["unit_id", "max_cycle"]

    df = df.merge(max_cycles, on="unit_id")
    df["RUL"] = df["max_cycle"] - df["cycle"]
    df["RUL"] = df["RUL"].clip(upper=max_rul)   # piecewise linear cap
    df = df.drop(columns=["max_cycle"])

    return df


# ------------------------------------------------------------------
# Build sliding window sequences
# ------------------------------------------------------------------

def sliding_windows(df, seq_len=30, sensors=USEFUL_SENSORS):
    """
    Converts a flat DataFrame into overlapping time windows.

    For each engine, we slide a window of length seq_len across
    all its cycles. Each window becomes one training sample.
    The label is the RUL at the LAST timestep of the window.

    Args:
        df      : DataFrame with sensor columns and RUL column
        seq_len : number of timesteps per window
        sensors : list of sensor column names to include

    Returns:
        X : np.ndarray of shape (n_samples, seq_len, n_sensors)
        y : np.ndarray of shape (n_samples,)
    """
    X_list = []
    y_list = []

    for unit_id, group in df.groupby("unit_id"):
        data   = group[sensors].values.astype(np.float32)
        labels = group["RUL"].values.astype(np.float32)

        # Need at least seq_len cycles to build one window
        if len(data) < seq_len:
            continue

        for start in range(len(data) - seq_len + 1):
            end = start + seq_len
            X_list.append(data[start:end])
            y_list.append(labels[end - 1])   # RUL at last step

    X = np.stack(X_list, axis=0)   # (n_samples, seq_len, n_sensors)
    y = np.array(y_list)           # (n_samples,)

    return X, y


# ------------------------------------------------------------------
# Test set handling — C-MAPSS test files are different
# ------------------------------------------------------------------

def load_test_set(test_filepath, rul_filepath, seq_len=30, max_rul=125):
    """
    The C-MAPSS test set doesn't include failure — each engine's
    sequence is truncated at some unknown point before failure.
    True RUL values are provided in a separate file (RUL_FD00X.txt).

    We take the LAST seq_len cycles from each engine as the test sample.
    """
    df_test  = load_raw(test_filepath)
    rul_true = pd.read_csv(rul_filepath, header=None, names=["RUL"])

    df_test  = normalise_sensors(df_test)

    X_list = []
    for unit_id, group in df_test.groupby("unit_id"):
        data = group[USEFUL_SENSORS].values.astype(np.float32)

        if len(data) >= seq_len:
            X_list.append(data[-seq_len:])    # last window
        else:
            # Pad with zeros at the front if sequence is too short
            pad    = np.zeros((seq_len - len(data), len(USEFUL_SENSORS)), dtype=np.float32)
            padded = np.vstack([pad, data])
            X_list.append(padded)

    X_test = np.stack(X_list, axis=0)
    y_test = rul_true["RUL"].values.clip(max=max_rul).astype(np.float32)

    return X_test, y_test


# ------------------------------------------------------------------
# Normalisation — min-max per sensor across training set
# ------------------------------------------------------------------

def normalise_sensors(df, fit_on=None, sensors=USEFUL_SENSORS):
    """
    Min-max normalise each sensor to [0, 1].

    If fit_on is provided (training DataFrame), use its min/max.
    Otherwise fit on df itself (used for standalone normalisation).

    Returns normalised df. Stats are computed on fit_on.
    """
    source = fit_on if fit_on is not None else df

    for col in sensors:
        col_min = source[col].min()
        col_max = source[col].max()
        rng     = col_max - col_min

        if rng > 1e-8:
            df[col] = (df[col] - col_min) / rng
        else:
            df[col] = 0.0   # constant sensor → zero it out

    return df


# ------------------------------------------------------------------
# Main pipeline
# ------------------------------------------------------------------

def build_dataset(dataset_name="FD001", seq_len=30, max_rul=125,
                  val_split=0.1, seed=42):
    """
    Full pipeline from raw files → ready-to-use numpy arrays.

    Args:
        dataset_name : "FD001", "FD002", "FD003", or "FD004"
        seq_len      : sliding window length
        max_rul      : piecewise linear RUL cap
        val_split    : fraction of training engines held out for validation
        seed         : random seed for train/val split

    Returns:
        X_train, y_train, X_val, y_val, X_test, y_test
    """
    raw_dir = os.path.join("data", "raw")

    train_path = os.path.join(raw_dir, f"train_{dataset_name}.txt")
    test_path  = os.path.join(raw_dir, f"test_{dataset_name}.txt")
    rul_path   = os.path.join(raw_dir, f"RUL_{dataset_name}.txt")

    for p in [train_path, test_path, rul_path]:
        if not os.path.exists(p):
            print(f"\n[ERROR] File not found: {p}")
            print("Run this first:  python data/download_cmapss.py")
            sys.exit(1)

    print(f"\n  Loading {dataset_name} raw files...")
    df_train = load_raw(train_path)

    # Normalise training data (fit stats on training set only)
    df_train = normalise_sensors(df_train)

    # Build piecewise-linear RUL targets
    df_train = build_rul_targets(df_train, max_rul=max_rul)

    # Split engines into train / val before windowing
    # (engine-level split avoids data leakage)
    unit_ids      = df_train["unit_id"].unique()
    train_units, val_units = train_test_split(
        unit_ids, test_size=val_split, random_state=seed
    )

    df_tr  = df_train[df_train["unit_id"].isin(train_units)]
    df_val = df_train[df_train["unit_id"].isin(val_units)]

    print(f"  Building sliding windows (seq_len={seq_len})...")
    X_train, y_train = sliding_windows(df_tr,  seq_len=seq_len)
    X_val,   y_val   = sliding_windows(df_val, seq_len=seq_len)

    print(f"  Loading test set...")
    X_test, y_test = load_test_set(test_path, rul_path, seq_len=seq_len, max_rul=max_rul)

    print(f"\n  Dataset summary:")
    print(f"    Train : X={X_train.shape}  y={y_train.shape}")
    print(f"    Val   : X={X_val.shape}  y={y_val.shape}")
    print(f"    Test  : X={X_test.shape}  y={y_test.shape}")

    return X_train, y_train, X_val, y_val, X_test, y_test


def save_processed(dataset_name, X_train, y_train, X_val, y_val, X_test, y_test):
    out_dir = os.path.join("data", "processed", dataset_name)
    os.makedirs(out_dir, exist_ok=True)

    np.save(os.path.join(out_dir, "X_train.npy"), X_train)
    np.save(os.path.join(out_dir, "y_train.npy"), y_train)
    np.save(os.path.join(out_dir, "X_val.npy"),   X_val)
    np.save(os.path.join(out_dir, "y_val.npy"),   y_val)
    np.save(os.path.join(out_dir, "X_test.npy"),  X_test)
    np.save(os.path.join(out_dir, "y_test.npy"),  y_test)

    print(f"\n  Saved to {out_dir}/")


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Preprocess NASA C-MAPSS dataset"
    )
    parser.add_argument(
        "--dataset", type=str, default="FD001",
        choices=["FD001", "FD002", "FD003", "FD004"],
        help="Which sub-dataset to process"
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Process all 4 sub-datasets at once"
    )
    parser.add_argument("--seq_len",   type=int,   default=30)
    parser.add_argument("--max_rul",   type=int,   default=125)
    parser.add_argument("--val_split", type=float, default=0.1)
    args = parser.parse_args()

    datasets = ["FD001", "FD002", "FD003", "FD004"] if args.all else [args.dataset]

    for ds in datasets:
        print(f"\n{'='*50}")
        print(f"  Processing {ds}")
        print(f"{'='*50}")

        X_train, y_train, X_val, y_val, X_test, y_test = build_dataset(
            dataset_name=ds,
            seq_len=args.seq_len,
            max_rul=args.max_rul,
            val_split=args.val_split,
        )
        save_processed(ds, X_train, y_train, X_val, y_val, X_test, y_test)

    print("\nAll done. You can now run:  python training/train.py")