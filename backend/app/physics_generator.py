"""
backend/app/physics_generator.py -- Phase 21: Physics-informed live sensor generator.

Extracts Phase 7's per-zone, per-tick Fukuzono generation logic into an importable
module for use by the WebSocket broadcast loop.

Design contracts:
- Phase 7 (scripts/phase7_synthetic_sensors.py) is LOCKED and UNTOUCHED.
  This module is ADDITIVE -- it replicas the physics in callable form only.
- All physics formulas, parameter ranges, and threshold constants are
  byte-for-byte identical to Phase 7 v2. Any drift here would mean live
  readings are drawn from a different distribution than the trained data.
- ZoneGeneratorState is persistent across ticks. Per-zone random parameters
  (v_base, v_rain_amp, u_base, u_gain) are drawn ONCE at init from a seeded
  RNG -- never per tick. Drawing fresh params per tick collapses the physics
  signal into random noise, defeating the entire point of Phase 21.
- Timestamps on generated readings use the SIMULATED date from rainfall.csv
  (indexed by state.current_t), NOT wall-clock time. Rationale: wall-clock
  dates (2026-08-20+) fall outside the zone_features date range (2025-08-22
  to 2026-08-12), causing _lookup_sar_features() to raise "no SAR acquisition
  on or before" on every tick. Simulated dates stay within range and preserve
  the Phase 12 / Phase 20 SAR backward-fill (<=23-day staleness) property.
- The 356-day series wraps at index 356 (mod 356) so the generator runs
  indefinitely without exhausting the rainfall dataset.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from backend.app.schemas import (
        SAFE_DISPLACEMENT_MAX_MM_DAY,
        WARNING_DISPLACEMENT_MAX_MM_DAY,
        RiskLevel,
        SensorReading,
    )
except ImportError:
    from app.schemas import (  # type: ignore
        SAFE_DISPLACEMENT_MAX_MM_DAY,
        WARNING_DISPLACEMENT_MAX_MM_DAY,
        RiskLevel,
        SensorReading,
    )

# ---------------------------------------------------------------------------
# Constants -- must match Phase 7 exactly
# ---------------------------------------------------------------------------

# Fukuzono failure peak index: day 338 = 2026-07-25 (late monsoon maximum)
_T_PEAK_FAILURE: int = 338

# Deterministic zone ordering -- matches Phase 7's sorted(zone_risk_map.keys())
ZONE_IDS: list[str] = [f"zone_{i:02d}" for i in range(1, 17)]


# ---------------------------------------------------------------------------
# Generator state
# ---------------------------------------------------------------------------

@dataclass
class ZoneGeneratorState:
    """
    Persistent state for one zone's live physics generator.

    v_base, v_rain_amp, u_base, u_gain are drawn once at initialization
    and held constant across all ticks for this zone. These define the
    zone's displacement and pore-pressure behavioral envelope.

    current_t advances by 1 each step, wrapping at 356.
    rng provides per-tick Gaussian noise; seeded separately from the
    param draw so noise sequence is independent of parameter values.
    """
    zone_id: str
    tier: str               # "safe" | "warning" | "evacuation"
    mult: float             # susceptibility multiplier in [0.70, 1.30]
    v_base: float           # baseline displacement velocity (mm/day)
    v_rain_amp: float       # rainfall response amplitude
    u_base: float           # baseline pore pressure (kPa)
    u_gain: float           # pore pressure rainfall gain
    current_t: int          # cursor into 356-day series (0-indexed)
    rng: np.random.Generator  # per-zone tick-level noise RNG


# ---------------------------------------------------------------------------
# Multiplier computation -- replicates Phase 7's compute_physics_informed_risk_tiers
# ---------------------------------------------------------------------------

def _compute_zone_multipliers(
    zone_features_df: pd.DataFrame,
) -> tuple[dict[str, str], dict[str, float]]:
    """
    Compute zone risk tiers and susceptibility multipliers from zone_features.

    Logic is byte-for-byte identical to Phase 7's compute_physics_informed_risk_tiers().
    Inlined here (not imported from phase7_synthetic_sensors.py) so this module is
    importable without Phase 7's side effects (argparse, sys.path mutations, print storms).

    Returns:
        zone_risk_map    -- zone_id -> "safe" | "warning" | "evacuation"
        zone_multipliers -- zone_id -> float in [0.70, 1.30]
    """
    agg = zone_features_df.groupby("zone_id").agg(
        slope=("slope", "first"),
        curvature=("curvature", "first"),
        vv_backscatter=("vv_backscatter", "mean"),
        vh_backscatter=("vh_backscatter", "mean"),
    ).reset_index()

    # Normalize components to [0, 1] -- identical to Phase 7 (weights: slope 0.50,
    # curvature 0.30, SAR 0.20)
    slope_norm = (agg["slope"] - agg["slope"].min()) / (
        agg["slope"].max() - agg["slope"].min() + 1e-7
    )
    curv_neg = -agg["curvature"]  # concave (negative) = higher susceptibility
    curv_norm = (curv_neg - curv_neg.min()) / (
        curv_neg.max() - curv_neg.min() + 1e-7
    )
    sar_combined = (agg["vv_backscatter"] + agg["vh_backscatter"]) / 2.0
    sar_neg = -sar_combined  # lower dB = higher disturbance proxy
    sar_norm = (sar_neg - sar_neg.min()) / (
        sar_neg.max() - sar_neg.min() + 1e-7
    )

    agg["susceptibility_score"] = (
        0.50 * slope_norm + 0.30 * curv_norm + 0.20 * sar_norm
    )
    agg = agg.sort_values(by="susceptibility_score", ascending=False).reset_index(drop=True)

    # Rescale [0,1] -> [0.70, 1.30] (Phase 7 MULT_MIN=0.70, MULT_MAX=1.30)
    agg["susceptibility_multiplier"] = 0.70 + 0.60 * agg["susceptibility_score"]

    zone_risk_map: dict[str, str] = {}
    zone_multipliers: dict[str, float] = {}

    for idx, row in agg.iterrows():
        zid = str(row["zone_id"])
        mult = float(row["susceptibility_multiplier"])
        zone_multipliers[zid] = round(mult, 4)
        if idx < 2:
            zone_risk_map[zid] = "evacuation"
        elif idx < 6:
            zone_risk_map[zid] = "warning"
        else:
            zone_risk_map[zid] = "safe"

    return zone_risk_map, zone_multipliers


# ---------------------------------------------------------------------------
# API norm computation -- replicates Phase 7's antecedent precipitation index
# ---------------------------------------------------------------------------

def compute_api_norm(rainfall_values: np.ndarray, lambda_decay: float = 0.82) -> np.ndarray:
    """
    Compute Antecedent Precipitation Index and normalize to [0, 1].

    API_t = P_t + lambda * API_{t-1}  (lambda_decay=0.82, identical to Phase 7)

    Captures soil moisture retention and diffusive hydraulic recharge into
    rock fractures. Must be computed from the full 356-day series to preserve
    API's temporal memory of prior wet periods.
    """
    n = len(rainfall_values)
    api = np.zeros(n, dtype=np.float64)
    for t in range(n):
        api[t] = rainfall_values[t] + (lambda_decay * api[t - 1] if t > 0 else 0.0)
    api_max, api_min = api.max(), api.min()
    return (api - api_min) / (api_max - api_min + 1e-7)


# ---------------------------------------------------------------------------
# Data loading -- called once from lifespan
# ---------------------------------------------------------------------------

def load_generator_data(
    repo_root: Path,
) -> tuple[np.ndarray, np.ndarray, list[str], dict[str, str], dict[str, float]]:
    """
    Load rainfall + zone_features, compute all static generator inputs.
    Called ONCE at startup from the lifespan -- not per tick.

    Returns:
        api_norm         -- shape (356,) float64, normalized API index
        rainfall_values  -- shape (356,) float64, raw daily rainfall (mm)
        sim_dates        -- list[str] of 356 date strings ("YYYY-MM-DD")
        zone_risk_map    -- zone_id -> tier
        zone_multipliers -- zone_id -> susceptibility multiplier
    """
    rainfall_path = repo_root / "data" / "rainfall.csv"
    zone_features_path = repo_root / "data" / "zone_features.csv"

    df_rain = pd.read_csv(rainfall_path)
    rainfall_values = df_rain["rainfall_mm"].values.astype(np.float64)
    sim_dates: list[str] = df_rain["date"].tolist()

    df_zf = pd.read_csv(zone_features_path)
    zone_risk_map, zone_multipliers = _compute_zone_multipliers(df_zf)

    api_norm = compute_api_norm(rainfall_values)

    return api_norm, rainfall_values, sim_dates, zone_risk_map, zone_multipliers


# ---------------------------------------------------------------------------
# Zone state initialization
# ---------------------------------------------------------------------------

def build_zone_generator_state(
    zone_id: str,
    tier: str,
    mult: float,
    initial_t: int = 0,
    seed: int | None = None,
) -> ZoneGeneratorState:
    """
    Initialize one zone's generator state with per-zone random parameters.

    Two separate RNG instances are used:
    - param_rng: draws fixed per-zone envelope parameters (used once)
    - tick_rng:  draws per-step Gaussian noise (used every step_zone call)
    Keeping them separate ensures tick noise is independent of parameter
    sampling order.

    Args:
        zone_id:    e.g. "zone_11"
        tier:       "safe" | "warning" | "evacuation"
        mult:       susceptibility multiplier for this zone
        initial_t:  starting cursor in 0..355
        seed:       RNG seed. Defaults to stable hash of zone_id.
    """
    if seed is None:
        seed = abs(hash(zone_id)) % (2 ** 31)

    param_rng = np.random.default_rng(seed)
    tick_rng = np.random.default_rng(seed + 1)

    if tier == "safe":
        v_base = float(param_rng.uniform(10.0, 35.0))
        v_rain_amp = float(param_rng.uniform(25.0, 65.0))
        u_base = float(param_rng.uniform(28.0, 42.0))
        u_gain = float(param_rng.uniform(16.0, 30.0))
    elif tier == "warning":
        v_base = float(param_rng.uniform(45.0, 65.0))
        v_rain_amp = float(param_rng.uniform(60.0, 100.0))
        u_base = float(param_rng.uniform(55.0, 72.0))
        u_gain = float(param_rng.uniform(42.0, 65.0))
    else:  # evacuation -- Fukuzono formula replaces v_base/v_rain_amp
        v_base = 0.0
        v_rain_amp = 0.0
        u_base = float(param_rng.uniform(80.0, 95.0))
        u_gain = float(param_rng.uniform(100.0, 145.0))

    return ZoneGeneratorState(
        zone_id=zone_id,
        tier=tier,
        mult=mult,
        v_base=v_base,
        v_rain_amp=v_rain_amp,
        u_base=u_base,
        u_gain=u_gain,
        current_t=initial_t % 356,
        rng=tick_rng,
    )


def initialize_all_zone_states(
    zone_risk_map: dict[str, str],
    zone_multipliers: dict[str, float],
) -> dict[str, ZoneGeneratorState]:
    """
    Build initial ZoneGeneratorState for all 16 zones.

    Staggered initial offsets (zone_01 at t=0, zone_02 at t=1, ..., zone_16
    at t=15) ensure the first full rotation broadcasts 16 distinct simulated
    dates. Stagger of 15 days is small enough not to affect SAR backward-fill.
    """
    return {
        zone_id: build_zone_generator_state(
            zone_id=zone_id,
            tier=zone_risk_map.get(zone_id, "safe"),
            mult=zone_multipliers.get(zone_id, 1.0),
            initial_t=idx,
        )
        for idx, zone_id in enumerate(ZONE_IDS)
    }


# ---------------------------------------------------------------------------
# Per-tick step function -- the live generation core
# ---------------------------------------------------------------------------

def step_zone(
    state: ZoneGeneratorState,
    api_norm: np.ndarray,
    rainfall_values: np.ndarray,
    sim_dates: list[str],
) -> SensorReading:
    """
    Advance one zone by a single timestep and return its SensorReading.

    Mutates state.current_t (increments mod 356 -- wraps at series end).

    Physics are byte-for-byte identical to Phase 7's per-tier loops
    (lines 420-598 of scripts/phase7_synthetic_sensors.py), restructured
    to operate on a single index t rather than iterating all 356 days.

    The returned timestamp is the SIMULATED date from rainfall.csv at index t.
    See module docstring for why wall-clock time must NOT be used here.
    """
    t = state.current_t
    rng = state.rng
    rain_val = float(rainfall_values[t])
    api_val = float(api_norm[t])

    if state.tier == "safe":
        u_val = float(np.clip(
            state.u_base + state.u_gain * api_val + rng.normal(0, 1.2),
            25.0, 75.0,
        ))
        v_val = float(np.clip(
            state.v_base + state.v_rain_amp * api_val + rng.normal(0, 2.0),
            0.5, 90.0,
        ))
        strain_val = float(np.clip(
            50.0 + 2.2 * v_val + 1.0 * u_val + rng.normal(0, 5.0),
            50.0, 480.0,
        ))
        vib_val = float(np.clip(
            0.010 + 0.055 * (v_val / 60.0) + rng.normal(0, 0.004),
            0.010, 0.420,
        ))

    elif state.tier == "warning":
        u_val = float(np.clip(
            state.u_base + state.u_gain * api_val + rng.normal(0, 1.8),
            50.0, 148.0,
        ))
        v_val = float(np.clip(
            state.v_base + state.v_rain_amp * api_val + rng.normal(0, 2.5),
            10.0, 145.0,
        ))
        strain_val = float(np.clip(
            180.0 + 2.8 * v_val + 1.3 * u_val + rng.normal(0, 8.0),
            120.0, 850.0,
        ))
        vib_val = float(np.clip(
            0.045 + 0.200 * (v_val / 120.0) + rng.normal(0, 0.008),
            0.020, 0.550,
        ))

    else:  # evacuation -- Fukuzono power-law acceleration toward t_peak_failure
        u_val = float(np.clip(
            state.u_base + state.u_gain * api_val + rng.normal(0, 2.5),
            70.0, 248.0,
        ))
        dt_to_failure = max(1.0, float(_T_PEAK_FAILURE + 2 - t))
        v_fukuzono = 25.0 / (dt_to_failure ** 0.25)

        if t < 62 and api_val < 0.25:
            # Early dry season: high floor, minimal Fukuzono acceleration
            v_val = float(np.clip(
                90.0 + 35.0 * api_val + v_fukuzono + rng.normal(0, 3.0),
                80.0, 155.0,
            ))
        elif t <= _T_PEAK_FAILURE:
            # Sustained tertiary creep acceleration toward peak failure date
            v_val = float(np.clip(
                100.0 + 65.0 * api_val + v_fukuzono + rng.normal(0, 3.0),
                88.0, 255.0,
            ))
        else:
            # Post-peak exponential decay
            decay = math.exp(-0.05 * (t - _T_PEAK_FAILURE))
            v_val = float(np.clip(
                90.0 + 110.0 * decay + rng.normal(0, 2.5),
                78.0, 245.0,
            ))

        strain_val = float(np.clip(
            280.0 + 4.0 * v_val + 1.7 * u_val + rng.normal(0, 12.0),
            200.0, 1580.0,
        ))
        vib_val = float(np.clip(
            0.080 + 0.680 * ((v_val - 20.0) / 235.0) + rng.normal(0, 0.012),
            0.020, 0.895,
        ))

    # v2 terrain-modulated risk label -- identical to Phase 7 v2:
    # risk_score = displacement * susceptibility_multiplier
    # risk_level = threshold(risk_score) at SSR cutoffs 50 / 120 mm/day
    risk_score = v_val * state.mult
    if risk_score < SAFE_DISPLACEMENT_MAX_MM_DAY:
        risk_level_str = "safe"
    elif risk_score <= WARNING_DISPLACEMENT_MAX_MM_DAY:
        risk_level_str = "warning"
    else:
        risk_level_str = "evacuation"

    # Advance cursor -- wraps for continuous operation past 356 days
    state.current_t = (t + 1) % 356

    return SensorReading(
        sensor_id=f"SNS-{state.zone_id}-01",
        zone_id=state.zone_id,
        timestamp=f"{sim_dates[t]}T00:00:00Z",
        displacement_mm_day=round(v_val, 2),
        vibration=round(vib_val, 3),
        pore_pressure=round(u_val, 2),
        strain=round(strain_val, 2),
        rainfall_mm=round(rain_val, 2),
        risk_level=RiskLevel(risk_level_str),
    )
