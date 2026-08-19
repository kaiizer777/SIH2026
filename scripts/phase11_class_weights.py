#!/usr/bin/env python3
"""
Phase 11 — Class Imbalance Handling Pipeline (Strict Sample Weight Generation)
SIH25071: AI-Based Rockfall Prediction and Alert System

================================================================================
GEOTECHNICAL & MACHINE LEARNING CONTEXT:
--------------------------------------------------------------------------------
This pipeline executes Phase 11 of the SIH25071 ML Baseline roadmap, establishing
the class weight vector using inverse-frequency scaling to handle minority class
imbalance (evacuation/warning phases vs safe phase).

1. CRITICAL METHODOLOGICAL JUSTIFICATION — CLASS WEIGHTING VS SMOTE:
   - Why SMOTE/ADASYN was rejected:
     For open-pit mine geotechnical sensor monitoring, the features (displacement, 
     vibration, pore pressure, strain) are physically correlated by design, following 
     the physical trajectory of the Fukuzono tertiary creep curve.
     SMOTE synthesizes new minority points by linear interpolation in feature space. 
     This interpolation can generate physically implausible sensor readings that 
     violate the laws of rock mechanics and our physics-informed precursor model.
     Class weighting (cost-sensitive loss) reweights the loss function on real 
     observations only. No synthetic or implausible data is added to the training set.

2. MULTICLASS INVARIANT — DO NOT USE scale_pos_weight:
   - XGBoost's `scale_pos_weight` parameter is strictly for binary classification. 
     For a 3-class problem (safe, warning, evacuation), using `scale_pos_weight` will 
     either cause an error or produce incorrect behavior.
     Instead, we compute a sample weight vector that can be passed to the `.fit()` 
     method of both RandomForestClassifier and XGBClassifier.

3. TRAIN-SET ONLY BOUNDARY:
   - Weights must be computed from `data/train.csv` ONLY. Computing them over the 
     entire dataset, or including validation/test splits, leaks class distribution 
     information and violates the strict split boundary established in Phase 10.
================================================================================
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.utils.class_weight import compute_sample_weight

# Ensure stdout handles UTF-8 safely on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Resolve repository root directory and canonical paths
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

# Canonical input and output paths
DEFAULT_TRAIN_CSV = DATA_DIR / "train.csv"
DEFAULT_WEIGHTS_NPY = DATA_DIR / "train_sample_weights.npy"
DEFAULT_METADATA_JSON = DATA_DIR / "weights_metadata.json"

# Invariants
EXPECTED_TRAIN_ROWS: int = 3648  # train_core: 228 days × 16 zones (2025-08-22 → 2026-04-06)
TARGET_CLASSES: List[str] = ["safe", "warning", "evacuation"]


def validate_train_dataset(df: pd.DataFrame, source_path: Path) -> None:
    """
    Validate input train.csv schema, rows, and class balance.
    Fails loudly with descriptive error messages upon any anomaly.
    """
    print(f"[Step 1/4] Validating training dataset '{source_path.name}'...")

    # Check non-empty
    if df.empty:
        raise ValueError(f"FATAL: Training dataset '{source_path}' is completely empty.")

    # Check total rows
    if len(df) != EXPECTED_TRAIN_ROWS:
        print(f"WARNING: Expected exactly {EXPECTED_TRAIN_ROWS} training rows (from Phase 10 split), but found {len(df)}.")

    # Check required columns
    if "risk_level" not in df.columns:
        raise ValueError(
            f"FATAL: Missing required target column 'risk_level' in {source_path.name}."
        )

    # Check null values in target
    null_counts = df["risk_level"].isnull().sum()
    if null_counts > 0:
        raise ValueError(
            f"FATAL: Target column 'risk_level' contains {null_counts} null/NaN values."
        )

    # Check risk_level classes match exactly
    unique_classes = set(df["risk_level"].unique())
    expected_classes = set(TARGET_CLASSES)
    if unique_classes != expected_classes:
        raise ValueError(
            f"FATAL: Unrecognized or missing risk_level classes. Found {unique_classes}, expected exactly {expected_classes}."
        )

    print(f"  [OK] Training dataset schema and classes validated successfully.")


def compute_weights(df: pd.DataFrame) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    Compute balanced class weights on the training dataset.
    """
    print(f"[Step 2/4] Computing sample weights using balanced frequency formula...")

    y_train = df["risk_level"]
    
    # Compute the sample weight vector (balanced)
    sample_weights = compute_sample_weight(class_weight="balanced", y=y_train)

    # Map class names to computed weight per class for verification and logging
    unique_classes = sorted(y_train.unique())
    class_weights_map = {}
    for c in unique_classes:
        # Find first index matching the class to read its computed weight
        idx = y_train[y_train == c].index[0]
        class_weights_map[c] = float(sample_weights[idx])

    return sample_weights, class_weights_map


def verify_and_sanity_check(
    df: pd.DataFrame, 
    sample_weights: np.ndarray, 
    class_weights_map: Dict[str, float]
) -> Dict[str, Any]:
    """
    Perform sanity checks and compute effective weighted class balance.
    """
    print(f"[Step 3/4] Performing sanity checks and calculating effective weighted counts...")

    # Assert length matches exactly
    assert len(sample_weights) == len(df), (
        f"Length of sample weights ({len(sample_weights)}) does not match training row count ({len(df)})."
    )

    y_train = df["risk_level"]
    raw_counts = y_train.value_counts().to_dict()
    raw_pct = (y_train.value_counts(normalize=True) * 100).round(2).to_dict()

    # Calculate effective weighted counts: sum(weights for class c)
    df_weights = pd.DataFrame({"risk_level": y_train, "weight": sample_weights})
    weighted_sums = df_weights.groupby("risk_level")["weight"].sum().to_dict()
    total_weight_sum = sum(weighted_sums.values())
    weighted_pct = {c: round((weighted_sums[c] / total_weight_sum) * 100, 2) for c in TARGET_CLASSES}

    stats = {
        "raw_counts": {c: int(raw_counts.get(c, 0)) for c in TARGET_CLASSES},
        "raw_percentages": {c: float(raw_pct.get(c, 0.0)) for c in TARGET_CLASSES},
        "computed_class_weights": {c: float(class_weights_map[c]) for c in TARGET_CLASSES},
        "effective_weighted_sums": {c: float(weighted_sums.get(c, 0.0)) for c in TARGET_CLASSES},
        "effective_weighted_percentages": {c: float(weighted_pct.get(c, 0.0)) for c in TARGET_CLASSES},
    }

    # Verify that class_weight='balanced' successfully equalizes class weights
    # Sum of weights for class c should be len(y) / n_classes.
    expected_weighted_sum = len(y_train) / len(TARGET_CLASSES)
    for c, w_sum in weighted_sums.items():
        assert np.isclose(w_sum, expected_weighted_sum), (
            f"Class {c} weighted sum {w_sum} deviates from expected balanced sum {expected_weighted_sum}."
        )

    print("  [OK] Sample weight vector length checks out.")
    print("  [OK] Mathematical balance validation passed: all weighted classes have equal effective volume.")
    return stats


def save_artifacts(
    sample_weights: np.ndarray, 
    stats: Dict[str, Any], 
    weights_path: Path, 
    meta_path: Path
) -> None:
    """
    Save sample weights array and metadata JSON to disk.
    """
    print(f"[Step 4/4] Exporting weight vector and metadata to disk...")

    # Save weights as a NumPy binary array (.npy) for fast loading
    np.save(weights_path, sample_weights)
    print(f"  * Saved sample weights array to: {weights_path} ({weights_path.stat().st_size} bytes)")

    # Save metadata JSON
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print(f"  * Saved metadata to: {meta_path}")


def print_formatted_audit(stats: Dict[str, Any]) -> None:
    """
    Print human-readable audit table to terminal.
    """
    print("\n" + "=" * 80)
    print("PHASE 11: CLASS IMBALANCE HANDLING AUDIT SUMMARY")
    print("=" * 80)

    print("\n1. CLASS DISTRIBUTION AND COMPUTED WEIGHTS:")
    print("-" * 80)
    header = f"{'Risk Level':<12} | {'Raw Count':<10} | {'Raw %':<8} | {'Computed Weight':<15} | {'Weighted Sum':<12} | {'Weighted %':<10}"
    print(header)
    print("-" * 80)

    for c in TARGET_CLASSES:
        raw_cnt = stats["raw_counts"][c]
        raw_pct = stats["raw_percentages"][c]
        weight = stats["computed_class_weights"][c]
        w_sum = stats["effective_weighted_sums"][c]
        w_pct = stats["effective_weighted_percentages"][c]
        print(f"{c:<12} | {raw_cnt:<10} | {raw_pct:>6.2f}% | {weight:>15.6f} | {w_sum:>12.2f} | {w_pct:>8.2f}%")
    print("-" * 80)

    print("\n2. PITCH JUSTIFICATION (COPY & PASTE FOR SLIDE DECK):")
    print("-" * 80)
    print("  \"We use class-weighted loss rather than SMOTE because our sensor channels")
    print("   are physically correlated by construction — synthetic interpolation risks")
    print("   generating physically implausible readings. Weighting keeps every training point real.\"")
    print("=" * 80 + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Phase 11: Class Imbalance Handling for SIH25071."
    )
    parser.add_argument(
        "--train-csv",
        type=Path,
        default=DEFAULT_TRAIN_CSV,
        help="Path to input train.csv",
    )
    parser.add_argument(
        "--output-weights",
        type=Path,
        default=DEFAULT_WEIGHTS_NPY,
        help="Path to output train_sample_weights.npy",
    )
    parser.add_argument(
        "--output-metadata",
        type=Path,
        default=DEFAULT_METADATA_JSON,
        help="Path to output weights_metadata.json",
    )

    args = parser.parse_args()
    start_time = time.time()

    print("=" * 80)
    print("SIH25071 ROCKFALL PREDICTION — PHASE 11: CLASS IMBALANCE HANDLING")
    print("=" * 80)

    # Validate train.csv file exists
    if not args.train_csv.exists():
        print(f"FATAL: Training file does not exist at '{args.train_csv}'", file=sys.stderr)
        return 1

    df_train = pd.read_csv(args.train_csv)
    
    # Step 1: Validate train dataset
    validate_train_dataset(df_train, args.train_csv)

    # Step 2: Compute weights
    sample_weights, class_weights_map = compute_weights(df_train)

    # Step 3: Verify and run sanity check
    stats = verify_and_sanity_check(df_train, sample_weights, class_weights_map)

    # Step 4: Save weights and metadata
    args.output_weights.parent.mkdir(parents=True, exist_ok=True)
    save_artifacts(sample_weights, stats, args.output_weights, args.output_metadata)

    # Print summary
    print_formatted_audit(stats)

    elapsed = time.time() - start_time
    print(f"Phase 11 execution completed in {elapsed:.2f}s.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
