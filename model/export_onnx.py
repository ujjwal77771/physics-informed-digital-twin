# model/export_onnx.py
# ------------------------------------------------------------------
# Author : Ujjwal Deep
# College: BIT Mesra, Ranchi
# Project: Physics-Informed Digital Twin for RUL Prediction
# ------------------------------------------------------------------

import os
import sys
import torch

# Ensure imports work from repo root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model.vibformer import VibFormer
from training.config import get_config

def export_model(checkpoint_path=None, output_path="model/vibformer.onnx"):
    """
    Exports the PyTorch VibFormer model to ONNX format.
    """
    config = get_config()
    
    # 1. Initialize model
    model = VibFormer(
        n_sensors=config.n_sensors,
        seq_len=config.seq_len,
        patch_size=config.patch_size,
        d_model=config.d_model,
        n_heads=config.n_heads,
        n_layers=config.n_layers,
        dropout=config.dropout,
    )
    
    # 2. Load weights if a checkpoint is provided
    if checkpoint_path and os.path.exists(checkpoint_path):
        print(f"Loading weights from {checkpoint_path}...")
        model.load_state_dict(torch.load(checkpoint_path, map_location=torch.device('cpu')))
    else:
        print("No checkpoint found. Exporting model with random weights (for structural validation).")
        
    model.eval()
    
    # 3. Create dummy input matching the shape (batch_size, seq_len, n_sensors)
    dummy_input = torch.randn(1, config.seq_len, config.n_sensors, dtype=torch.float32)
    
    # 4. Export to ONNX
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    print(f"Exporting model to ONNX format at: {output_path}...")
    torch.onnx.export(
        model,
        dummy_input,
        output_path,
        export_params=True,        # Store the trained parameter weights inside the model file
        opset_version=14,          # ONNX opset version
        do_constant_folding=True,  # Inline constant values for optimization
        input_names=['sensor_sequence'],
        output_names=['predicted_rul'],
        dynamic_axes={             # Enable dynamic batch sizing
            'sensor_sequence': {0: 'batch_size'},
            'predicted_rul': {0: 'batch_size'}
        }
    )
    
    print("Verifying exported ONNX model...")
    try:
        import onnx
        onnx_model = onnx.load(output_path)
        onnx.checker.check_model(onnx_model)
        print("✓ ONNX model successfully verified and is structurally correct!")
    except ImportError:
        print("onxx library not installed. Skipping structural validation check.")
    except Exception as e:
        print(f"ONNX validation failed: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Export VibFormer to ONNX")
    parser.add_argument("--checkpoint", type=str, default=None, help="Path to PyTorch .pth checkpoint")
    parser.add_argument("--output", type=str, default="model/vibformer.onnx", help="Output path for .onnx file")
    args = parser.parse_args()
    
    export_model(args.checkpoint, args.output)
