"""
Phase 13 — SHAP Feature Importance Analysis
===========================================
Computes SHAP feature importances for both the baseline RandomForest and XGBoost
models on the validation set.

Focus:
  - Validates feature ordering and contribution.
  - Specifically analyzes the `evacuation` class (index 2).
  - Evaluates the impact of terrain/SAR features vs raw sensor features.

Run:
    python scripts/phase13_shap_analysis.py

Artifacts produced:
    reports/shap_rf_evacuation.png
    reports/shap_xgb_evacuation.png
"""

import os
import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
import shap
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Paths and Constants
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT / "scripts"))

from phase12_baseline_training import load_split, sar_forward_fill, build_features_labels

DATA_DIR = REPO_ROOT / "data"
MODELS_DIR = REPO_ROOT / "models"
REPORTS_DIR = REPO_ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

VAL_CSV = DATA_DIR / "val.csv"
ZF_CSV = DATA_DIR / "zone_features.csv"

RF_MODEL_PATH = MODELS_DIR / "rf-v2-20260820.joblib"
XGB_MODEL_PATH = MODELS_DIR / "xgb-v2-20260820.joblib"
LABEL_ENCODING_PATH = MODELS_DIR / "label_encoding.json"

SAR_TERRAIN_FEATURES = ["slope", "aspect", "curvature", "vv_backscatter", "vh_backscatter", "rainfall_mm"]
SENSOR_FEATURES = ["displacement_mm_day", "vibration", "pore_pressure", "strain"]

def main():
    print("=" * 60)
    print("  Phase 13 - SHAP Analysis")
    print("=" * 60)

    # 1. Load label encoding and verify evacuation index
    with open(LABEL_ENCODING_PATH, "r") as f:
        label_encoding = json.load(f)
    evac_idx = label_encoding["evacuation"]
    print(f"Evacuation class index: {evac_idx}")
    
    # 2. Reconstruct X_val using exact SAR forward-fill join logic
    print("\n[1] Loading and joining validation data...")
    val_df = load_split(VAL_CSV)
    zf = pd.read_csv(ZF_CSV)
    val_joined, val_staleness = sar_forward_fill(val_df, zf)
    X_val, y_val = build_features_labels(val_joined)
    print(f"X_val shape: {X_val.shape}")
    
    # 3. Load Models
    print("\n[2] Loading models...")
    models = {
        "RandomForest": joblib.load(RF_MODEL_PATH),
        "XGBoost": joblib.load(XGB_MODEL_PATH)
    }
    
    # 4. Compute SHAP for both models
    print("\n[3] Computing SHAP values...")
    
    results = {}
    
    for model_name, model in models.items():
        print(f"\n--- Analyzing {model_name} ---")
        try:
            explainer = shap.TreeExplainer(model, feature_perturbation='tree_path_dependent', model_output='raw')
            shap_values = explainer.shap_values(X_val)
            
            # Assert Shape (N, F, 3)
            try:
                assert shap_values.shape == (len(X_val), X_val.shape[1], 3)
                print(f"Shape assertion passed: {shap_values.shape}")
            except AssertionError:
                print(f"SHAPE ASSERTION FAILED for {model_name}! Actual shape: {shap_values.shape if hasattr(shap_values, 'shape') else type(shap_values)}")
                sys.exit(1)
            
            # Index evacuation class
            shap_values_evac = shap_values[:, :, evac_idx]
            
            # Feature Importance (Mean Absolute SHAP)
            mean_abs_shap = np.abs(shap_values_evac).mean(axis=0)
            feature_names = X_val.columns.tolist()
            
            # Rank top 10 features
            feature_importance = pd.DataFrame({
                "Feature": feature_names,
                "Mean_Abs_SHAP": mean_abs_shap
            }).sort_values(by="Mean_Abs_SHAP", ascending=False)
            
            print(f"\nTop 10 Features for {model_name} (Evacuation Class):")
            print(feature_importance.head(10).to_string(index=False))
            
            # Terrain/SAR contribution check
            total_shap = feature_importance["Mean_Abs_SHAP"].sum()
            terrain_sar_shap = feature_importance[feature_importance["Feature"].isin(SAR_TERRAIN_FEATURES)]["Mean_Abs_SHAP"].sum()
            sensor_shap = feature_importance[feature_importance["Feature"].isin(SENSOR_FEATURES)]["Mean_Abs_SHAP"].sum()
            
            terrain_pct = (terrain_sar_shap / total_shap) * 100
            sensor_pct = (sensor_shap / total_shap) * 100
            
            print(f"\n{model_name} Contribution Breakdown (Evacuation Class):")
            print(f"  Terrain/SAR features (6): {terrain_pct:.2f}%")
            print(f"  Raw sensor features (4):  {sensor_pct:.2f}%")
            
            # Generate Summary Plot
            plt.figure(figsize=(10, 6))
            shap.summary_plot(shap_values_evac, X_val, show=False)
            plot_path = REPORTS_DIR / f"shap_{model_name.lower()}_evacuation.png"
            plt.savefig(plot_path, bbox_inches='tight', dpi=300)
            plt.close()
            print(f"Saved summary plot to: {plot_path}")
            
            results[model_name] = {
                "shape": shap_values.shape,
                "top_10": feature_importance.head(10),
                "terrain_pct": terrain_pct,
                "sensor_pct": sensor_pct,
                "plot_path": plot_path
            }
            
        except Exception as e:
            print(f"Failed to compute SHAP for {model_name}: {e}")
            raise
    
    print("\n" + "=" * 60)
    print("  Phase 13 COMPLETE")
    print("=" * 60)
    
if __name__ == "__main__":
    main()
