"""
Phase 19 -- GRU Test-Set Evaluation
=====================================
SIH25071: AI-Based Rockfall Prediction and Alert System

PURPOSE
-------
First and only time test_sequences.npz is opened in the GRU pipeline.
- Phase 17 built it.
- Phase 18 never touched it (held out strictly for early stopping via val only).
- This script opens it NOW for the first time.

Evaluation mirrors Phase 13/14's rubric exactly:
  - classification_report with per-class precision/recall/F1
  - Evacuation class headlined (not accuracy)
  - Raw confusion matrix counts with evacuation row/column called out explicitly
  - Honest val-loss vs test-performance comparison with explicit flagging

SHAP NOTE (decision point -- not implemented here):
  TreeExplainer (used in Phase 13/14) does not apply to a GRU.
  Options: shap.DeepExplainer or shap.GradientExplainer, but both require
  a separate scoping decision (background dataset for DeepExplainer,
  gradient graph compatibility for GradientExplainer). This is NOT a silent
  omission -- see printed flag below and WORK.md comparison table cell.

Run from repo root:
    python scripts/phase19_gru_evaluation.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless backend for server/CI environments
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.metrics import precision_recall_fscore_support

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
SEQUENCES_DIR = REPO_ROOT / "data" / "sequences"
MODELS_DIR = REPO_ROOT / "models"
REPORTS_DIR = REPO_ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

MODEL_PT    = MODELS_DIR / "gru-v1-20260821.pt"
CONFIG_JSON = MODELS_DIR / "gru-v1-20260821_config.json"
TEST_NPZ    = SEQUENCES_DIR / "test_sequences.npz"
CM_PLOT_OUT = REPORTS_DIR / "confusion_matrix_gru_test.png"

TARGET_NAMES = ["safe", "warning", "evacuation"]

# Val-loss reference locked from Phase 18 (best epoch 19, patience 8)
PHASE18_BEST_VAL_LOSS = 0.0321609786366472

# Known test-class counts from Phase 17 (for sanity check)
EXPECTED_TEST_N = 1136
EXPECTED_EVAC_N = 197   # evacuation samples in test split

# RF/XGBoost evacuation F1 baseline (Phase 13/14) for comparison flagging
RF_XGB_EVAC_F1_BASELINE = 0.99


# ---------------------------------------------------------------------------
# GRUClassifier — identical to Phase 18, params read from config (not hardcoded)
# ---------------------------------------------------------------------------
class GRUClassifier(nn.Module):
    """
    Single-layer GRU sequence-to-one classifier.
    Architecture params are sourced from config JSON so this file cannot
    silently drift from the model that was actually trained in Phase 18.
    """

    def __init__(
        self,
        input_size: int,
        hidden_size: int,
        num_classes: int,
        dropout: float,
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

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        _, h_n = self.gru(x)
        final_hidden = h_n[-1]          # (batch, hidden_size)
        dropped = self.dropout(final_hidden)
        return self.fc(dropped)         # raw logits (batch, num_classes)


# ---------------------------------------------------------------------------
# Confusion matrix plot — same visual style as Phase 13's SHAP reports
# (Blues colormap, 300 dpi, tight layout, white annotation on dark cells)
# ---------------------------------------------------------------------------
def plot_confusion_matrix(
    cm: np.ndarray,
    class_names: list[str],
    out_path: Path,
    title: str = "GRU Test-Set Confusion Matrix",
) -> None:
    fig, ax = plt.subplots(figsize=(7, 6))
    im = ax.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    ax.set(
        xticks=np.arange(len(class_names)),
        yticks=np.arange(len(class_names)),
        xticklabels=class_names,
        yticklabels=class_names,
        xlabel="Predicted label",
        ylabel="True label",
        title=title,
    )
    ax.tick_params(axis="x", labelrotation=45)

    thresh = cm.max() / 2.0
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(
                j, i, str(cm[i, j]),
                ha="center", va="center",
                color="white" if cm[i, j] > thresh else "black",
                fontsize=13, fontweight="bold",
            )

    fig.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"\nConfusion matrix plot saved -> {out_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    print("=" * 70)
    print("  Phase 19 -- GRU Test-Set Evaluation")
    print("=" * 70)

    # ------------------------------------------------------------------
    # 1. Load config from Phase 18 — architecture params come from here,
    #    NOT hardcoded, so this script cannot silently drift from what
    #    was actually trained.
    # ------------------------------------------------------------------
    print(f"\n[1] Loading model config from {CONFIG_JSON.name} ...")
    with open(CONFIG_JSON, "r") as f:
        cfg = json.load(f)

    hidden_size   = cfg["hidden_size"]     # 64
    dropout       = cfg["dropout"]         # 0.2
    input_size    = cfg["input_features"]  # 10
    num_classes   = cfg["num_classes"]     # 3
    best_val_loss = cfg["best_val_loss"]   # 0.03216...
    best_epoch    = cfg["best_epoch"]      # 19
    stopped_epoch = cfg["stopped_epoch"]   # 27

    print(f"  Architecture : {cfg['architecture']}")
    print(f"  hidden_size  : {hidden_size}")
    print(f"  dropout      : {dropout}")
    print(f"  input_size   : {input_size}")
    print(f"  best_val_loss: {best_val_loss:.8f}  (epoch {best_epoch}, stopped epoch {stopped_epoch})")
    print(f"  class_weights: {cfg['class_weights']}")

    # Cross-check the locked val-loss constant in this script matches the JSON
    assert abs(best_val_loss - PHASE18_BEST_VAL_LOSS) < 1e-10, (
        f"Val-loss mismatch: JSON={best_val_loss}, script constant={PHASE18_BEST_VAL_LOSS}"
    )

    # ------------------------------------------------------------------
    # 2. Load model weights
    # ------------------------------------------------------------------
    print(f"\n[2] Loading model weights from {MODEL_PT.name} ...")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"  Device: {device}")

    model = GRUClassifier(
        input_size=input_size,
        hidden_size=hidden_size,
        num_classes=num_classes,
        dropout=dropout,
    )
    model.load_state_dict(torch.load(MODEL_PT, map_location=device, weights_only=True))
    model.to(device)
    model.eval()
    print("  Model loaded and set to eval() mode.")

    # ------------------------------------------------------------------
    # 3. Load test sequences — FIRST TIME THIS FILE IS OPENED.
    #    Phase 17 built it. Phase 18 never opened it (only train+val).
    #    This is the true held-out evaluation.
    # ------------------------------------------------------------------
    print(f"\n[3] Loading test sequences from {TEST_NPZ.name} ...")
    print("  *** FIRST TIME test_sequences.npz is opened in the GRU pipeline ***")
    print("  (Phase 17 built it; Phase 18 strictly held it out; Phase 19 opens it now.)")

    npz = np.load(TEST_NPZ)
    X_test = npz["X"].astype(np.float32)   # (1136, 14, 10)
    y_test = npz["y"].astype(np.int64)     # (1136,)

    assert X_test.shape == (EXPECTED_TEST_N, 14, 10), (
        f"Unexpected X_test shape: {X_test.shape}"
    )
    assert y_test.shape == (EXPECTED_TEST_N,), (
        f"Unexpected y_test shape: {y_test.shape}"
    )

    evac_actual_n = int((y_test == 2).sum())
    assert evac_actual_n == EXPECTED_EVAC_N, (
        f"Evacuation sample count mismatch: expected {EXPECTED_EVAC_N}, got {evac_actual_n}"
    )

    print(f"  X_test shape : {X_test.shape}")
    print(f"  y_test shape : {y_test.shape}")
    print(f"  Class counts -> safe: {(y_test==0).sum()}, warning: {(y_test==1).sum()}, evacuation: {(y_test==2).sum()}")

    # ------------------------------------------------------------------
    # 4. Run inference
    # ------------------------------------------------------------------
    print("\n[4] Running inference (eval mode, no_grad) ...")
    X_tensor = torch.tensor(X_test, device=device)

    with torch.no_grad():
        logits = model(X_tensor)                       # (1136, 3)
        probs  = torch.softmax(logits, dim=1)          # (1136, 3) — for confidence inspection
        y_pred_tensor = logits.argmax(dim=1)

    y_pred   = y_pred_tensor.cpu().numpy()
    probs_np = probs.cpu().numpy()
    print(f"  Logits shape : {logits.shape}")
    print(f"  Probs shape  : {probs_np.shape}  (softmax, stored but not used for classification_report)")
    print(f"  Predictions  -> safe: {(y_pred==0).sum()}, warning: {(y_pred==1).sum()}, evacuation: {(y_pred==2).sum()}")

    # ------------------------------------------------------------------
    # 5. Classification report — identical params to Phase 13/14
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  CLASSIFICATION REPORT (apples-to-apples with Phase 13/14 RF/XGBoost)")
    print("=" * 70)
    report = classification_report(
        y_test, y_pred,
        target_names=TARGET_NAMES,
        digits=4,
    )
    print(report)

    # ------------------------------------------------------------------
    # 6. Confusion matrix — raw counts, evacuation row/column explicit
    # ------------------------------------------------------------------
    print("=" * 70)
    print("  CONFUSION MATRIX (raw counts)")
    print("=" * 70)
    cm = confusion_matrix(y_test, y_pred)
    print(f"\n  Labels (rows=true, cols=predicted): {TARGET_NAMES}")
    print(f"\n{cm}\n")

    # Evacuation row (index 2)
    evac_true_total = int(cm[2, :].sum())       # should == 197
    evac_correct    = int(cm[2, 2])             # true positive
    evac_missed     = evac_true_total - evac_correct
    evac_as_safe    = int(cm[2, 0])
    evac_as_warning = int(cm[2, 1])

    # Evacuation column (index 2) — false alarms from other classes
    evac_col_total  = int(cm[:, 2].sum())
    evac_fp         = evac_col_total - evac_correct  # other classes predicted as evacuation

    print(f"  Evacuation correctly identified   : {evac_correct} / {evac_true_total}")
    print(f"  Evacuation missed (-> safe)        : {evac_as_safe}")
    print(f"  Evacuation missed (-> warning)     : {evac_as_warning}")
    print(f"  Total evacuation missed            : {evac_missed}")
    print(f"  False evacuation alarms (FP)       : {evac_fp}  (other classes predicted as evacuation)")

    # ------------------------------------------------------------------
    # 7. Headline metrics for the pitch (per Phase 13's rubric)
    # ------------------------------------------------------------------
    prec, rec, f1, support = precision_recall_fscore_support(
        y_test, y_pred, labels=[0, 1, 2], zero_division=0
    )
    overall_acc = float((y_pred == y_test).sum()) / len(y_test)

    print("\n" + "=" * 70)
    print("  EVACUATION-CLASS HEADLINE METRICS  (primary pitch numbers)")
    print("=" * 70)
    print(f"  Evacuation Precision : {prec[2]:.4f}")
    print(f"  Evacuation Recall    : {rec[2]:.4f}")
    print(f"  Evacuation F1        : {f1[2]:.4f}")
    print(f"\n  Overall Accuracy     : {overall_acc:.4f}  (not the headline -- per Phase 13 rubric)")

    # ------------------------------------------------------------------
    # 8. Val-loss vs test-performance comparison & overfitting flag
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  VAL-LOSS vs TEST-PERFORMANCE COMPARISON")
    print("=" * 70)
    print(f"  Phase 18 best val loss : {PHASE18_BEST_VAL_LOSS:.8f}  (epoch {best_epoch})")
    print(f"  Test overall accuracy  : {overall_acc:.4f}")
    print(f"  Test evacuation F1     : {f1[2]:.4f}")
    print(f"  Test evacuation Recall : {rec[2]:.4f}")
    print(f"  Test evacuation Prec   : {prec[2]:.4f}")
    print()

    FLAG = False

    if f1[2] < RF_XGB_EVAC_F1_BASELINE - 0.05:
        FLAG = True
        print("  [FLAG] GRU evacuation F1 is noticeably below RF/XGBoost baseline (0.99).")
        print(f"         GRU={f1[2]:.4f} vs baseline={RF_XGB_EVAC_F1_BASELINE:.2f}.")
        print("         This is expected on clean synthetic data (tree models already")
        print("         capture the physical signal perfectly). Per WORK.md Phase 19:")
        print("         do NOT manufacture a win -- report honestly.")
        print()

    if rec[2] < 0.90:
        FLAG = True
        print(f"  [FLAG] GRU evacuation recall {rec[2]:.4f} < 0.90 -- meaningful miss rate.")
        print("         The model is leaving real evacuations undetected at a non-trivial rate.")
        print()

    if overall_acc < 0.80:
        FLAG = True
        print(f"  [FLAG] Overall test accuracy {overall_acc:.4f} < 0.80 despite")
        print(f"         val_loss={PHASE18_BEST_VAL_LOSS:.4f}.")
        print("         Val-to-test generalization gap may indicate overfitting or")
        print("         distribution shift on this synthetic dataset.")
        print()

    if not FLAG:
        print("  [OK] No major val-to-test gap flagged. Test performance is consistent")
        print("       with val-loss trajectory from Phase 18.")
        print()

    # ------------------------------------------------------------------
    # 9. SHAP — explicit decision-point flag (NOT implemented)
    # ------------------------------------------------------------------
    print("=" * 70)
    print("  SHAP STATUS -- DECISION POINT (not implemented in Phase 19)")
    print("=" * 70)
    print("  TreeExplainer (Phase 13/14) does NOT apply to a GRU.")
    print("  Gradient-based alternatives require separate scoping:")
    print("    - shap.DeepExplainer  : needs representative background dataset,")
    print("                           PyTorch-version compatibility constraints.")
    print("    - shap.GradientExplainer: requires gradient graph compatibility,")
    print("                            can be brittle with GRU's unrolled graph.")
    print()
    print("  WORK.md Phase 19 does NOT scope SHAP as a prerequisite to close Phase 19.")
    print("  Terrain/SAR SHAP cell in comparison table will be set to:")
    print("    'N/A -- GRU SHAP not computed (DeepExplainer/GradientExplainer scope")
    print("     not included in Phase 19 -- separate decision point required)'")
    print()
    print("  ACTION REQUIRED (user decision):")
    print("  Should Phase 20+ include a shap.DeepExplainer pass for the GRU?")
    print("  RF/XGBoost SHAP (Phase 13/14) already covers the pitch story fully.")

    # ------------------------------------------------------------------
    # Save confusion matrix plot — Blues colormap, 300 dpi, tight layout
    # ------------------------------------------------------------------
    print("\n[6] Generating confusion matrix plot ...")
    plot_confusion_matrix(cm, TARGET_NAMES, CM_PLOT_OUT)

    # ------------------------------------------------------------------
    # Summary banner
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("  PHASE 19 SUMMARY")
    print("=" * 70)
    print(f"  Test sequences evaluated : {len(y_test)}")
    print(f"  Evacuation samples (true): {evac_true_total}")
    print(f"  Evacuation correctly ID'd: {evac_correct}")
    print(f"  Evacuation missed        : {evac_missed}")
    print()
    print(f"  Evacuation Precision : {prec[2]:.4f}")
    print(f"  Evacuation Recall    : {rec[2]:.4f}")
    print(f"  Evacuation F1        : {f1[2]:.4f}")
    print(f"  Overall Accuracy     : {overall_acc:.4f}")
    print()
    print(f"  CM plot              : {CM_PLOT_OUT}")
    print()
    print("  SHAP                 : N/A -- decision point (see above)")
    print()
    print("  NOTE: WORK.md checklist items and comparison table will NOT be")
    print("  updated until user confirms these numbers. (Per Phase 19 protocol.)")
    print("=" * 70)


if __name__ == "__main__":
    main()
