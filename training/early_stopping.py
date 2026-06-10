# training/early_stopping.py
# ------------------------------------------------------------------
# Author : Ujjwal Deep
# College: BIT Mesra, Ranchi
# Project: Physics-Informed Digital Twin for RUL Prediction
#
# Stops training when validation loss stops improving.
# Automatically saves the best model checkpoint.
#
# Usage inside training loop:
#   stopper = EarlyStopping(patience=15, path="best_model.pth")
#   stopper(val_rmse, model)
#   if stopper.early_stop:
#       break
# ------------------------------------------------------------------

import numpy as np
import torch


class EarlyStopping:
    """
    Monitors validation RMSE each epoch.
    Saves model when RMSE improves.
    Stops training after `patience` epochs with no improvement.
    """

    def __init__(self, patience=15, delta=0.0, path="checkpoint.pth", verbose=True):
        """
        Args:
            patience : how many epochs to wait after last improvement
            delta    : minimum improvement to count as improvement
            path     : where to save the best model weights
            verbose  : print a message when model improves
        """
        self.patience   = patience
        self.delta      = delta
        self.path       = path
        self.verbose    = verbose

        self.best_score  = None
        self.early_stop  = False
        self.counter     = 0
        self.best_rmse   = np.inf

    def __call__(self, val_rmse, model):
        score = -val_rmse   # negate because lower RMSE = better

        if self.best_score is None: 
            # First epoch — always save
            self.best_score = score
            self._save(val_rmse, model)

        elif score < self.best_score + self.delta:
            # No improvement
            self.counter += 1
            if self.verbose:
                print(
                    f"  EarlyStopping: no improvement "
                    f"({self.counter}/{self.patience})"
                )
            if self.counter >= self.patience:
                self.early_stop = True

        else:
            # Improvement — reset counter and save
            self.best_score = score
            self._save(val_rmse, model)
            self.counter = 0

    def _save(self, val_rmse, model):
        if self.verbose:
            print(
                f"  Val RMSE improved "
                f"({self.best_rmse:.4f} → {val_rmse:.4f}). "
                f"Saving checkpoint → {self.path}"
            )
        torch.save(model.state_dict(), self.path)
        self.best_rmse = val_rmse