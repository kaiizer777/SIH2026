"""
Phase 12 — Baseline Model Training
===================================
Trains RandomForestClassifier and XGBClassifier on the verified train/val/test
splits from Phase 10, using:
  - SAR/terrain features forward-filled from zone_features.csv (sparse 30-date)
  - Sensor features from train/val/test CSVs
  - Sample weights from train_sample_weights.npy (Phase 11)

Run:
    python scripts/phase12_baseline_training.py

Artifacts produced (v2 — terrain-modulated labels, 2026-08-20):
    models/rf-v2-20260820.joblib
    models/xgb-v2-20260820.joblib
    models/feature_order.json
    models/label_encoding.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from xgboost import XGBClassifier

# ---------------------------------------------------------------------------
# Paths (relative to repo root — run from repo root)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
MODELS_DIR = REPO_ROOT / "models"
MODELS_DIR.mkdir(exist_ok=True)

TRAIN_CSV   = DATA_DIR / "train.csv"
VAL_CSV     = DATA_DIR / "val.csv"
TEST_CSV    = DATA_DIR / "test.csv"
ZF_CSV      = DATA_DIR / "zone_features.csv"
WEIGHTS_NPY = DATA_DIR / "train_sample_weights.npy"

LABEL_ENCODING = {"safe": 0, "warning": 1, "evacuation": 2}
LABEL_NAMES    = ["safe", "warning", "evacuation"]

SAR_TERRAIN_FEATURES = ["slope", "aspect", "curvature", "vv_backscatter", "vh_backscatter", "rainfall_mm"]
SENSOR_FEATURES      = ["displacement_mm_day", "vibration", "pore_pressure", "strain"]
FEATURE_ORDER        = SENSOR_FEATURES + SAR_TERRAIN_FEATURES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_split(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["timestamp"])
    return df


def sar_forward_fill(sensor_df: pd.DataFrame, zf: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    original_count = len(sensor_df)
    sensor_df = sensor_df.copy()
    # Normalize to midnight, then strip UTC tz so merge_asof keys match tz-naive SAR dates
    sensor_df["_date"] = (
        sensor_df["timestamp"].dt.normalize().dt.tz_localize(None)
    )

    zf = zf.copy()
    zf["_zf_date"] = pd.to_datetime(zf["date"])  # already tz-naive
    zf = zf.sort_values(["zone_id", "_zf_date"]).reset_index(drop=True)

    # Rename rainfall_mm in zone_features to sar_rainfall before join to avoid collision;
    # it gets renamed back after.
    zf = zf.rename(columns={"rainfall_mm": "_sar_rainfall_mm"})
    sar_cols_left  = ["slope", "aspect", "curvature", "vv_backscatter", "vh_backscatter", "_sar_rainfall_mm"]
    zf_cols = ["zone_id", "_zf_date"] + sar_cols_left

    results = []
    max_staleness = 0

    for zone_id, zone_sensor in sensor_df.groupby("zone_id", sort=False):
        zone_zf = zf.loc[zf["zone_id"] == zone_id, zf_cols].copy()
        zone_sensor = zone_sensor.sort_values("_date")

        merged = pd.merge_asof(
            zone_sensor,
            zone_zf,
            left_on="_date",
            right_on="_zf_date",
            by="zone_id",
            direction="backward",
        )

        staleness = (merged["_date"] - merged["_zf_date"]).dt.days
        zone_max = staleness.max()
        if pd.notna(zone_max):
            max_staleness = max(max_staleness, int(zone_max))

        results.append(merged)

    joined = pd.concat(results, ignore_index=True)

    assert len(joined) == original_count, (
        f"Row count changed after SAR join! Before: {original_count}, After: {len(joined)}"
    )

    # Rename _sar_rainfall_mm -> rainfall_mm (SAR version overwrites sensor version)
    joined = joined.drop(columns=["rainfall_mm"]).rename(
        columns={"_sar_rainfall_mm": "rainfall_mm"}
    )

    print(f"    max forward-fill staleness: {max_staleness} days")
    return joined, max_staleness


def build_features_labels(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    X = df[FEATURE_ORDER].copy()
    y = df["risk_level"].map(LABEL_ENCODING)
    assert y.isna().sum() == 0, "NaN in labels"
    nan_counts = X.isna().sum()
    assert nan_counts.sum() == 0, f"NaN in features:\n{nan_counts[nan_counts > 0]}"
    return X, y


def print_eval(model_name: str, y_true: pd.Series, y_pred: np.ndarray) -> None:
    print(f"\n{'='*60}")
    print(f"  {model_name} — Validation Set")
    print(f"{'='*60}")
    print(classification_report(y_true, y_pred, target_names=LABEL_NAMES, digits=4))
    print("Confusion Matrix (rows=actual, cols=predicted):")
    print(f"  Labels: {LABEL_NAMES}")
    cm = confusion_matrix(y_true, y_pred)
    print(cm)
    report = classification_report(y_true, y_pred, target_names=LABEL_NAMES, output_dict=True)
    evac = report["evacuation"]
    print(f"\n  * evacuation recall:    {evac['recall']:.4f}")
    print(f"  * evacuation precision: {evac['precision']:.4f}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("  Phase 12 - Baseline Model Training")
    print("=" * 60)

    print("\n[1] Loading splits and zone_features ...")
    train_df = load_split(TRAIN_CSV)
    val_df   = load_split(VAL_CSV)
    test_df  = load_split(TEST_CSV)
    zf       = pd.read_csv(ZF_CSV)
    weights  = np.load(str(WEIGHTS_NPY))

    print(f"  train: {len(train_df)} rows | val: {len(val_df)} rows | test: {len(test_df)} rows (held)")
    print(f"  zone_features: {len(zf)} rows | weights: {weights.shape}")

    assert len(weights) == len(train_df), (
        f"Weight vector length {len(weights)} != train rows {len(train_df)}"
    )

    print("\n[2] SAR forward-fill join (per zone, backward) ...")
    print("  train:")
    train_joined, train_staleness = sar_forward_fill(train_df, zf)
    print("  val:")
    val_joined, val_staleness = sar_forward_fill(val_df, zf)

    max_staleness = max(train_staleness, val_staleness)
    print(f"\n  >>> MAX FORWARD-FILL STALENESS: {max_staleness} days <<<")

    assert len(train_joined) == 3648, f"train row count changed: {len(train_joined)}"
    assert len(val_joined)   == 912,  f"val row count changed: {len(val_joined)}"
    print("  Row counts unchanged: 3648 train / 912 val")

    print("\n[3] Building feature matrices ...")
    X_train, y_train = build_features_labels(train_joined)
    X_val,   y_val   = build_features_labels(val_joined)
    print(f"  X_train: {X_train.shape} | X_val: {X_val.shape}")
    print(f"  Feature order: {list(X_train.columns)}")

    print("\n[4] Training RandomForestClassifier (n_estimators=300) ...")
    rf = RandomForestClassifier(
        n_estimators=300,
        max_depth=None,
        random_state=42,
        n_jobs=-1,
    )
    rf.fit(X_train, y_train, sample_weight=weights)
    print("  RF training complete")
    rf_pred = rf.predict(X_val)
    print_eval("RandomForestClassifier", y_val, rf_pred)

    print("\n[5] Training XGBClassifier (n_estimators=300, max_depth=6) ...")
    xgb = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.1,
        objective="multi:softprob",
        num_class=3,
        random_state=42,
        eval_metric="mlogloss",
        verbosity=0,
    )
    xgb.fit(X_train, y_train, sample_weight=weights)
    print("  XGB training complete")
    xgb_pred = xgb.predict(X_val)
    print_eval("XGBClassifier", y_val, xgb_pred)

    print("\n[6] Saving artifacts ...")
    rf_path  = MODELS_DIR / "rf-v2-20260820.joblib"
    xgb_path = MODELS_DIR / "xgb-v2-20260820.joblib"
    fo_path  = MODELS_DIR / "feature_order.json"
    le_path  = MODELS_DIR / "label_encoding.json"

    joblib.dump(rf,  rf_path)
    joblib.dump(xgb, xgb_path)

    with open(fo_path, "w") as f:
        json.dump(FEATURE_ORDER, f, indent=2)
    with open(le_path, "w") as f:
        json.dump(LABEL_ENCODING, f, indent=2)

    for p in [rf_path, xgb_path, fo_path, le_path]:
        assert p.exists(), f"Artifact missing: {p}"
        print(f"  {p}")

    print("\n" + "=" * 60)
    print("  Phase 12 COMPLETE")
    print(f"  Max forward-fill staleness: {max_staleness} days")
    print("=" * 60)


if __name__ == "__main__":
    main()
