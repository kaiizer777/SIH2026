import sys
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
import shap

REPO_ROOT = Path("C:/Users/bari2/Desktop/SIH2026")
sys.path.append(str(REPO_ROOT / "scripts"))
from phase12_baseline_training import load_split, sar_forward_fill, build_features_labels

val_df = load_split(REPO_ROOT / "data/val.csv")
zf = pd.read_csv(REPO_ROOT / "data/zone_features.csv")
val_joined, _ = sar_forward_fill(val_df, zf)
X_val, y_val = build_features_labels(val_joined)

rf = joblib.load(REPO_ROOT / "models/rf-v1-20260820.joblib")
xgb = joblib.load(REPO_ROOT / "models/xgb-v1-20260820.joblib")

for name, model in [("RF", rf), ("XGB", xgb)]:
    explainer = shap.TreeExplainer(model, feature_perturbation='tree_path_dependent', model_output='raw')
    shap_values = explainer.shap_values(X_val)
    print(f"--- {name} ---")
    print(f"Type: {type(shap_values)}")
    if isinstance(shap_values, list):
        print(f"List length: {len(shap_values)}")
        print(f"First element shape: {shap_values[0].shape}")
    else:
        print(f"Shape: {shap_values.shape}")
    
    explanation = explainer(X_val)
    print(f"Explanation.values shape: {explanation.values.shape}")
