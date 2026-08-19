#!/usr/bin/env python3
"""
Phase 13b - v2b Isolation Test: Multiplier-Only SHAP Contribution
SIH25071: AI-Based Rockfall Prediction and Alert System

PURPOSE
-------
Isolate the causal contribution of the terrain susceptibility_multiplier (v2
design) from the concomitant displacement-range widening also introduced in v2.

v2b variant:
  - KEEPS v2 terrain susceptibility_multiplier formula/weights/range [0.70, 1.30] EXACTLY.
  - REVERTS displacement_mm_day GENERATION clip ranges to v1 original hard-clipped values:
      Safe tier:       clip [0.5, 48.5]  mm/day
      Warning tier:    clip [50.5, 119.0] mm/day
      Evacuation tier: clip [120.5, 255.0] mm/day

Question answered:
  Does the multiplier alone produce meaningful crossover cases and terrain/SAR
  SHAP contribution, or does it require range-widening to work?

Hard rules:
  - DOES NOT touch v1 or v2 files, data, or models.
  - All v2b outputs use _v2b / -v2b suffixes.
  - Multiplier formula is identical to v2 phase7_synthetic_sensors.py.

Run:
    python scripts/phase13b_isolation_test.py
"""

from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np
import pandas as pd
import joblib
import shap
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT  = Path(__file__).resolve().parent.parent
DATA_DIR   = REPO_ROOT / "data"
MODELS_DIR = REPO_ROOT / "models"
REPORTS_DIR= REPO_ROOT / "reports"
MODELS_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)

RAINFALL_CSV      = DATA_DIR / "rainfall.csv"
ZONE_FEATURES_CSV = DATA_DIR / "zone_features.csv"
ZONE_GRID_JSON    = DATA_DIR / "zone_grid.json"

SYNTHETIC_V2B = DATA_DIR / "synthetic_sensors_v2b.csv"
TRAIN_V2B     = DATA_DIR / "train_v2b.csv"
VAL_V2B       = DATA_DIR / "val_v2b.csv"
TEST_V2B      = DATA_DIR / "test_v2b.csv"
WEIGHTS_V2B   = DATA_DIR / "train_sample_weights_v2b.npy"

TODAY   = date.today().strftime("%Y%m%d")
RF_V2B  = MODELS_DIR / f"rf-v2b-{TODAY}.joblib"
XGB_V2B = MODELS_DIR / f"xgb-v2b-{TODAY}.joblib"
FO_V2B  = MODELS_DIR / "feature_order_v2b.json"
LE_V2B  = MODELS_DIR / "label_encoding_v2b.json"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SAFE_MAX    = 50.0
WARNING_MAX = 120.0

# v1 ORIGINAL hard-clipped displacement generation ranges (reverted in v2b)
V1_CLIPS = {
    "safe":       (0.5,   48.5),
    "warning":    (50.5, 119.0),
    "evacuation": (120.5, 255.0),
}

TEST_CUTOFF_DATE = "2026-06-03"
VAL_CUTOFF_DATE  = "2026-04-07"

LABEL_ENCODING       = {"safe": 0, "warning": 1, "evacuation": 2}
LABEL_NAMES          = ["safe", "warning", "evacuation"]
SAR_TERRAIN_FEATURES = ["slope", "aspect", "curvature", "vv_backscatter", "vh_backscatter", "rainfall_mm"]
SENSOR_FEATURES      = ["displacement_mm_day", "vibration", "pore_pressure", "strain"]
FEATURE_ORDER        = SENSOR_FEATURES + SAR_TERRAIN_FEATURES
CANONICAL_COLUMNS    = [
    "sensor_id", "zone_id", "timestamp",
    "displacement_mm_day", "vibration", "pore_pressure",
    "strain", "rainfall_mm", "risk_level",
]


def _risk(score: float) -> str:
    if score < SAFE_MAX:
        return "safe"
    elif score <= WARNING_MAX:
        return "warning"
    return "evacuation"


# ===========================================================================
# Step 1 - Load inputs
# ===========================================================================
def load_inputs():
    print("\n[Step 1/8] Loading shared input datasets (read-only)...")
    df_rain = pd.read_csv(RAINFALL_CSV)
    assert list(df_rain.columns) == ["date", "rainfall_mm"]
    print(f"  Rainfall: {len(df_rain)} days")
    df_zf = pd.read_csv(ZONE_FEATURES_CSV)
    print(f"  Zone features: {len(df_zf)} rows, {df_zf['zone_id'].nunique()} zones")
    with open(ZONE_GRID_JSON, "r", encoding="utf-8") as f:
        grid = json.load(f)
    assert len(grid.get("zones", [])) == 16
    return df_rain, df_zf, grid


# ===========================================================================
# Step 2 - Susceptibility multipliers (IDENTICAL to v2 formula)
# ===========================================================================
def compute_multipliers(df_zf: pd.DataFrame):
    print("\n[Step 2/8] Computing susceptibility multipliers (v2 formula, unchanged)...")

    agg = df_zf.groupby("zone_id").agg({
        "slope": "first", "aspect": "first", "curvature": "first",
        "vv_backscatter": "mean", "vh_backscatter": "mean",
    }).reset_index()

    slope_norm = (agg["slope"] - agg["slope"].min()) / (agg["slope"].max() - agg["slope"].min() + 1e-7)
    curv_neg   = -agg["curvature"]
    curv_norm  = (curv_neg - curv_neg.min()) / (curv_neg.max() - curv_neg.min() + 1e-7)
    sar_comb   = (agg["vv_backscatter"] + agg["vh_backscatter"]) / 2.0
    sar_neg    = -sar_comb
    sar_norm   = (sar_neg - sar_neg.min()) / (sar_neg.max() - sar_neg.min() + 1e-7)

    agg["susceptibility_score"] = 0.50 * slope_norm + 0.30 * curv_norm + 0.20 * sar_norm
    agg = agg.sort_values("susceptibility_score", ascending=False).reset_index(drop=True)

    MULT_MIN, MULT_MAX = 0.70, 1.30
    agg["susceptibility_multiplier"] = MULT_MIN + (MULT_MAX - MULT_MIN) * agg["susceptibility_score"]

    zone_risk_map: Dict[str, str] = {}
    zone_scores:   Dict[str, float] = {}
    zone_mults:    Dict[str, float] = {}

    for idx, row in agg.iterrows():
        zid = row["zone_id"]
        zone_scores[zid] = round(float(row["susceptibility_score"]), 4)
        zone_mults[zid]  = round(float(row["susceptibility_multiplier"]), 4)
        zone_risk_map[zid] = "evacuation" if idx < 2 else ("warning" if idx < 6 else "safe")

    print(f"  Multiplier range: min={min(zone_mults.values()):.4f}, max={max(zone_mults.values()):.4f}")
    print(f"  {'Zone':<10} | {'Score':>8} | {'Mult':>6} | {'Tier'}")
    for _, row in agg.iterrows():
        zid = row["zone_id"]
        print(f"  {zid:<10} | {zone_scores[zid]:>8.4f} | {zone_mults[zid]:>6.4f} | {zone_risk_map[zid].upper()}")

    return zone_risk_map, zone_scores, zone_mults


# ===========================================================================
# Step 3 - Generate v2b synthetic data
#          v2 multiplier + v1 hard-clipped displacement ranges
# ===========================================================================
def generate_v2b(df_rain, zone_risk_map, zone_scores, zone_mults, seed=42):
    print("\n[Step 3/8] Generating v2b synthetic sensor data...")
    print("  NOTE: v2 multiplier logic KEPT | v1 hard-clipped displacement ranges REVERTED")
    np.random.seed(seed)

    dates    = df_rain["date"].tolist()
    rainfall = df_rain["rainfall_mm"].values
    n_days   = len(dates)
    zones    = sorted(zone_risk_map.keys())

    api = np.zeros(n_days, dtype=np.float64)
    for t in range(n_days):
        api[t] = rainfall[t] + (0.82 * api[t-1] if t > 0 else 0.0)
    api_norm = (api - api.min()) / (api.max() - api.min() + 1e-7)

    t_peak = 338
    records: List[Dict[str, Any]] = []

    for zone in zones:
        tier  = zone_risk_map[zone]
        mult  = zone_mults[zone]
        v_lo, v_hi = V1_CLIPS[tier]

        if tier == "safe":
            v_base     = float(np.random.uniform(3.0, 18.0))
            v_rain_amp = float(np.random.uniform(8.0, 28.0))
            u_base     = float(np.random.uniform(28.0, 42.0))
            u_gain     = float(np.random.uniform(16.0, 30.0))
            for t in range(n_days):
                u_val = float(np.clip(u_base + u_gain * api_norm[t] + np.random.normal(0, 1.2), 25.0, 75.0))
                v_val = float(np.clip(v_base + v_rain_amp * api_norm[t] + np.random.normal(0, 1.5), v_lo, v_hi))
                strain = float(np.clip(50.0 + 2.2*v_val + 1.0*u_val + np.random.normal(0, 5.0), 50.0, 480.0))
                vib    = float(np.clip(0.010 + 0.055*(v_val/60.0) + np.random.normal(0, 0.004), 0.010, 0.420))
                records.append({"sensor_id": f"SNS-{zone}-01", "zone_id": zone,
                    "timestamp": f"{dates[t]}T00:00:00Z",
                    "displacement_mm_day": round(v_val,2), "vibration": round(vib,3),
                    "pore_pressure": round(u_val,2), "strain": round(strain,2),
                    "rainfall_mm": round(float(rainfall[t]),2), "risk_level": _risk(v_val*mult)})

        elif tier == "warning":
            v_base     = float(np.random.uniform(52.0, 70.0))
            v_rain_amp = float(np.random.uniform(20.0, 45.0))
            u_base     = float(np.random.uniform(55.0, 72.0))
            u_gain     = float(np.random.uniform(42.0, 65.0))
            for t in range(n_days):
                u_val = float(np.clip(u_base + u_gain * api_norm[t] + np.random.normal(0, 1.8), 50.0, 148.0))
                v_val = float(np.clip(v_base + v_rain_amp * api_norm[t] + np.random.normal(0, 2.5), v_lo, v_hi))
                strain = float(np.clip(180.0 + 2.8*v_val + 1.3*u_val + np.random.normal(0, 8.0), 120.0, 850.0))
                vib    = float(np.clip(0.045 + 0.200*(v_val/120.0) + np.random.normal(0, 0.008), 0.020, 0.550))
                records.append({"sensor_id": f"SNS-{zone}-01", "zone_id": zone,
                    "timestamp": f"{dates[t]}T00:00:00Z",
                    "displacement_mm_day": round(v_val,2), "vibration": round(vib,3),
                    "pore_pressure": round(u_val,2), "strain": round(strain,2),
                    "rainfall_mm": round(float(rainfall[t]),2), "risk_level": _risk(v_val*mult)})

        else:  # evacuation
            u_base = float(np.random.uniform(80.0, 95.0))
            u_gain = float(np.random.uniform(100.0, 145.0))
            for t in range(n_days):
                u_val = float(np.clip(u_base + u_gain * api_norm[t] + np.random.normal(0, 2.5), 70.0, 248.0))
                dt_f  = max(1.0, (t_peak + 2) - t)
                fuk   = 25.0 / (dt_f ** 0.25)
                if t < 62 and api_norm[t] < 0.25:
                    raw_v = 125.0 + 30.0*api_norm[t] + fuk + np.random.normal(0, 3.0)
                elif t <= t_peak:
                    raw_v = 135.0 + 60.0*api_norm[t] + fuk + np.random.normal(0, 3.0)
                else:
                    decay = np.exp(-0.05 * (t - t_peak))
                    raw_v = 125.0 + 110.0*decay + np.random.normal(0, 2.5)
                v_val  = float(np.clip(raw_v, v_lo, v_hi))
                strain = float(np.clip(280.0 + 4.0*v_val + 1.7*u_val + np.random.normal(0, 12.0), 200.0, 1580.0))
                vib    = float(np.clip(0.080 + 0.680*((v_val-20.0)/235.0) + np.random.normal(0, 0.012), 0.020, 0.895))
                records.append({"sensor_id": f"SNS-{zone}-01", "zone_id": zone,
                    "timestamp": f"{dates[t]}T00:00:00Z",
                    "displacement_mm_day": round(v_val,2), "vibration": round(vib,3),
                    "pore_pressure": round(u_val,2), "strain": round(strain,2),
                    "rainfall_mm": round(float(rainfall[t]),2), "risk_level": _risk(v_val*mult)})

    df = (pd.DataFrame(records)
          .sort_values(["timestamp","zone_id"])
          .reset_index(drop=True)
          [CANONICAL_COLUMNS])

    assert len(df) == 16 * n_days, f"Row count: {len(df)} != {16*n_days}"
    assert not df.isnull().any().any(), "Null values found"

    print(f"  Generated: {len(df)} rows")
    print("\n  Displacement range per risk_level (label is from risk_score, not raw disp):")
    for rl in ["safe", "warning", "evacuation"]:
        sub = df[df["risk_level"] == rl]
        if len(sub):
            print(f"    {rl.upper():>12}: [{sub['displacement_mm_day'].min():.2f}, "
                  f"{sub['displacement_mm_day'].max():.2f}] mm/day  (n={len(sub)})")
        else:
            print(f"    {rl.upper():>12}: NO ROWS")
    return df


# ===========================================================================
# Step 4 - Crossover pair analysis
# ===========================================================================
def crossover_analysis(df: pd.DataFrame, zone_mults: Dict[str, float]) -> int:
    print("\n[Step 4/8] Crossover pair analysis (same-date, |disp_delta|<=2mm, different class)...")
    df = df.copy()
    df["_date"] = df["timestamp"].str[:10]
    crossover_pairs = []
    for d, day_df in df.groupby("_date"):
        rows = day_df.reset_index(drop=True)
        n = len(rows)
        for i in range(n):
            for j in range(i+1, n):
                ri, rj = rows.iloc[i], rows.iloc[j]
                if (abs(ri["displacement_mm_day"] - rj["displacement_mm_day"]) <= 2.0
                        and ri["risk_level"] != rj["risk_level"]):
                    crossover_pairs.append({
                        "date": d, "zone_a": ri["zone_id"], "disp_a": ri["displacement_mm_day"],
                        "label_a": ri["risk_level"], "mult_a": zone_mults.get(ri["zone_id"]),
                        "zone_b": rj["zone_id"], "disp_b": rj["displacement_mm_day"],
                        "label_b": rj["risk_level"], "mult_b": zone_mults.get(rj["zone_id"]),
                    })

    count = len(crossover_pairs)
    print(f"\n  v2b crossover pairs (|delta|<=2mm, diff label): {count}")
    print(f"  v2  crossover pairs (reference):                 75")
    print(f"  v1  crossover pairs (reference):                  0  (hard-clipped by construction)")

    if count > 0:
        print("\n  First 5 examples:")
        for p in crossover_pairs[:5]:
            rs_a = round(p["disp_a"]*p["mult_a"], 2)
            rs_b = round(p["disp_b"]*p["mult_b"], 2)
            print(f"    {p['date']} | {p['zone_a']} disp={p['disp_a']:.2f} mult={p['mult_a']:.4f} "
                  f"-> score={rs_a} -> {p['label_a'].upper()} | "
                  f"{p['zone_b']} disp={p['disp_b']:.2f} mult={p['mult_b']:.4f} "
                  f"-> score={rs_b} -> {p['label_b'].upper()}")
    else:
        print("\n  RESULT: ZERO crossover pairs found under v1 hard clips + v2 multiplier.")
        print("  [0.70,1.30] multiplier range cannot push displacement across the 50/120 tier")
        print("  boundaries when displacement is hard-clipped away from those boundaries.")
        print("  Range-widening (v2 change B) was LOAD-BEARING, not incidental.")

    return count


# ===========================================================================
# Step 5 - Temporal split
# ===========================================================================
def split_v2b(df: pd.DataFrame):
    print("\n[Step 5/8] Temporal split (same cutoffs as Phase 10)...")
    df = df.copy()
    df["_d"] = pd.to_datetime(df["timestamp"], utc=True).dt.strftime("%Y-%m-%d")
    df_s = df.sort_values(["timestamp","zone_id"]).reset_index(drop=True)

    train_core = df_s[df_s["_d"] <  VAL_CUTOFF_DATE].copy().reset_index(drop=True)
    val        = df_s[(df_s["_d"] >= VAL_CUTOFF_DATE) & (df_s["_d"] < TEST_CUTOFF_DATE)].copy().reset_index(drop=True)
    test       = df_s[df_s["_d"] >= TEST_CUTOFF_DATE].copy().reset_index(drop=True)

    td, vd, ted = set(train_core["_d"]), set(val["_d"]), set(test["_d"])
    print(f"  Train-Val overlap:  {len(td & vd)} (must be 0)")
    print(f"  Val-Test overlap:   {len(vd & ted)} (must be 0)")
    print(f"  Train-Test overlap: {len(td & ted)} (must be 0)")
    assert len(td & vd)  == 0, f"Train-Val leakage: {td & vd}"
    assert len(vd & ted) == 0, f"Val-Test leakage:  {vd & ted}"
    assert len(td & ted) == 0, f"Train-Test leakage:{td & ted}"

    print(f"  Sizes: train={len(train_core)} | val={len(val)} | test={len(test)}")
    for name, sdf in [("train_v2b", train_core), ("val_v2b", val), ("test_v2b", test)]:
        vc = sdf["risk_level"].value_counts(); tot = len(sdf)
        print(f"  {name}: safe={vc.get('safe',0)}({vc.get('safe',0)/tot*100:.1f}%) "
              f"warning={vc.get('warning',0)}({vc.get('warning',0)/tot*100:.1f}%) "
              f"evacuation={vc.get('evacuation',0)}({vc.get('evacuation',0)/tot*100:.1f}%)")

    train_core[CANONICAL_COLUMNS].to_csv(TRAIN_V2B, index=False)
    val[CANONICAL_COLUMNS].to_csv(VAL_V2B, index=False)
    test[CANONICAL_COLUMNS].to_csv(TEST_V2B, index=False)
    print(f"  Saved: {TRAIN_V2B.name}, {VAL_V2B.name}, {TEST_V2B.name}")
    return train_core, val, test


# ===========================================================================
# Step 6 - Class weights
# ===========================================================================
def compute_weights(train_df: pd.DataFrame) -> np.ndarray:
    print("\n[Step 6/8] Computing balanced sample weights (Phase 11 logic)...")
    y = train_df["risk_level"]
    w = compute_sample_weight(class_weight="balanced", y=y)
    vc = y.value_counts()
    print(f"  Train class counts: safe={vc.get('safe',0)} warning={vc.get('warning',0)} evacuation={vc.get('evacuation',0)}")
    np.save(str(WEIGHTS_V2B), w)
    print(f"  Saved: {WEIGHTS_V2B.name}")
    return w


# ===========================================================================
# SAR forward-fill (identical to phase12)
# ===========================================================================
def sar_forward_fill(sensor_df: pd.DataFrame, zf: pd.DataFrame) -> pd.DataFrame:
    orig = len(sensor_df)
    sensor_df = sensor_df.copy()
    sensor_df["_date"] = pd.to_datetime(sensor_df["timestamp"], utc=True).dt.normalize().dt.tz_localize(None)
    zf = zf.copy()
    zf["_zf_date"] = pd.to_datetime(zf["date"])
    zf = zf.sort_values(["zone_id","_zf_date"]).reset_index(drop=True)
    zf = zf.rename(columns={"rainfall_mm": "_sar_rf"})
    sar_cols = ["slope","aspect","curvature","vv_backscatter","vh_backscatter","_sar_rf"]
    results = []
    for zone_id, zs in sensor_df.groupby("zone_id", sort=False):
        zz = zf[zf["zone_id"]==zone_id][["zone_id","_zf_date"]+sar_cols].copy()
        merged = pd.merge_asof(zs.sort_values("_date"), zz, left_on="_date", right_on="_zf_date",
                               by="zone_id", direction="backward")
        results.append(merged)
    joined = pd.concat(results, ignore_index=True)
    assert len(joined) == orig
    joined = joined.drop(columns=["rainfall_mm"]).rename(columns={"_sar_rf": "rainfall_mm"})
    return joined


def build_xy(df: pd.DataFrame):
    X = df[FEATURE_ORDER].copy()
    y = df["risk_level"].map(LABEL_ENCODING)
    assert y.isna().sum() == 0
    assert X.isna().sum().sum() == 0
    return X, y


# ===========================================================================
# Step 7 - Train models
# ===========================================================================
def train_models(train_df, val_df, zf, weights):
    print("\n[Step 7/8] Training RF + XGBoost on v2b data (Phase 12 logic)...")
    tr = sar_forward_fill(train_df, zf)
    vl = sar_forward_fill(val_df, zf)
    X_train, y_train = build_xy(tr)
    X_val,   y_val   = build_xy(vl)
    print(f"  X_train: {X_train.shape} | X_val: {X_val.shape}")
    assert len(weights) == len(X_train)

    print("\n  Training RandomForestClassifier (n_estimators=300)...")
    rf = RandomForestClassifier(n_estimators=300, max_depth=None, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train, sample_weight=weights)
    rf_pred = rf.predict(X_val)
    print("\n  RF - Validation Set:")
    print(classification_report(y_val, rf_pred, target_names=LABEL_NAMES, digits=4))
    print("  Confusion Matrix (rows=actual, cols=predicted):", LABEL_NAMES)
    print(confusion_matrix(y_val, rf_pred))

    print("\n  Training XGBClassifier (n_estimators=300, max_depth=6)...")
    xgb = XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.1,
                        objective="multi:softprob", num_class=3,
                        random_state=42, eval_metric="mlogloss", verbosity=0)
    xgb.fit(X_train, y_train, sample_weight=weights)
    xgb_pred = xgb.predict(X_val)
    print("\n  XGB - Validation Set:")
    print(classification_report(y_val, xgb_pred, target_names=LABEL_NAMES, digits=4))
    print("  Confusion Matrix (rows=actual, cols=predicted):", LABEL_NAMES)
    print(confusion_matrix(y_val, xgb_pred))

    joblib.dump(rf, RF_V2B); joblib.dump(xgb, XGB_V2B)
    with open(FO_V2B,"w") as f: json.dump(FEATURE_ORDER,f,indent=2)
    with open(LE_V2B,"w") as f: json.dump(LABEL_ENCODING,f,indent=2)
    print(f"\n  Saved: {RF_V2B.name}, {XGB_V2B.name}, {FO_V2B.name}, {LE_V2B.name}")
    return rf, xgb, X_val, y_val


# ===========================================================================
# Step 8 - SHAP analysis + three-way comparison
# ===========================================================================
def run_shap(rf, xgb, X_val, y_val):
    print("\n[Step 8/8] SHAP analysis (model_output=raw, evac_idx=2)...")
    evac_idx = LABEL_ENCODING["evacuation"]
    assert evac_idx == 2, f"evacuation index must be 2, got {evac_idx}"
    print(f"  Evacuation class index: {evac_idx}")

    results: Dict[str, float] = {}

    for model_name, model in [("RandomForest", rf), ("XGBoost", xgb)]:
        print(f"\n  --- {model_name} ---")
        expl = shap.TreeExplainer(model, feature_perturbation="tree_path_dependent", model_output="raw")
        sv   = expl.shap_values(X_val)

        # Shape assert BEFORE indexing
        try:
            assert sv.shape == (len(X_val), X_val.shape[1], 3), \
                f"Expected ({len(X_val)}, {X_val.shape[1]}, 3), got {sv.shape}"
            print(f"  Shape assertion PASSED: {sv.shape}")
        except AssertionError as e:
            print(f"  SHAPE ASSERTION FAILED: {e}")
            sys.exit(1)

        sv_evac  = sv[:, :, evac_idx]
        mean_abs = np.abs(sv_evac).mean(axis=0)

        fi = (pd.DataFrame({"Feature": X_val.columns.tolist(), "Mean_Abs_SHAP": mean_abs})
              .sort_values("Mean_Abs_SHAP", ascending=False))
        print(f"\n  Top 10 features ({model_name}, evacuation):")
        print(fi.head(10).to_string(index=False))

        total  = fi["Mean_Abs_SHAP"].sum()
        t_shap = fi[fi["Feature"].isin(SAR_TERRAIN_FEATURES)]["Mean_Abs_SHAP"].sum()
        s_shap = fi[fi["Feature"].isin(SENSOR_FEATURES)]["Mean_Abs_SHAP"].sum()
        t_pct  = (t_shap / total) * 100
        s_pct  = (s_shap / total) * 100

        print(f"\n  {model_name} SHAP Contribution (evacuation):")
        print(f"    Terrain/SAR features (6): {t_pct:.2f}%")
        print(f"    Raw sensor features  (4): {s_pct:.2f}%")

        safe_n = model_name.lower().replace(" ", "")
        ppath  = REPORTS_DIR / f"shap_{safe_n}_v2b_evacuation.png"
        plt.figure(figsize=(10, 6))
        shap.summary_plot(sv_evac, X_val, show=False)
        plt.title(f"v2b SHAP — {model_name} (Evacuation Class)")
        plt.savefig(ppath, bbox_inches="tight", dpi=300)
        plt.close()
        print(f"  Saved: {ppath.name}")

        results[model_name] = t_pct

    return results


# ===========================================================================
# Main
# ===========================================================================
def main():
    t0 = time.time()
    print("=" * 70)
    print("SIH25071 - Phase 13b: v2b Isolation Test (Multiplier-Only Effect)")
    print("=" * 70)

    # Guard: must not accidentally overwrite v2 production files
    v2_protected = [DATA_DIR/"synthetic_sensors.csv", DATA_DIR/"train.csv",
                    DATA_DIR/"val.csv", DATA_DIR/"test.csv",
                    DATA_DIR/"train_sample_weights.npy"]
    for p in v2_protected:
        assert SYNTHETIC_V2B != p, f"Output path collision with v2 file: {p}"

    df_rain, df_zf, grid = load_inputs()
    zone_risk_map, zone_scores, zone_mults = compute_multipliers(df_zf)
    df_v2b = generate_v2b(df_rain, zone_risk_map, zone_scores, zone_mults, seed=42)

    df_v2b.to_csv(SYNTHETIC_V2B, index=False)
    print(f"\n  Saved: {SYNTHETIC_V2B.name} ({SYNTHETIC_V2B.stat().st_size/1024:.1f} KB, {len(df_v2b)} rows)")

    vc    = df_v2b["risk_level"].value_counts()
    total = len(df_v2b)
    print(f"\n  v2b Full Dataset Class Distribution:")
    for cls in ["safe", "warning", "evacuation"]:
        n = vc.get(cls, 0)
        print(f"    {cls.upper():>12}: {n:>4} / {total}  ({n/total*100:.2f}%)")

    n_crossover = crossover_analysis(df_v2b, zone_mults)

    train_df, val_df, test_df = split_v2b(df_v2b)
    weights = compute_weights(train_df)
    zf      = pd.read_csv(ZONE_FEATURES_CSV)
    rf, xgb, X_val, y_val = train_models(train_df, val_df, zf, weights)

    if n_crossover == 0:
        print("\n" + "!" * 70)
        print("  WARNING: Zero crossover pairs found under v1 hard clips + v2 multiplier.")
        print("  Proceeding to SHAP for completeness. Expect near-v1 terrain/SAR contribution.")
        print("!" * 70)

    shap_results = run_shap(rf, xgb, X_val, y_val)

    # -----------------------------------------------------------
    # THREE-WAY COMPARISON TABLE
    # -----------------------------------------------------------
    print("\n" + "=" * 70)
    print("  THREE-WAY TERRAIN/SAR SHAP CONTRIBUTION (evacuation class)")
    print("=" * 70)

    V1_XGB, V1_RF =  0.00, 12.27
    V2_XGB, V2_RF =  6.75, 18.63
    v2b_xgb = shap_results.get("XGBoost",       float("nan"))
    v2b_rf  = shap_results.get("RandomForest",   float("nan"))

    print(f"\n  {'Variant':<35} | {'XGBoost':>10} | {'RandomForest':>13}")
    print(f"  {'-'*35}-+-{'-'*10}-+-{'-'*13}")
    print(f"  {'v1  (hard-clipped ranges, no mult)':<35} | {V1_XGB:>9.2f}% | {V1_RF:>12.2f}%")
    print(f"  {'v2  (widened ranges + mult)':<35} | {V2_XGB:>9.2f}% | {V2_RF:>12.2f}%")
    print(f"  {'v2b (v1 clips + mult only, isolated)':<35} | {v2b_xgb:>9.2f}% | {v2b_rf:>12.2f}%")
    print(f"  {'-'*35}-+-{'-'*10}-+-{'-'*13}")

    print("\n  INTERPRETATION:")
    print(f"  v2b crossover pairs: {n_crossover} (vs v2: 75 / vs v1: 0)")
    if n_crossover == 0:
        print("  The [0.70,1.30] multiplier CANNOT cross the 50/120 mm/day tier")
        print("  boundaries when displacement is hard-clipped to non-overlapping v1 windows.")
        print("  -> Range-widening (v2 change B) was LOAD-BEARING, not incidental.")
        print("  -> Honest pitch: BOTH changes together produce the SHAP delta.")
        print("     The multiplier alone is insufficient without overlapping ranges.")
    elif n_crossover >= 10:
        diff_xgb = abs(v2b_xgb - V2_XGB)
        diff_rf  = abs(v2b_rf  - V2_RF)
        if diff_xgb <= 2.0 and diff_rf <= 2.0:
            print("  v2b SHAP is CLOSE to v2 -> multiplier is doing the real work.")
            print("  -> Range-widening was incidental; pitch can attribute improvement to multiplier.")
        else:
            print("  v2b SHAP is higher than v1 but lower than v2 -> both changes contribute.")
            print("  -> Multiplier meaningful but range-widening amplifies crossover substantially.")
    else:
        print(f"  Marginal crossover ({n_crossover}) -> range-widening was load-bearing.")

    elapsed = time.time() - t0
    print(f"\n[DONE] Phase 13b completed in {elapsed:.1f}s.")
    print("=" * 70)


if __name__ == "__main__":
    main()
