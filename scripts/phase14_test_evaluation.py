#!/usr/bin/env python3
"""
Phase 14 - Test Set Evaluation for v2 Models
SIH25071: AI-Based Rockfall Prediction and Alert System

PURPOSE
-------
Evaluate the final v2 models (RandomForest and XGBoost) on the held-out test
set to confirm metrics and SHAP feature importance percentages out-of-sample.
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
import shap
from sklearn.metrics import classification_report, confusion_matrix

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
MODELS_DIR = REPO_ROOT / "models"
REPORTS_DIR = REPO_ROOT / "reports"

TEST_CSV = DATA_DIR / "test.csv"
ZONE_FEATURES_CSV = DATA_DIR / "zone_features.csv"

# We'll dynamically find the latest v2 models
import glob
rf_models = glob.glob(str(MODELS_DIR / "rf-v2-*.joblib"))
xgb_models = glob.glob(str(MODELS_DIR / "xgb-v2-*.joblib"))
rf_model_path = sorted(rf_models)[-1]
xgb_model_path = sorted(xgb_models)[-1]

FO_JSON = MODELS_DIR / "feature_order.json"
LE_JSON = MODELS_DIR / "label_encoding.json"

def sar_forward_fill(sensor_df: pd.DataFrame, zf: pd.DataFrame) -> pd.DataFrame:
    orig = len(sensor_df)
    sensor_df = sensor_df.copy()
    sensor_df["_date"] = pd.to_datetime(sensor_df["timestamp"], utc=True).dt.normalize().dt.tz_localize(None)
    zf = zf.copy()
    zf["_zf_date"] = pd.to_datetime(zf["date"])
    zf = zf.sort_values(["zone_id", "_zf_date"]).reset_index(drop=True)
    zf = zf.rename(columns={"rainfall_mm": "_sar_rf"})
    sar_cols = ["slope", "aspect", "curvature", "vv_backscatter", "vh_backscatter", "_sar_rf"]
    results = []
    for zone_id, zs in sensor_df.groupby("zone_id", sort=False):
        zz = zf[zf["zone_id"] == zone_id][["zone_id", "_zf_date"] + sar_cols].copy()
        merged = pd.merge_asof(zs.sort_values("_date"), zz,
                               left_on="_date", right_on="_zf_date",
                               by="zone_id", direction="backward")
        results.append(merged)
    joined = pd.concat(results, ignore_index=True)
    assert len(joined) == orig
    joined = joined.drop(columns=["rainfall_mm"]).rename(columns={"_sar_rf": "rainfall_mm"})
    return joined

def main():
    print(f"Loading test data from {TEST_CSV.name}...")
    df_test = pd.read_csv(TEST_CSV)
    df_zf = pd.read_csv(ZONE_FEATURES_CSV)
    
    with open(FO_JSON, "r") as f:
        feature_order = json.load(f)
    with open(LE_JSON, "r") as f:
        label_encoding = json.load(f)
    
    label_names = ["safe", "warning", "evacuation"]
    
    print("Applying SAR forward fill...")
    df_test_filled = sar_forward_fill(df_test, df_zf)
    
    X_test = df_test_filled[feature_order].copy()
    y_test = df_test_filled["risk_level"].map(label_encoding)
    
    print(f"Loading models: {Path(rf_model_path).name}, {Path(xgb_model_path).name}")
    rf = joblib.load(rf_model_path)
    xgb = joblib.load(xgb_model_path)
    
    for name, model in [("RandomForest", rf), ("XGBoost", xgb)]:
        print(f"\\n{'='*50}")
        print(f"Evaluatng {name} on Test Set")
        print(f"{'='*50}")
        
        preds = model.predict(X_test)
        print("\\nClassification Report:")
        print(classification_report(y_test, preds, target_names=label_names, digits=4))
        print("Confusion Matrix:")
        print(confusion_matrix(y_test, preds))
        
        print(f"\\nRunning SHAP for {name} on Test Set (Evacuation class)...")
        expl = shap.TreeExplainer(model, feature_perturbation="tree_path_dependent", model_output="raw")
        sv = expl.shap_values(X_test)
        
        evac_idx = label_encoding["evacuation"]
        sv_evac = sv[:, :, evac_idx]
        mean_abs = np.abs(sv_evac).mean(axis=0)
        
        fi = pd.DataFrame({"Feature": X_test.columns.tolist(), "Mean_Abs_SHAP": mean_abs}).sort_values("Mean_Abs_SHAP", ascending=False)
        print(f"\\nTop 10 Features ({name}):")
        print(fi.head(10).to_string(index=False))
        
        total = fi["Mean_Abs_SHAP"].sum()
        sar_features = ["slope", "aspect", "curvature", "vv_backscatter", "vh_backscatter", "rainfall_mm"]
        sensor_features = ["displacement_mm_day", "vibration", "pore_pressure", "strain"]
        t_shap = fi[fi["Feature"].isin(sar_features)]["Mean_Abs_SHAP"].sum()
        s_shap = fi[fi["Feature"].isin(sensor_features)]["Mean_Abs_SHAP"].sum()
        t_pct = (t_shap / total) * 100 if total > 0 else 0.0
        s_pct = (s_shap / total) * 100 if total > 0 else 0.0
        
        print(f"\\n{name} SHAP Contribution (evacuation):")
        print(f"  Terrain/SAR features: {t_pct:.2f}%")
        print(f"  Raw sensor features:  {s_pct:.2f}%")

if __name__ == "__main__":
    main()
