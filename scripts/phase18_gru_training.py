"""
Phase 18 -- GRU Model Training
==============================
SIH25071 Rockfall Prediction

Trains a single-layer GRU sequence-to-one classifier on the 14-day temporal
sequences constructed in Phase 17, using inverse-frequency class weights
computed strictly from sequence-level train labels.

Design decisions (locked, see WORK.md Phase 18):
  - Framework: PyTorch
  - Architecture: Single-layer nn.GRU(hidden_size=64, batch_first=True) -> Dropout(0.2) -> Linear(64, 3)
  - No softmax in forward pass: nn.CrossEntropyLoss computes softmax internally over raw logits.
  - Loss: nn.CrossEntropyLoss(weight=weight_tensor) using balanced class weights from y_train_seq.
  - Early stopping: Monitored on val_loss (val_sequences.npz, 912 samples), patience 8 epochs.
  - Test set (test_sequences.npz, 1136 samples) is held out completely for Phase 19.
  - No oversampling/SMOTE applied to sequences (avoids whole-trajectory duplication).

Run from repo root:
    python scripts/phase18_gru_training.py
"""

from __future__ import annotations

import copy
import json
import random
import sys
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.utils.class_weight import compute_class_weight
from torch.utils.data import DataLoader, TensorDataset

# Ensure UTF-8 output encoding on Windows if supported
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Hyperparameters & Configuration
# ---------------------------------------------------------------------------
CONFIG: dict[str, Any] = {
    "model_name": "gru-v1-20260821",
    "window_length": 14,
    "input_features": 10,
    "hidden_size": 64,
    "num_layers": 1,
    "num_classes": 3,
    "dropout": 0.2,
    "batch_size": 32,
    "learning_rate": 1e-3,
    "max_epochs": 100,
    "patience": 8,
    "min_delta": 1e-4,
    "random_seed": 42,
}

# ---------------------------------------------------------------------------
# Paths (relative to repo root)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
SEQUENCES_DIR = DATA_DIR / "sequences"
MODELS_DIR = REPO_ROOT / "models"
MODELS_DIR.mkdir(exist_ok=True)

TRAIN_NPZ = SEQUENCES_DIR / "train_sequences.npz"
VAL_NPZ = SEQUENCES_DIR / "val_sequences.npz"
TEST_NPZ = SEQUENCES_DIR / "test_sequences.npz"
MANIFEST_JSON = SEQUENCES_DIR / "manifest.json"

FEATURE_ORDER_JSON = MODELS_DIR / "feature_order.json"
LABEL_ENCODING_JSON = MODELS_DIR / "label_encoding.json"

MODEL_OUT_PATH = MODELS_DIR / f"{CONFIG['model_name']}.pt"
CONFIG_OUT_PATH = MODELS_DIR / f"{CONFIG['model_name']}_config.json"


# ---------------------------------------------------------------------------
# Reproducibility
# ---------------------------------------------------------------------------
def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


# ---------------------------------------------------------------------------
# PyTorch GRU Architecture
# ---------------------------------------------------------------------------
class GRUClassifier(nn.Module):
    """
    Single-layer GRU sequence-to-one classifier.

    Input shape:  (batch_size, seq_len=14, input_size=10)
    Output shape: (batch_size, num_classes=3) -- raw unnormalized logits
    """

    def __init__(
        self,
        input_size: int = 10,
        hidden_size: int = 64,
        num_classes: int = 3,
        dropout: float = 0.2,
    ) -> None:
        super().__init__()
        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=1,
            batch_first=True,
            bidirectional=False,
        )
        self.dropout = nn.Dropout(p=dropout)
        self.fc = nn.Linear(hidden_size, num_classes)

        # NOTE: No nn.Softmax layer is included here.
        # nn.CrossEntropyLoss applies log-softmax internally for numerical stability.
        # This module outputs raw logits directly from the Linear layer.

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch_size, seq_len, input_size)
        # _, h_n: h_n shape is (num_layers, batch_size, hidden_size) = (1, batch_size, hidden_size)
        _, h_n = self.gru(x)

        # Sequence-to-one: extract final hidden state across all batches
        final_hidden = h_n[-1]  # (batch_size, hidden_size)
        dropped = self.dropout(final_hidden)
        logits = self.fc(dropped)  # (batch_size, num_classes)
        return logits


# ---------------------------------------------------------------------------
# Main Execution Pipeline
# ---------------------------------------------------------------------------
def main() -> None:
    print("=" * 70)
    print("  Phase 18 -- GRU Model Training (PyTorch)")
    print("=" * 70)

    set_seed(CONFIG["random_seed"])

    # 1. Verify PyTorch installation and hardware
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("\n[1] Environment & Framework:")
    print(f"  PyTorch version: {torch.__version__}")
    print(f"  Compute device:  {device}")

    # 2. Load sequence datasets (.npz)
    print(f"\n[2] Loading sequence datasets from {SEQUENCES_DIR} ...")
    assert TRAIN_NPZ.exists(), f"Missing {TRAIN_NPZ}"
    assert VAL_NPZ.exists(), f"Missing {VAL_NPZ}"
    assert TEST_NPZ.exists(), f"Missing {TEST_NPZ}"

    train_data = np.load(TRAIN_NPZ)
    val_data = np.load(VAL_NPZ)
    test_data = np.load(TEST_NPZ)

    X_train, y_train_seq = train_data["X"], train_data["y"]
    X_val, y_val_seq = val_data["X"], val_data["y"]
    X_test, y_test_seq = test_data["X"], test_data["y"]

    print(f"  Train sequences: X={X_train.shape} (dtype={X_train.dtype}), y={y_train_seq.shape} (dtype={y_train_seq.dtype})")
    print(f"  Val sequences:   X={X_val.shape} (dtype={X_val.dtype}), y={y_val_seq.shape} (dtype={y_val_seq.dtype})")
    print(f"  Test sequences:  X={X_test.shape} (dtype={X_test.dtype}), y={y_test_seq.shape} (dtype={y_test_seq.dtype})")

    # Strict assertion on exact sequence counts from Phase 17
    assert y_train_seq.shape[0] == 3440, f"Expected 3440 train sequences, got {y_train_seq.shape[0]}"
    assert y_val_seq.shape[0] == 912, f"Expected 912 val sequences, got {y_val_seq.shape[0]}"
    assert y_test_seq.shape[0] == 1136, f"Expected 1136 test sequences, got {y_test_seq.shape[0]}"
    assert X_train.shape[1:] == (14, 10), f"Expected train X shape (n, 14, 10), got {X_train.shape}"
    assert X_val.shape[1:] == (14, 10), f"Expected val X shape (n, 14, 10), got {X_val.shape}"
    assert X_test.shape[1:] == (14, 10), f"Expected test X shape (n, 14, 10), got {X_test.shape}"
    print("  [OK] Sequence counts and tensor shapes strictly verified against Phase 17 manifest.")

    # 3. Verify feature order and label encoding consistency
    print("\n[3] Verifying schema alignment ...")
    manifest = json.loads(MANIFEST_JSON.read_text())
    feature_order = json.loads(FEATURE_ORDER_JSON.read_text())
    label_encoding = json.loads(LABEL_ENCODING_JSON.read_text())

    assert feature_order == manifest["feature_order"], (
        f"Feature order mismatch between models/feature_order.json and manifest.json!\n"
        f"models:   {feature_order}\nmanifest: {manifest['feature_order']}"
    )
    assert label_encoding == manifest["label_encoding"], (
        f"Label encoding mismatch between models/label_encoding.json and manifest.json!\n"
        f"models:   {label_encoding}\nmanifest: {manifest['label_encoding']}"
    )
    print(f"  [OK] Feature order matches manifest exactly: {feature_order}")
    print(f"  [OK] Label encoding matches manifest exactly: {label_encoding}")

    # 4. Compute balanced class weights on sequence-level train labels ONLY
    print("\n[4] Computing class weights from train sequences (y_train_seq only) ...")
    classes = np.array([0, 1, 2])
    class_weights_np = compute_class_weight(
        class_weight="balanced",
        classes=classes,
        y=y_train_seq,
    )
    weight_tensor = torch.tensor(class_weights_np, dtype=torch.float32).to(device)

    train_class_counts = {
        name: int(np.sum(y_train_seq == code))
        for name, code in label_encoding.items()
    }
    total_train = len(y_train_seq)
    print("  Train class breakdown:")
    for name, code in label_encoding.items():
        count = train_class_counts[name]
        pct = 100.0 * count / total_train
        w = class_weights_np[code]
        print(f"    Class {code} ({name:10s}): {count:5d} ({pct:5.2f}%) -> computed weight: {w:.4f}")

    print(f"  Resulting PyTorch weight vector: {[round(float(x), 4) for x in weight_tensor.tolist()]}")
    # Sanity check: evacuation weight must exceed safe weight
    assert class_weights_np[label_encoding["evacuation"]] > class_weights_np[label_encoding["safe"]], (
        "Evacuation class weight should be significantly higher than safe class weight due to class imbalance."
    )
    print("  [OK] Class weight sanity check passed (evacuation weight > safe weight).")

    # 5. Build DataLoaders (train + val only; test split is held out)
    train_dataset = TensorDataset(
        torch.tensor(X_train, dtype=torch.float32),
        torch.tensor(y_train_seq, dtype=torch.long),
    )
    val_dataset = TensorDataset(
        torch.tensor(X_val, dtype=torch.float32),
        torch.tensor(y_val_seq, dtype=torch.long),
    )

    train_loader = DataLoader(
        train_dataset,
        batch_size=CONFIG["batch_size"],
        shuffle=True,
        drop_last=False,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=CONFIG["batch_size"],
        shuffle=False,
        drop_last=False,
    )

    # 6. Initialize Model, Loss, Optimizer
    print("\n[5] Initializing GRU model & training setup ...")
    model = GRUClassifier(
        input_size=CONFIG["input_features"],
        hidden_size=CONFIG["hidden_size"],
        num_classes=CONFIG["num_classes"],
        dropout=CONFIG["dropout"],
    ).to(device)

    total_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"  Architecture: GRU({CONFIG['input_features']} -> {CONFIG['hidden_size']}) -> Dropout({CONFIG['dropout']}) -> Linear({CONFIG['hidden_size']} -> {CONFIG['num_classes']})")
    print(f"  Trainable parameters: {total_params:,}")
    print(f"  Loss function: nn.CrossEntropyLoss(weight={[round(float(x), 4) for x in weight_tensor.tolist()]})")
    print(f"  Optimizer: Adam(lr={CONFIG['learning_rate']})")
    print(f"  Early stopping: patience={CONFIG['patience']}, min_delta={CONFIG['min_delta']}")

    criterion = nn.CrossEntropyLoss(weight=weight_tensor)
    optimizer = optim.Adam(model.parameters(), lr=CONFIG["learning_rate"])

    # 7. Training Loop with Early Stopping on Validation Loss
    print(f"\n[6] Starting training loop (max {CONFIG['max_epochs']} epochs) ...")
    print(f"  {'Epoch':>6s} | {'Train Loss':>12s} | {'Val Loss':>12s} | {'Best Val':>12s} | {'Status':>10s}")
    print("  " + "-" * 62)

    best_val_loss = float("inf")
    best_epoch = 0
    best_model_state: dict[str, torch.Tensor] | None = None
    patience_counter = 0
    stopped_epoch = CONFIG["max_epochs"]
    final_train_loss = 0.0

    for epoch in range(1, CONFIG["max_epochs"] + 1):
        # --- Training Phase ---
        model.train()
        running_train_loss = 0.0
        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)

            optimizer.zero_grad()
            logits = model(batch_x)
            loss = criterion(logits, batch_y)
            loss.backward()
            optimizer.step()

            running_train_loss += loss.item() * batch_x.size(0)

        epoch_train_loss = running_train_loss / len(train_dataset)

        # --- Validation Phase ---
        model.eval()
        running_val_loss = 0.0
        with torch.no_grad():
            for val_x, val_y in val_loader:
                val_x, val_y = val_x.to(device), val_y.to(device)
                logits = model(val_x)
                loss = criterion(logits, val_y)
                running_val_loss += loss.item() * val_x.size(0)

        epoch_val_loss = running_val_loss / len(val_dataset)
        final_train_loss = epoch_train_loss

        # --- Early Stopping Check ---
        status = ""
        if epoch_val_loss < (best_val_loss - CONFIG["min_delta"]):
            best_val_loss = epoch_val_loss
            best_epoch = epoch
            best_model_state = copy.deepcopy(model.state_dict())
            patience_counter = 0
            status = "* Best"
        else:
            patience_counter += 1
            status = f"patience {patience_counter}/{CONFIG['patience']}"

        print(f"  {epoch:6d} | {epoch_train_loss:12.5f} | {epoch_val_loss:12.5f} | {best_val_loss:12.5f} | {status}")

        if patience_counter >= CONFIG["patience"]:
            print(f"\n  Early stopping triggered at epoch {epoch} (no val loss improvement for {CONFIG['patience']} epochs).")
            stopped_epoch = epoch
            break

    assert best_model_state is not None, "Training finished without capturing any model state."

    # 8. Restore best model state and save artifacts
    print(f"\n[7] Restoring best model state from epoch {best_epoch} (val_loss: {best_val_loss:.5f}) ...")
    model.load_state_dict(best_model_state)

    # Save PyTorch state_dict
    torch.save(best_model_state, MODEL_OUT_PATH)
    print(f"  [OK] Model state dict saved to: {MODEL_OUT_PATH}")

    # Save companion config metadata JSON
    companion_metadata = {
        "model_name": CONFIG["model_name"],
        "architecture": "Single-layer GRU -> Dropout -> Linear",
        "input_features": CONFIG["input_features"],
        "hidden_size": CONFIG["hidden_size"],
        "num_layers": CONFIG["num_layers"],
        "num_classes": CONFIG["num_classes"],
        "dropout": CONFIG["dropout"],
        "window_length": CONFIG["window_length"],
        "batch_size": CONFIG["batch_size"],
        "learning_rate": CONFIG["learning_rate"],
        "max_epochs": CONFIG["max_epochs"],
        "patience": CONFIG["patience"],
        "min_delta": CONFIG["min_delta"],
        "stopped_epoch": stopped_epoch,
        "best_epoch": best_epoch,
        "best_val_loss": float(best_val_loss),
        "final_train_loss": float(final_train_loss),
        "class_weights": class_weights_np.tolist(),
        "train_class_counts": train_class_counts,
        "feature_order": feature_order,
        "label_encoding": label_encoding,
        "sequence_counts": {
            "train": int(y_train_seq.shape[0]),
            "val": int(y_val_seq.shape[0]),
            "test": int(y_test_seq.shape[0]),
        },
        "history_boundary_policy": manifest.get("history_boundary_policy", ""),
    }

    CONFIG_OUT_PATH.write_text(json.dumps(companion_metadata, indent=2))
    print(f"  [OK] Companion config saved to:    {CONFIG_OUT_PATH}")

    print("\n" + "=" * 70)
    print("  Phase 18 Complete -- GRU Model Trained & Artifacts Locked")
    print(f"  Best Epoch: {best_epoch} | Best Val Loss: {best_val_loss:.5f}")
    print("=" * 70)


if __name__ == "__main__":
    main()
