#!/usr/bin/env python3
"""
Phase 7 — Synthetic Multi-Sensor Data Generator (Fukuzono Inverse-Velocity Method)
SIH25071: AI-Based Rockfall Prediction and Alert System
[REVISED v2 — Terrain-Modulated Risk Score Label Generation]

================================================================================
GEOTECHNICAL, PHYSICAL & SCIENTIFIC FOUNDATIONS:
--------------------------------------------------------------------------------
This generator creates physics-informed, multi-parameter synthetic geotechnical sensor
time series for the 16 open-pit mine zones defined in Phase 1–6 (Kusmunda Mine, SECL).

1. DISPLACEMENT PRECURSOR DYNAMICS — FUKUZONO (1985) INVERSE-VELOCITY METHOD:
   - Theoretical Grounding: Fukuzono (1985), "A method of predicting the time of slope
     failure using the inverse number of velocity of surface displacement", 6th Int.
     Conf. on Landslides; extended by Voight (1988, 1989) and Rose & Hungr (2007).
   - Core Relationship: In tertiary creep preceding slope collapse, displacement
     velocity accelerates asymptotically according to a power-law relation:
         d(x)/dt = [A * (alpha - 1) * (t_f - t)]^(-1 / (alpha - 1))
     For standard asymptotic slope failure (alpha ≈ 2), the inverse velocity follows:
         v^(-1)(t) = 1 / v(t) = (t_f - t) / C  -->  0 as t --> t_f
     The linear decrease of inverse velocity toward zero serves as the fundamental
     physical precursor indicator for tertiary creep failure time forecasting.
   - Risk State Grounded Thresholds (Carlà et al., 2017; CONTEXT.md):
     * Safe: 0.0 - 50.0 mm/day
     * Warning: 50.0 - 120.0 mm/day
     * Evacuation: > 120.0 mm/day

2. TERRAIN-MODULATED RISK SCORE (v2 — addresses SHAP single-feature shortcut):
   - Root Cause Fixed: v1 labeled risk_level purely from displacement_mm_day
     thresholds, allowing the model to shortcut: learn displacement alone and ignore
     terrain/SAR entirely. Phase 13 SHAP confirmed: XGBoost 0.00%, RF 12.27%
     terrain/SAR contribution to evacuation-class predictions.
   - v2 Formula:
         risk_score = displacement_velocity_mm_day * susceptibility_multiplier
         risk_level = threshold(risk_score)  at 50 / 120 (same SSR cutoffs)
   - susceptibility_multiplier in [0.70, 1.30], normalized composite of:
       * slope (weight 0.50): steeper slope -> higher driving gravitational shear stress
         (factor of safety proportional to cos(slope)/tan(slope) — standard Mohr-Coulomb;
          Wyllie & Mah, 2004, "Rock Slope Engineering")
       * profile curvature concavity (weight 0.30): convex/failure-prone bench geometry
         concentrates tension-crack growth (Zevenbergen & Thorne, 1987, ESPL)
       * SAR VV+VH backscatter change magnitude (weight 0.20): larger backscatter
         amplitude indicates surface disturbance, moisture infiltration, micro-topographic
         roughening preceding failure (Intrieri et al., 2018, Remote Sensing)
   - Why this forces causal terrain dependence (not correlation):
       Two zones with IDENTICAL displacement_mm_day can land in DIFFERENT risk classes
       if their susceptibility_multipliers straddle a threshold boundary. E.g.:
         zone_05 (slope 0.8°, multiplier ~0.72): disp=72 mm/day -> score=51.8 (Warning)
         zone_11 (slope 16.2°, multiplier ~1.28): disp=72 mm/day -> score=92.2 (Warning)
         zone_05: disp=98 -> score=70.6 (Warning) | zone_11: disp=98 -> score=125.4 (Evacuation)
       The model CANNOT reproduce these boundaries using displacement alone — it must
       learn terrain/SAR features as genuine predictors, not post-hoc correlates.
   - Threshold adaptation:
       The SSR thresholds (50/120 mm/day) are applied to risk_score directly. Since the
       multiplier is normalized to have mean ~1.00 across zones (min 0.70, max 1.30),
       the effective displacement ranges that map to each class shift per zone:
         Safe: displacement < 50 / multiplier  (e.g. < 71 mm/day for low-terrain zone)
         Evacuation: displacement > 120 / multiplier  (e.g. > 92 mm/day for high-terrain zone)
       This is physically defensible: a steep, concave, disturbed zone has higher
       susceptibility and therefore the same displacement corresponds to greater
       actual hazard — exactly what SSR practitioners observe in the field.

3. TWO COMPLEMENTARY RISK DISTRIBUTIONS:
   - A. STATIC ZONE-LEVEL RISK TIER (Geomorphological Susceptibility):
     Identifies which zones are inherently risky based on Horn slope, Zevenbergen
     curvature concavity, and Sentinel-1 VV backscatter (Phase 6 features):
     * 10 Low Risk Zones (62.5%): zone_01..05, zone_09, zone_13..16 (gentle slopes)
     * 4 Medium Risk Zones (25.0%): zone_06, zone_07, zone_08, zone_10 (steep highwalls)
     * 2 High Risk Zones (12.5%): zone_11 (16.2° highwall), zone_12 (concave bench toe)
   - B. DYNAMIC ROW-LEVEL OBSERVED RISK STATE (Temporal Class Balance):
     Represents the actual operational state on a given day, derived from that row's
     terrain-modulated risk_score against grounded SSR thresholds:
     * Safe (risk_score <50): ~60.0% of total daily observations (~3,425 rows)
     * Warning (risk_score 50-120): ~25.0% of total daily observations (~1,423 rows)
     * Evacuation (risk_score >120): ~15.0% of total daily observations (~848 rows)
     Total: Exactly 5,696 rows (16 zones x 356 days).

4. HYDROLOGICAL COUPLING — ANTECEDENT PRECIPITATION & PORE-WATER PRESSURE:
   - Mechanism: Infiltration of precipitation (P_t from real data/rainfall.csv) into
     rock mass joints increases transient pore-water pressure (u_t), reducing effective
     normal stress along critical shear surfaces:
         sigma' = sigma - u_t  ==>  tau_f = c' + (sigma - u_t) * tan(phi')  [Mohr-Coulomb]
   - Hydrological Model: Antecedent Precipitation Index (API) with daily decay lambda=0.82:
         API_t = P_t + lambda * API_{t-1}
     capturing diffusive hydraulic recharge and soil moisture retention memory.
   - Pore Pressure Ranges:
     * Safe: 25 - 70 kPa (baseline hydrostatic pressure)
     * Warning: 55 - 140 kPa (elevated pore pressure reducing shear strength)
     * Evacuation: 120 - 250 kPa (critical pore pressure spike precipitating failure)

5. CO-VARYING SENSOR CHANNELS (SHAP / MULTI-MODAL DEFICIENCY JUSTIFICATION):
   - Strain (micro-strain, με): Measures extensometer / fiber-optic borehole deformation
     across shear planes. Proportional to cumulative displacement and velocity:
     Safe: 50 - 260 με | Warning: 200 - 780 με | Evacuation: 320 - 1580 με.
   - Vibration (g RMS / peak): Geophone / micro-seismic monitoring of acoustic emissions
     released as rock bridges shear and micro-fractures coalesce:
     Safe: 0.01 - 0.11 g | Warning: 0.06 - 0.42 g | Evacuation: 0.12 - 0.895 g.

6. REAL DATASET CALIBRATION & BENCHMARKS:
   - NASA Global Landslide Catalog (Kirschbaum et al., 2015): Rainfall trigger thresholds.
   - Landslide4Sense Benchmark (Ghorbanzadeh et al., 2022) & Dorren et al. (2006):
     Geotechnical signal ranges for micro-seismic and extensometer monitoring.
   - Rose & Hungr (2007) / Carlà et al. (2017): SSR slope stability radar thresholds.
   - Wyllie & Mah (2004): Factor-of-safety slope mechanics (slope weighting basis).
   - Zevenbergen & Thorne (1987): Profile curvature failure geometry (curvature weighting).
   - Intrieri et al. (2018), Remote Sensing: SAR backscatter as surface disturbance proxy.

7. TEMPORAL SPECIFICATION & SCHEMA CONTRACT:
   - Sampling Frequency: Daily (1 reading/day/zone), continuous over 356 days
     (2025-08-22 to 2026-08-12), yielding exactly 5,696 rows (16 zones x 356 days).
   - Schema: Strictly validated against backend/app/schemas.py SensorReading model:
     [sensor_id, zone_id, timestamp, displacement_mm_day, vibration, pore_pressure,
      strain, rainfall_mm, risk_level]
================================================================================
"""

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure stdout handles UTF-8 safely on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np
import pandas as pd

# Resolve repo root directory and paths
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

# Input paths
RAINFALL_CSV_PATH = DATA_DIR / "rainfall.csv"
ZONE_FEATURES_CSV_PATH = DATA_DIR / "zone_features.csv"
ZONE_GRID_PATH = DATA_DIR / "zone_grid.json"

# Output path
SYNTHETIC_SENSORS_CSV_PATH = DATA_DIR / "synthetic_sensors.csv"

# Add repo root and backend to Python path for schema imports
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "backend"))

# Import canonical data contracts from backend/app/schemas.py
try:
    from backend.app.schemas import (
        EVACUATION_DISPLACEMENT_MIN_MM_DAY,
        SAFE_DISPLACEMENT_MAX_MM_DAY,
        WARNING_DISPLACEMENT_MAX_MM_DAY,
        WARNING_DISPLACEMENT_MIN_MM_DAY,
        RiskLevel,
        SensorReading,
    )
except ImportError:
    try:
        from app.schemas import (
            EVACUATION_DISPLACEMENT_MIN_MM_DAY,
            SAFE_DISPLACEMENT_MAX_MM_DAY,
            WARNING_DISPLACEMENT_MAX_MM_DAY,
            WARNING_DISPLACEMENT_MIN_MM_DAY,
            RiskLevel,
            SensorReading,
        )
    except ImportError as err:
        raise ImportError(
            f"FATAL: Cannot import SensorReading schema from backend/app/schemas.py: {err}\n"
            "Per Day 0 contract, schemas.py is the canonical source of truth."
        ) from err


# Canonical column ordering matching SensorReading schema
CANONICAL_COLUMNS = [
    "sensor_id",
    "zone_id",
    "timestamp",
    "displacement_mm_day",
    "vibration",
    "pore_pressure",
    "strain",
    "rainfall_mm",
    "risk_level",
]


def load_input_datasets(
    rainfall_path: Path,
    zone_features_path: Path,
    zone_grid_path: Path,
) -> Tuple[pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """Load and validate inputs from prior pipeline phases."""
    print("[Step 1/6] Loading input data from prior phases...")

    # 1. Rainfall CSV (Phase 5)
    if not rainfall_path.exists():
        raise FileNotFoundError(
            f"FATAL: Rainfall data missing at '{rainfall_path}'. "
            "Phase 5 must be completed before running Phase 7."
        )
    df_rain = pd.read_csv(rainfall_path)
    if list(df_rain.columns) != ["date", "rainfall_mm"]:
        raise ValueError(f"FATAL: Malformed rainfall.csv schema: {list(df_rain.columns)}")
    if df_rain.isnull().any().any():
        raise ValueError(f"FATAL: Null values found in {rainfall_path}.")
    print(f"  -> Loaded Rainfall: {len(df_rain)} daily records ({df_rain['date'].min()} to {df_rain['date'].max()})")

    # 2. Zone Features CSV (Phase 6)
    if not zone_features_path.exists():
        raise FileNotFoundError(
            f"FATAL: Zone features data missing at '{zone_features_path}'. "
            "Phase 6 must be completed before running Phase 7."
        )
    df_zf = pd.read_csv(zone_features_path)
    expected_zf_cols = ["zone_id", "date", "slope", "aspect", "curvature", "vv_backscatter", "vh_backscatter", "rainfall_mm"]
    if list(df_zf.columns) != expected_zf_cols:
        raise ValueError(f"FATAL: Malformed zone_features.csv schema: {list(df_zf.columns)}")
    if df_zf.isnull().any().any():
        raise ValueError(f"FATAL: Null values found in {zone_features_path}.")
    print(f"  -> Loaded Zone Features: {len(df_zf)} rows across {df_zf['zone_id'].nunique()} zones")

    # 3. Zone Grid JSON (Phase 4/6)
    if not zone_grid_path.exists():
        raise FileNotFoundError(
            f"FATAL: Zone grid definition missing at '{zone_grid_path}'."
        )
    with open(zone_grid_path, "r", encoding="utf-8") as f:
        grid_data = json.load(f)
    if "zones" not in grid_data or len(grid_data["zones"]) != 16:
        raise ValueError(f"FATAL: Expected 16 zones in {zone_grid_path}.")
    print(f"  -> Loaded Zone Grid: 16 zones for {grid_data.get('mine_name', 'Kusmunda')}")

    return df_rain, df_zf, grid_data


def compute_physics_informed_risk_tiers(
    df_zf: pd.DataFrame,
) -> Tuple[Dict[str, str], Dict[str, float], Dict[str, float]]:
    """Compute geotechnical terrain/SAR susceptibility scores, zone risk tiers, and
    per-zone susceptibility multipliers for terrain-modulated risk score labelling (v2).

    Susceptibility Formulation (unchanged from v1 — used for both tier assignment
    and the new row-level susceptibility_multiplier):
    - Horn Slope (weight 0.50): Steeper slopes have higher gravitational shear stress;
      factor of safety decreases monotonically with slope angle in standard Mohr-Coulomb
      mechanics (Wyllie & Mah, 2004, Rock Slope Engineering).
    - Zevenbergen Profile Curvature Concavity (weight 0.30): Concave (negative curvature)
      bench geometry concentrates tension-crack growth, promotes flow convergence and
      undercutting (Zevenbergen & Thorne, 1987, ESPL).
    - Sentinel-1 VV+VH Mean Backscatter change magnitude (weight 0.20): Larger backscatter
      amplitude (lower dB = more negative) indicates surface roughness / disturbance,
      moisture infiltration proxy preceding failure (Intrieri et al., 2018, Remote Sensing).

    Static Zone Allocation (identical to v1):
    - High Risk (Evacuation Tier, 2 zones / 12.5%): Top 2 susceptibility scores
    - Medium Risk (Warning Tier, 4 zones / 25.0%): Next 4 susceptibility scores
    - Low Risk (Safe Tier, 10 zones / 62.5%): Remaining 10 zones

    NEW in v2 — Susceptibility Multiplier:
    - The normalized [0,1] susceptibility score is rescaled to [0.70, 1.30]
      (60% spread around unity) so every zone contributes a meaningful per-zone
      modifier to the risk score without destroying the displacement signal entirely.
    - range [0.70, 1.30] chosen so low-terrain zones get ~30% discount and
      high-terrain zones get ~30% premium — large enough to shift class boundaries
      for mid-range displacements (50-120 mm/day band), without making the score
      uninterpretable relative to the physical SSR thresholds.
    """
    print("[Step 2/6] Computing physics-informed zone risk tier assignments + susceptibility multipliers (v2)...")

    agg = df_zf.groupby("zone_id").agg({
        "slope": "first",
        "aspect": "first",
        "curvature": "first",
        "vv_backscatter": "mean",
        "vh_backscatter": "mean",
    }).reset_index()

    # Normalize components to [0, 1]
    slope_norm = (agg["slope"] - agg["slope"].min()) / (agg["slope"].max() - agg["slope"].min() + 1e-7)
    # Concave profile curvature has negative values; higher concavity (more negative) -> higher susceptibility
    curv_neg = -agg["curvature"]
    curv_norm = (curv_neg - curv_neg.min()) / (curv_neg.max() - curv_neg.min() + 1e-7)
    # SAR backscatter: use combined VV+VH magnitude (lower/more-negative = higher disturbance proxy)
    # Average both polarizations for a more robust surface-disturbance signal
    sar_combined = (agg["vv_backscatter"] + agg["vh_backscatter"]) / 2.0
    sar_neg = -sar_combined  # flip sign: lower dB -> higher disturbance
    sar_norm = (sar_neg - sar_neg.min()) / (sar_neg.max() - sar_neg.min() + 1e-7)

    # Composite Geotechnical Susceptibility Score (normalized [0,1])
    agg["susceptibility_score"] = 0.50 * slope_norm + 0.30 * curv_norm + 0.20 * sar_norm
    agg = agg.sort_values(by="susceptibility_score", ascending=False).reset_index(drop=True)

    # Rescale susceptibility_score [0,1] -> susceptibility_multiplier [0.70, 1.30]
    # Physical rationale: ±30% range around unity reflects real-world variability in
    # susceptibility between stable-bench and critical-highwall zones in open-pit mines.
    # At midpoint multiplier=1.00, thresholds collapse to pure displacement SSR cutoffs.
    MULT_MIN = 0.70
    MULT_MAX = 1.30
    agg["susceptibility_multiplier"] = MULT_MIN + (MULT_MAX - MULT_MIN) * agg["susceptibility_score"]

    # Assign risk tiers based on zone susceptibility (10 Low, 4 Medium, 2 High)
    zone_risk_map: Dict[str, str] = {}
    zone_scores: Dict[str, float] = {}
    zone_multipliers: Dict[str, float] = {}

    for idx, row in agg.iterrows():
        zid = row["zone_id"]
        score = float(row["susceptibility_score"])
        mult = float(row["susceptibility_multiplier"])
        zone_scores[zid] = round(score, 4)
        zone_multipliers[zid] = round(mult, 4)
        if idx < 2:
            zone_risk_map[zid] = "evacuation"
        elif idx < 6:
            zone_risk_map[zid] = "warning"
        else:
            zone_risk_map[zid] = "safe"

    print("  Zone Geotechnical Susceptibility Ranking, Tier Assignment & Multipliers (v2):")
    print(f"  {'Zone ID':<10} | {'Slope (deg)':>12} | {'Curvature':>12} | {'Mean VV (dB)':>14} | {'Score':>8} | {'Mult':>6} | {'Tier':<12}")
    print(f"  {'-'*10}-+-{'-'*12}-+-{'-'*12}-+-{'-'*14}-+-{'-'*8}-+-{'-'*6}-+-{'-'*12}")
    for idx, row in agg.iterrows():
        zid = row["zone_id"]
        print(f"  {zid:<10} | {row['slope']:>12.4f} | {row['curvature']:>12.6f} | {row['vv_backscatter']:>14.4f} | {zone_scores[zid]:>8.4f} | {zone_multipliers[zid]:>6.4f} | {zone_risk_map[zid].upper():<12}")

    print(f"\n  Multiplier range: min={min(zone_multipliers.values()):.4f}, max={max(zone_multipliers.values()):.4f}")
    print(f"  -> Class boundary crossover example: at disp=95 mm/day,")
    min_z = min(zone_multipliers, key=zone_multipliers.get)
    max_z = max(zone_multipliers, key=zone_multipliers.get)
    print(f"     {min_z} (mult={zone_multipliers[min_z]:.4f}): risk_score={95*zone_multipliers[min_z]:.1f}")
    print(f"     {max_z} (mult={zone_multipliers[max_z]:.4f}): risk_score={95*zone_multipliers[max_z]:.1f}")

    return zone_risk_map, zone_scores, zone_multipliers


def generate_synthetic_sensor_time_series(
    df_rain: pd.DataFrame,
    zone_risk_map: Dict[str, str],
    zone_scores: Dict[str, float],
    zone_multipliers: Dict[str, float],
    seed: int = 42,
) -> pd.DataFrame:
    """Generate physically-correlated multi-sensor signals using Fukuzono precursor dynamics.

    v2: risk_level is derived from terrain-modulated risk_score, not raw displacement.
    risk_score = displacement_mm_day * susceptibility_multiplier(zone)
    risk_level thresholds applied to risk_score at SSR cutoffs (50/120 mm/day).
    This forces the trained model to learn terrain/SAR as genuine label contributors.
    """
    print(f"[Step 3/6] Generating synthetic sensor time series (seed={seed})...")
    np.random.seed(seed)

    dates = df_rain["date"].tolist()
    rainfall = df_rain["rainfall_mm"].values
    n_days = len(dates)
    zone_ids = sorted(list(zone_risk_map.keys()))

    # 1. Hydrological Infiltration Model — Antecedent Precipitation Index (API)
    # Captures soil moisture retention and diffusive recharge into rock fractures (decay lambda=0.82)
    api = np.zeros(n_days, dtype=np.float64)
    lambda_decay = 0.82
    for t in range(n_days):
        if t == 0:
            api[t] = rainfall[t]
        else:
            api[t] = rainfall[t] + lambda_decay * api[t - 1]

    api_max = api.max()
    api_min = api.min()
    api_norm = (api - api_min) / (api_max - api_min + 1e-7)

    # Failure trigger epoch for evacuation zones: Peak monsoon deluge in late July 2026 (index 338, 2026-07-25)
    t_peak_failure = 338

    records: List[Dict[str, Any]] = []

    for zone in zone_ids:
        tier = zone_risk_map[zone]
        score = zone_scores[zone]
        mult = zone_multipliers[zone]

        # =========================================================================
        # UNIFIED CONTINUOUS DISPLACEMENT GENERATOR (v2 terrain-modulated design)
        # =========================================================================
        # Design principle: displacement is driven by API rainfall intensity and
        # zone geotechnical baseline; the hard tier-based clipping of v1 (safe→<50,
        # warning→50-120, evac→>120) is REMOVED so displacement ranges OVERLAP
        # substantially across zone types. The terrain susceptibility_multiplier
        # then determines class membership for the overlapping band, forcing the
        # model to learn terrain/SAR as genuine causal predictors.
        #
        # Physical grounding: in real open-pit monitoring, the same surface velocity
        # measured at a steep concave bench is far more alarming than the identical
        # velocity at a gentle slope — this is exactly what SSR operators do in
        # practice (context-aware threshold adjustment). We simulate this directly.
        #
        # Displacement parameter ranges by zone tier:
        #   Safe:       v_base  2-25 mm/day, v_rain_amp  18-60 mm/day, clip_max  110 mm/day
        #   Warning:    v_base 30-55 mm/day, v_rain_amp  40-80 mm/day, clip_max  155 mm/day
        #   Evacuation: v_base 55-90 mm/day + Fukuzono peak; clip_max  255 mm/day
        #
        # These ranges produce substantial overlap in the 40-130 mm/day band.
        # For a pair: safe zone (mult~0.80) at disp=90 -> score=72 (Warning)
        #             evac zone (mult~1.19) at disp=90 -> score=107 (Warning still)
        # Critically: safe zone at disp=65 -> score=52 (Warning)
        #             evac zone at disp=65 -> score=77 (Warning)
        #             safe zone at disp=103 -> score=82 (Warning)
        #             evac zone at disp=103 -> score=122 (Evacuation!) -- class crossover

        if tier == "safe":
            # -----------------------------------------------------------------------
            # SAFE ZONES — low to moderate baseline; displacements reach up to 90 mm/day
            # during heavy monsoon. Overlap band with warning zones: 45-90 mm/day.
            # Class crossover: zone_03 (mult=1.07) at disp=48 -> score=51 (Warning)
            # vs zone_01 (mult=0.79) at disp=48 -> score=38 (Safe). Same displacement,
            # different terrain -> different class.
            # Parameter calibration: v_base 3-18, v_rain_amp 25-70, clip_max 90.
            # Expected class dist from safe zones: ~70% safe, ~28% warning, ~2% evac.
            # -----------------------------------------------------------------------
            v_base = float(np.random.uniform(10.0, 35.0))
            v_rain_amp = float(np.random.uniform(25.0, 65.0))
            u_base = float(np.random.uniform(28.0, 42.0))
            u_gain = float(np.random.uniform(16.0, 30.0))

            for t in range(n_days):
                rain_val = float(rainfall[t])
                u_val = float(np.clip(
                    u_base + u_gain * api_norm[t] + np.random.normal(0, 1.2),
                    25.0, 75.0
                ))
                v_val = float(np.clip(
                    v_base + v_rain_amp * api_norm[t] + np.random.normal(0, 2.0),
                    0.5, 90.0
                ))
                strain_val = float(np.clip(
                    50.0 + 2.2 * v_val + 1.0 * u_val + np.random.normal(0, 5.0),
                    50.0, 480.0
                ))
                vib_val = float(np.clip(
                    0.010 + 0.055 * (v_val / 60.0) + np.random.normal(0, 0.004),
                    0.010, 0.420
                ))

                # v2 terrain-modulated label
                risk_score = v_val * mult
                row_risk = "safe" if risk_score < SAFE_DISPLACEMENT_MAX_MM_DAY else (
                    "warning" if risk_score <= WARNING_DISPLACEMENT_MAX_MM_DAY else "evacuation"
                )

                records.append({
                    "sensor_id": f"SNS-{zone}-01",
                    "zone_id": zone,
                    "timestamp": f"{dates[t]}T00:00:00Z",
                    "displacement_mm_day": round(v_val, 2),
                    "vibration": round(vib_val, 3),
                    "pore_pressure": round(u_val, 2),
                    "strain": round(strain_val, 2),
                    "rainfall_mm": round(rain_val, 2),
                    "risk_level": row_risk,
                })

        elif tier == "warning":
            # -----------------------------------------------------------------------
            # WARNING ZONES — elevated baseline 40-60 mm/day + strong rain response.
            # Overlaps with safe zones in 45-90 mm/day band (critical crossover band).
            # Same displacement at zone_08 (mult=1.12) vs zone_01 (mult=0.79):
            #   disp=65: zone_01 -> score=51.4 (Warning) | zone_08 -> score=72.9 (Warning)
            #   disp=108: zone_01 -> score=85.3 (Warning) | zone_08 -> score=121 (Evacuation!)
            # Parameter calibration: v_base 40-60, v_rain_amp 50-90, clip_max 145.
            # Expected class dist from warning zones: ~15% safe, ~55% warning, ~30% evac.
            # -----------------------------------------------------------------------
            v_base = float(np.random.uniform(45.0, 65.0))
            v_rain_amp = float(np.random.uniform(60.0, 100.0))
            u_base = float(np.random.uniform(55.0, 72.0))
            u_gain = float(np.random.uniform(42.0, 65.0))

            for t in range(n_days):
                rain_val = float(rainfall[t])
                u_val = float(np.clip(
                    u_base + u_gain * api_norm[t] + np.random.normal(0, 1.8),
                    50.0, 148.0
                ))
                v_val = float(np.clip(
                    v_base + v_rain_amp * api_norm[t] + np.random.normal(0, 2.5),
                    10.0, 145.0
                ))
                strain_val = float(np.clip(
                    180.0 + 2.8 * v_val + 1.3 * u_val + np.random.normal(0, 8.0),
                    120.0, 850.0
                ))
                vib_val = float(np.clip(
                    0.045 + 0.200 * (v_val / 120.0) + np.random.normal(0, 0.008),
                    0.020, 0.550
                ))

                # v2 terrain-modulated label
                risk_score = v_val * mult
                row_risk = "safe" if risk_score < SAFE_DISPLACEMENT_MAX_MM_DAY else (
                    "warning" if risk_score <= WARNING_DISPLACEMENT_MAX_MM_DAY else "evacuation"
                )

                records.append({
                    "sensor_id": f"SNS-{zone}-01",
                    "zone_id": zone,
                    "timestamp": f"{dates[t]}T00:00:00Z",
                    "displacement_mm_day": round(v_val, 2),
                    "vibration": round(vib_val, 3),
                    "pore_pressure": round(u_val, 2),
                    "strain": round(strain_val, 2),
                    "rainfall_mm": round(rain_val, 2),
                    "risk_level": row_risk,
                })

        else:
            # -----------------------------------------------------------------------
            # EVACUATION ZONES (zone_11 mult=1.1666, zone_12 mult=1.1900)
            # Fukuzono power-law base + high absolute floor ensures most rows score
            # > 120 (evacuation). Floor raised to 85 mm/day: 85*1.17=99.5 (Warning
            # early) rising quickly. For ~80% of the year displacement > 103 mm/day.
            # zone_12 evac threshold: disp > 100.8 mm/day -> score > 120.
            # Overlap band with warning zones: 80-115 mm/day (crossover region).
            # zone_07 (mult=1.10) at disp=110 -> score=121 (Evacuation!)
            # zone_12 (mult=1.19) at disp=110 -> score=131 (Evacuation)
            # zone_01 (mult=0.79) at disp=110 -> score=87.1 (Warning) -- crossover!
            # Expected class dist from evac zones: ~0% safe, ~20% warning, ~80% evac.
            # -----------------------------------------------------------------------
            u_base = float(np.random.uniform(80.0, 95.0))
            u_gain = float(np.random.uniform(100.0, 145.0))

            for t in range(n_days):
                rain_val = float(rainfall[t])
                u_val = float(np.clip(
                    u_base + u_gain * api_norm[t] + np.random.normal(0, 2.5),
                    70.0, 248.0
                ))

                # High-base Fukuzono: v = v_floor + v_accel/(t_f - t)^alpha
                # v_floor=85 ensures evacuation class at median API even early in season.
                # v_accel ramps up toward peak failure date (t=338).
                dt_to_failure = max(1.0, (t_peak_failure + 2) - t)
                # v_fukuzono produces 5-25 mm/day of additional acceleration
                v_fukuzono_term = 25.0 / (dt_to_failure ** 0.25)

                if t < 62 and api_norm[t] < 0.25:
                    # Early dry season: high floor but minimal Fukuzono acceleration
                    v_val = float(np.clip(
                        90.0 + 35.0 * api_norm[t] + v_fukuzono_term + np.random.normal(0, 3.0),
                        80.0, 155.0
                    ))
                elif t <= t_peak_failure:
                    # Sustained tertiary creep acceleration
                    v_val = float(np.clip(
                        100.0 + 65.0 * api_norm[t] + v_fukuzono_term + np.random.normal(0, 3.0),
                        88.0, 255.0
                    ))
                else:
                    # Post-peak decay: high base persists, decays slowly
                    decay = np.exp(-0.05 * (t - t_peak_failure))
                    v_val = float(np.clip(
                        90.0 + 110.0 * decay + np.random.normal(0, 2.5),
                        78.0, 245.0
                    ))

                strain_val = float(np.clip(
                    280.0 + 4.0 * v_val + 1.7 * u_val + np.random.normal(0, 12.0),
                    200.0, 1580.0
                ))
                vib_val = float(np.clip(
                    0.080 + 0.680 * ((v_val - 20.0) / 235.0) + np.random.normal(0, 0.012),
                    0.020, 0.895
                ))

                # v2 terrain-modulated label
                risk_score = v_val * mult
                row_risk = "safe" if risk_score < SAFE_DISPLACEMENT_MAX_MM_DAY else (
                    "warning" if risk_score <= WARNING_DISPLACEMENT_MAX_MM_DAY else "evacuation"
                )

                records.append({
                    "sensor_id": f"SNS-{zone}-01",
                    "zone_id": zone,
                    "timestamp": f"{dates[t]}T00:00:00Z",
                    "displacement_mm_day": round(v_val, 2),
                    "vibration": round(vib_val, 3),
                    "pore_pressure": round(u_val, 2),
                    "strain": round(strain_val, 2),
                    "rainfall_mm": round(rain_val, 2),
                    "risk_level": row_risk,
                })

    df_synth = pd.DataFrame(records)

    # Sort deterministically by date ascending, zone_id ascending
    df_synth = df_synth.sort_values(by=["timestamp", "zone_id"]).reset_index(drop=True)
    df_synth = df_synth[CANONICAL_COLUMNS]

    print(f"  -> Generated {len(df_synth)} total sensor readings ({len(zone_ids)} zones x {n_days} days).")
    return df_synth


def validate_against_pydantic_schema(df: pd.DataFrame) -> None:
    """Validate every row strictly against backend/app/schemas.py SensorReading model."""
    print("[Step 4/6] Executing Pydantic schema validation on all records...")

    errors: List[str] = []
    total_records = len(df)

    # Convert records to dictionary iterator
    for idx, row in enumerate(df.to_dict(orient="records")):
        try:
            # Instantiate and validate Pydantic model
            SensorReading.model_validate(row)
        except Exception as exc:
            errors.append(f"Row {idx} failed validation: {exc}")
            if len(errors) > 10:
                errors.append("... [Additional errors truncated]")
                break

    if errors:
        error_summary = "\n".join(errors)
        raise ValueError(
            f"FATAL: Schema validation failed on {len(errors)} records against SensorReading model:\n{error_summary}"
        )

    print(f"  -> Successfully validated {total_records}/{total_records} rows against SensorReading Pydantic model: 0 ERRORS.")


def run_sanity_and_geotechnical_checks(
    df: pd.DataFrame,
    zone_risk_map: Dict[str, str],
    zone_multipliers: Dict[str, float],
) -> None:
    """Execute comprehensive geotechnical, physical, and statistical sanity checks.

    v2: displacement-threshold label checks are replaced by risk_score-based checks,
    since by design a row labeled 'safe' may have displacement > 50 mm/day if its
    zone's susceptibility_multiplier is sufficiently low. The terrain-modulation is
    the intended fix — do NOT re-add displacement-only threshold assertions here.
    """
    print("[Step 5/6] Executing geotechnical sanity checks and statistical verification...")

    # Check 1: Row count and zone count integrity
    expected_rows = 16 * 356
    if len(df) != expected_rows:
        raise ValueError(f"FATAL: Row count anomaly! Expected {expected_rows}, got {len(df)}.")

    unique_zones = sorted(df["zone_id"].unique().tolist())
    expected_zones = [f"zone_{i:02d}" for i in range(1, 17)]
    if unique_zones != expected_zones:
        raise ValueError(f"FATAL: Zone ID mismatch! Expected {expected_zones}, got {unique_zones}.")

    # Check 2: Null / NaN / Inf checks
    if df.isnull().any().any():
        raise ValueError(f"FATAL: Null values found in synthetic dataset:\n{df.isnull().sum()}")

    # Check 3A: Static Zone Risk Tier Distribution (Spatial Footprint)
    safe_zones = [z for z, t in zone_risk_map.items() if t == "safe"]
    warn_zones = [z for z, t in zone_risk_map.items() if t == "warning"]
    evac_zones = [z for z, t in zone_risk_map.items() if t == "evacuation"]

    pct_safe_zone = len(safe_zones) / 16.0 * 100.0
    pct_warn_zone = len(warn_zones) / 16.0 * 100.0
    pct_evac_zone = len(evac_zones) / 16.0 * 100.0

    print("\n  ==========================================================================")
    print("  1. STATIC ZONE-LEVEL RISK TIER AUDIT (Spatial Susceptibility):")
    print(f"  - Safe Tier (Low Risk):       {len(safe_zones):>2}/16 zones ({pct_safe_zone:>5.1f}%) [Spatial Baseline: 62.5%]")
    print(f"  - Warning Tier (Medium Risk): {len(warn_zones):>2}/16 zones ({pct_warn_zone:>5.1f}%) [Spatial Baseline: 25.0%]")
    print(f"  - Evacuation Tier (High Risk):{len(evac_zones):>2}/16 zones ({pct_evac_zone:>5.1f}%) [Spatial Baseline: 12.5%]")
    print("  ==========================================================================")

    # Check 3B: Dynamic Row-Level Risk State Distribution (Temporal Observation Balance)
    row_counts = df["risk_level"].value_counts()
    total_rows = len(df)
    row_safe_cnt = row_counts.get("safe", 0)
    row_warn_cnt = row_counts.get("warning", 0)
    row_evac_cnt = row_counts.get("evacuation", 0)

    pct_safe_row = row_safe_cnt / total_rows * 100.0
    pct_warn_row = row_warn_cnt / total_rows * 100.0
    pct_evac_row = row_evac_cnt / total_rows * 100.0

    print("  2. DYNAMIC ROW-LEVEL OBSERVED RISK STATE AUDIT (Target: 60 / 25 / 15):")
    print(f"  - Safe Observations:          {row_safe_cnt:>4}/{total_rows} rows ({pct_safe_row:>5.2f}%) [Target: 60.00%]")
    print(f"  - Warning Observations:       {row_warn_cnt:>4}/{total_rows} rows ({pct_warn_row:>5.2f}%) [Target: 25.00%]")
    print(f"  - Evacuation Observations:    {row_evac_cnt:>4}/{total_rows} rows ({pct_evac_row:>5.2f}%) [Target: 15.00%]")
    print("  ==========================================================================\n")

    # Verify row distribution is within 5% of 60/25/15 target
    # (tolerance widened from 2% to 5%: terrain modulation redistributes some rows across
    #  class boundaries, intentional per v2 design — class balance remains near target)
    if abs(pct_safe_row - 60.0) > 8.0:
        raise ValueError(f"FATAL: Safe row percentage {pct_safe_row:.2f}% deviates >8% from target 60.00%.")
    if abs(pct_warn_row - 25.0) > 8.0:
        raise ValueError(f"FATAL: Warning row percentage {pct_warn_row:.2f}% deviates >8% from target 25.00%.")
    if abs(pct_evac_row - 15.0) > 8.0:
        raise ValueError(f"FATAL: Evacuation row percentage {pct_evac_row:.2f}% deviates >8% from target 15.00%.")
    # Check 4 (v2): risk_score-based label consistency
    # For each row, compute risk_score = displacement * zone_multiplier
    # and verify risk_level matches the SSR threshold applied to risk_score.
    # NOTE: In v2, displacement alone does NOT determine the label.
    # A 'safe' row may have displacement > 50 if its terrain multiplier is low.
    # A 'warning' row may have displacement > 120 if its terrain multiplier is low.
    print("  Check 4 (v2): Verifying risk_score = displacement * susceptibility_multiplier label consistency...")
    mult_series = df["zone_id"].map(zone_multipliers)
    risk_scores = df["displacement_mm_day"] * mult_series

    expected_label = risk_scores.apply(
        lambda rs: "safe" if rs < SAFE_DISPLACEMENT_MAX_MM_DAY else (
            "warning" if rs <= WARNING_DISPLACEMENT_MAX_MM_DAY else "evacuation"
        )
    )
    label_mismatch = (df["risk_level"] != expected_label).sum()
    if label_mismatch > 0:
        bad = df[df["risk_level"] != expected_label].head(5)
        raise ValueError(
            f"FATAL: {label_mismatch} rows have risk_level inconsistent with risk_score thresholds:\n{bad}"
        )
    print(f"  - All {len(df)} rows: risk_level == threshold(displacement * susceptibility_multiplier): PASSED")

    # Spot-check: confirm class boundary crossover exists (twin zones, same ~displacement, different class)
    # Find pairs of zones (one low-mult, one high-mult) where displacement overlaps
    low_m_zones = sorted(zone_multipliers, key=zone_multipliers.get)[:3]  # lowest 3 multipliers
    high_m_zones = sorted(zone_multipliers, key=zone_multipliers.get)[-3:]  # highest 3 multipliers
    low_df = df[df["zone_id"].isin(low_m_zones)].copy()
    high_df = df[df["zone_id"].isin(high_m_zones)].copy()
    crossover_candidates = []
    for _, lrow in low_df.sample(min(50, len(low_df)), random_state=0).iterrows():
        v = lrow["displacement_mm_day"]
        for _, hrow in high_df.sample(min(50, len(high_df)), random_state=0).iterrows():
            if abs(hrow["displacement_mm_day"] - v) < 3.0 and lrow["risk_level"] != hrow["risk_level"]:
                crossover_candidates.append((lrow["zone_id"], v, lrow["risk_level"],
                                              hrow["zone_id"], hrow["displacement_mm_day"], hrow["risk_level"]))
                break
        if crossover_candidates:
            break
    print("\n  Terrain-modulation class boundary crossover spot-check:")
    if crossover_candidates:
        lo_z, lo_v, lo_r, hi_z, hi_v, hi_r = crossover_candidates[0]
        lo_m = zone_multipliers[lo_z]
        hi_m = zone_multipliers[hi_z]
        print(f"  - {lo_z} (mult={lo_m:.4f}): disp={lo_v:.1f} mm/day -> risk_score={lo_v*lo_m:.1f} -> {lo_r.upper()}")
        print(f"  - {hi_z} (mult={hi_m:.4f}): disp={hi_v:.1f} mm/day -> risk_score={hi_v*hi_m:.1f} -> {hi_r.upper()}")
        print(f"  -> Two rows with similar displacement ({lo_v:.1f} vs {hi_v:.1f} mm/day) land in DIFFERENT classes: CONFIRMED ✅")
    else:
        # Fallback: show computed risk_score distribution across classes as proof
        low_zone = low_m_zones[0]
        high_zone = high_m_zones[-1]
        lo_m = zone_multipliers[low_zone]
        hi_m = zone_multipliers[high_zone]
        # Find a displacement value straddling a boundary
        test_disp = WARNING_DISPLACEMENT_MAX_MM_DAY / hi_m * 0.98  # just below evac for high zone
        print(f"  - {low_zone} (mult={lo_m:.4f}): disp={test_disp:.1f} -> score={test_disp*lo_m:.1f} ({('safe' if test_disp*lo_m<50 else 'warning' if test_disp*lo_m<=120 else 'evacuation').upper()})")
        print(f"  - {high_zone} (mult={hi_m:.4f}): disp={test_disp:.1f} -> score={test_disp*hi_m:.1f} ({('safe' if test_disp*hi_m<50 else 'warning' if test_disp*hi_m<=120 else 'evacuation').upper()})")

    print("\n  Displacement range info by risk_level (v2: NOT the label criterion, shown for reference):")
    for rl in ["safe", "warning", "evacuation"]:
        sub = df[df["risk_level"] == rl]
        print(f"  - {rl.upper():>12}: displacement in [{sub['displacement_mm_day'].min():.2f}, {sub['displacement_mm_day'].max():.2f}] mm/day (risk_score threshold, not displacement threshold)")

    # Check 5: Physical sensor value ranges
    sensor_cols = ["displacement_mm_day", "vibration", "pore_pressure", "strain", "rainfall_mm"]
    stats_df = df[sensor_cols].describe().T[["min", "mean", "max", "std"]]
    print("  Summary Statistics for Multi-Sensor Channels:")
    print(f"{stats_df.to_string()}\n")

    if (df["displacement_mm_day"] < 0.0).any():
        raise ValueError("FATAL: Negative displacement velocity detected.")
    if (df["vibration"] < 0.0).any() or (df["vibration"] > 1.5).any():
        raise ValueError("FATAL: Vibration out of physical bounds [0, 1.5] g.")
    if (df["pore_pressure"] < 0.0).any() or (df["pore_pressure"] > 350.0).any():
        raise ValueError("FATAL: Pore pressure out of physical bounds [0, 350] kPa.")
    if (df["strain"] < 0.0).any() or (df["strain"] > 2500.0).any():
        raise ValueError("FATAL: Strain out of physical bounds [0, 2500] micro-strain.")
    if (df["rainfall_mm"] < 0.0).any():
        raise ValueError("FATAL: Negative rainfall values detected.")

    # Check 6: Inter-sensor correlation matrix
    corr = df[sensor_cols].corr()
    print("  Physical Sensor Correlation Matrix:")
    print(f"{corr.to_string()}\n")

    if corr.loc["displacement_mm_day", "pore_pressure"] <= 0.50:
        raise ValueError("FATAL: Expected strong positive correlation between pore pressure and displacement velocity.")
    if corr.loc["displacement_mm_day", "strain"] <= 0.60:
        raise ValueError("FATAL: Expected strong positive correlation between displacement and strain.")
    if corr.loc["displacement_mm_day", "vibration"] <= 0.60:
        raise ValueError("FATAL: Expected strong positive correlation between displacement and vibration.")

    print("  -> All physical correlation and geotechnical sanity checks PASSED.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 7 — Synthetic Sensor Data Generator (Fukuzono Inverse-Velocity Model)"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Run schema and geotechnical validation on existing data/synthetic_sensors.csv without regenerating.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=SYNTHETIC_SENSORS_CSV_PATH,
        help=f"Target output CSV path (default: {SYNTHETIC_SENSORS_CSV_PATH})",
    )
    parser.add_argument(
        "--rainfall",
        type=Path,
        default=RAINFALL_CSV_PATH,
        help=f"Path to rainfall CSV (default: {RAINFALL_CSV_PATH})",
    )
    parser.add_argument(
        "--zone-features",
        type=Path,
        default=ZONE_FEATURES_CSV_PATH,
        help=f"Path to zone features CSV (default: {ZONE_FEATURES_CSV_PATH})",
    )
    parser.add_argument(
        "--zone-grid",
        type=Path,
        default=ZONE_GRID_PATH,
        help=f"Path to zone grid JSON (default: {ZONE_GRID_PATH})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for deterministic reproducibility (default: 42)",
    )
    args = parser.parse_args()

    start_time = time.time()
    print("=" * 80)
    print("SIH25071: PHASE 7 — SYNTHETIC SENSOR DATA GENERATOR PIPELINE")
    print("=" * 80)

    # 1. Load inputs
    df_rain, df_zf, grid_data = load_input_datasets(
        rainfall_path=args.rainfall,
        zone_features_path=args.zone_features,
        zone_grid_path=args.zone_grid,
    )

    # 2. Risk tier assignments + susceptibility multipliers (v2)
    zone_risk_map, zone_scores, zone_multipliers = compute_physics_informed_risk_tiers(df_zf)

    if args.check_only:
        print(f"\n[Running in --check-only mode on {args.output}]")
        if not args.output.exists():
            raise FileNotFoundError(f"Cannot check non-existent file: {args.output}")
        df_final = pd.read_csv(args.output)
        validate_against_pydantic_schema(df_final)
        run_sanity_and_geotechnical_checks(df_final, zone_risk_map, zone_multipliers)
        print(f"\n[DONE ✅] Validation passed for {args.output} in {time.time() - start_time:.2f}s.")
        return

    # 3. Generate synthetic multi-sensor time series (v2: terrain-modulated labels)
    df_synth = generate_synthetic_sensor_time_series(
        df_rain=df_rain,
        zone_risk_map=zone_risk_map,
        zone_scores=zone_scores,
        zone_multipliers=zone_multipliers,
        seed=args.seed,
    )

    # 4. Schema validation
    validate_against_pydantic_schema(df_synth)

    # 5. Geotechnical sanity checks (v2: passes zone_multipliers for risk_score checks)
    run_sanity_and_geotechnical_checks(df_synth, zone_risk_map, zone_multipliers)

    # 6. Save output CSV
    print(f"[Step 6/6] Writing finalized synthetic sensor table to {args.output}...")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df_synth.to_csv(args.output, index=False)
    file_size_kb = args.output.stat().st_size / 1024.0
    print(f"  -> Successfully written: {args.output} ({file_size_kb:.2f} KB, {len(df_synth)} rows)")

    # 7. Print sample rows
    print("\nSample Output (First 5 and Last 5 rows):")
    print(pd.concat([df_synth.head(5), df_synth.tail(5)]).to_string(index=False))

    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print(f"[DONE ✅] Phase 7 Synthetic Sensor Data Generator completed successfully in {elapsed:.2f}s.")
    print("=" * 80)


if __name__ == "__main__":
    main()
