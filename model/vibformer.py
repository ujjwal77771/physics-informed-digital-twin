# model/vibformer.py
# ------------------------------------------------------------------
# Author : Ujjwal Deep
# College: BIT Mesra, Ranchi
# Project: Physics-Informed Digital Twin for RUL Prediction
# ------------------------------------------------------------------

import torch
import torch.nn as nn

class VibFormer(nn.Module):
    """
    VibFormer: A patch-based Transformer architecture for Remaining Useful Life (RUL)
    prediction using multi-sensor vibration and operating telemetry.
    """

    def __init__(self, n_sensors=14, seq_len=30, patch_size=5, d_model=128, n_heads=8, n_layers=4, dropout=0.1):
        """
        Args:
            n_sensors   : number of sensor channels (input dimension)
            seq_len     : temporal sequence length of the window
            patch_size  : size of each temporal patch (must divide seq_len)
            d_model     : dimension of the Transformer embedding
            n_heads     : number of attention heads in the Transformer
            n_layers    : number of Transformer encoder layers
            dropout     : dropout rate
        """
        super().__init__()
        
        assert seq_len % patch_size == 0, f"seq_len ({seq_len}) must be divisible by patch_size ({patch_size})"
        self.num_patches = seq_len // patch_size
        self.patch_size = patch_size
        self.n_sensors = n_sensors
        self.d_model = d_model

        # 1. Patch Projection (Linear projection of flattened patches)
        patch_dim = patch_size * n_sensors
        self.patch_proj = nn.Linear(patch_dim, d_model)

        # 2. Positional Embedding (Learnable)
        self.pos_embed = nn.Parameter(torch.zeros(1, self.num_patches, d_model))
        nn.init.trunc_normal_(self.pos_embed, std=0.02)

        # 3. Transformer Encoder (Pre-LayerNorm architecture)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=n_heads,
            dim_feedforward=d_model * 4,
            dropout=dropout,
            activation='gelu',
            norm_first=True,      # Pre-LN for training stability
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=n_layers)

        # 4. MLP Head
        self.mlp = nn.Sequential(
            nn.Linear(d_model, 64),
            nn.GELU(),
            nn.Linear(64, 1),
            nn.ReLU()             # RUL must be non-negative
        )

    def forward(self, x):
        """
        Args:
            x : input tensor of shape (batch_size, seq_len, n_sensors)
        Returns:
            pred_rul : prediction of shape (batch_size,)
        """
        batch_size, seq_len, n_sensors = x.shape
        
        # 1. Reshape into patches: (batch, num_patches, patch_size * n_sensors)
        x_patches = x.view(batch_size, self.num_patches, self.patch_size * n_sensors)
        
        # 2. Project patches to embedding dimension
        embeddings = self.patch_proj(x_patches)
        
        # 3. Add positional encoding
        embeddings = embeddings + self.pos_embed
        
        # 4. Transformer Encoder layers
        enc_out = self.transformer(embeddings)
        
        # 5. Global Average Pooling over patches: (batch, d_model)
        pooled = enc_out.mean(dim=1)
        
        # 6. MLP regression and squeeze to (batch,)
        pred_rul = self.mlp(pooled).squeeze(-1)
        
        return pred_rul
