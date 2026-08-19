#!/usr/bin/env python3
"""
Phase 6 — Zone Feature Table Assembly Pipeline
SIH25071: AI-Based Rockfall Prediction and Alert System

================================================================================
GEOTECHNICAL & MACHINE LEARNING CONTEXT:
--------------------------------------------------------------------------------
This pipeline serves as the primary data fusion hub for Person 1's geospatial
deliverables, integrating:
1. Static Geomorphological Terrain Derivatives (Phase 3):
   - Slope (degrees [0, 90], Horn 1981): Key driver of shear stress and gravitational driving force.
   - Circular Aspect (degrees [0, 360)): Directional exposure to weathering, solar radiation, and prevailing precipitation.
     * Note: Computed using circular mean (arctan2 of mean sin/cos vectors) to prevent directional averaging artifacts (e.g., 359° and 1° averaging to 180° instead of 0°/360°).
   - Profile Curvature (m^-1, Zevenbergen & Thorne 1987): Flow-acceleration failure surface indicator (concave/convex bench morphology).
2. Multi-temporal SAR Backscatter Intensity (Phase 4):
   - Co-pol (VV, dB): Surface roughness, tension cracks, soil moisture.
   - Cross-pol (VH, dB): Volume scattering, structural disaggregation.
3. Multi-temporal Precipitation (Phase 5):
   - Daily Rainfall (mm, Open-Meteo ERA5-Land reanalysis): Hydrological trigger for pore-water pressure spikes and shear strength reduction.

ARCHITECTURAL DECISION — TEMPORAL TABLE FORMAT:
--------------------------------------------------------------------------------
Format: Long format (per zone-date: 16 zones x 30 Sentinel-1 acquisition dates = 480 rows).
Rationale: Preserves full temporal granularity for downstream modeling:
- Person 3 (ML Baseline): Can compute rolling stats, lag features, and backscatter deltas (ΔVV, ΔVH).
- Person 4 (Deep Learning): Directly feeds sequence models (LSTM/GRU) on time series.
Static terrain parameters (slope, aspect, curvature) are systematically broadcast per zone across dates.

SCHEMA CONTRACT:
--------------------------------------------------------------------------------
Output columns: [zone_id, date, slope, aspect, curvature, vv_backscatter, vh_backscatter, rainfall_mm]
zone_id format: "zone_01" through "zone_16", matching data/zone_grid.json, data/sar_backscatter.csv,
and backend/app/schemas.py (SensorReading contract).
================================================================================
"""

import argparse
import json
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
import rasterio
import rasterio.mask

# Resolve repo root directory and canonical paths
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

# Input file paths
AOI_PATH = DATA_DIR / "aoi.json"
ZONE_GRID_PATH = DATA_DIR / "zone_grid.json"
DEM_RASTER_PATH = DATA_DIR / "dem.tif"
SLOPE_RASTER_PATH = DATA_DIR / "slope.tif"
ASPECT_RASTER_PATH = DATA_DIR / "aspect.tif"
CURVATURE_RASTER_PATH = DATA_DIR / "curvature.tif"
SAR_CSV_PATH = DATA_DIR / "sar_backscatter.csv"
RAINFALL_CSV_PATH = DATA_DIR / "rainfall.csv"

# Target output file path
ZONE_FEATURES_CSV_PATH = DATA_DIR / "zone_features.csv"

# Canonical output schema
CANONICAL_COLUMNS = [
    "zone_id",
    "date",
    "slope",
    "aspect",
    "curvature",
    "vv_backscatter",
    "vh_backscatter",
    "rainfall_mm",
]


def load_zone_grid(grid_path: Path) -> Dict[str, Any]:
    """Load and validate the 16-zone spatial grid from data/zone_grid.json."""
    print(f"[Step 1/6] Loading zone grid definition from {grid_path.name}...")
    if not grid_path.exists():
        raise FileNotFoundError(
            f"FATAL: Zone grid file missing at '{grid_path}'. "
            "Phase 4 must generate data/zone_grid.json before Phase 6 execution."
        )

    try:
        with open(grid_path, "r", encoding="utf-8") as f:
            grid_data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"FATAL: Malformed JSON in '{grid_path}': {exc}") from exc

    if "zones" not in grid_data or not isinstance(grid_data["zones"], list):
        raise KeyError(f"FATAL: 'zones' list missing or malformed in '{grid_path}'.")

    zones = grid_data["zones"]
    if len(zones) != 16:
        raise ValueError(f"FATAL: Expected exactly 16 zones in '{grid_path}', found {len(zones)}.")

    print(f"  -> Successfully loaded {len(zones)} zones for mine: {grid_data.get('mine_name', 'Unknown')}")
    return grid_data


def compute_zone_terrain_statistics(
    zones: List[Dict[str, Any]],
    slope_path: Path,
    aspect_path: Path,
    curvature_path: Path,
) -> Dict[str, Dict[str, float]]:
    """Compute zonal terrain statistics per zone polygon using rasterio masking.
    
    Terrain Metrics:
    - Slope: Mean slope in geotechnical degrees [0, 90].
    - Aspect: Circular mean aspect in azimuth degrees [0, 360) using vector summation:
      mean_aspect = rad2deg(arctan2(mean(sin(rad)), mean(cos(rad)))) % 360
    - Curvature: Mean profile curvature (m^-1).
    """
    print(f"[Step 2/6] Computing zonal terrain statistics via rasterio polygon masking...")

    for path in [slope_path, aspect_path, curvature_path]:
        if not path.exists():
            raise FileNotFoundError(f"FATAL: Required terrain raster missing at '{path}'.")

    zone_terrain_stats: Dict[str, Dict[str, float]] = {}

    with rasterio.open(slope_path) as slope_src, \
         rasterio.open(aspect_path) as aspect_src, \
         rasterio.open(curvature_path) as curv_src:

        print(f"  Raster Metadata:")
        print(f"  - Slope:     shape={slope_src.shape}, CRS={slope_src.crs}, nodata={slope_src.nodata}")
        print(f"  - Aspect:    shape={aspect_src.shape}, CRS={aspect_src.crs}, nodata={aspect_src.nodata}")
        print(f"  - Curvature: shape={curv_src.shape}, CRS={curv_src.crs}, nodata={curv_src.nodata}")

        for zone in zones:
            zone_id = zone["zone_id"]
            geom = [zone["geometry"]]

            # 1. Slope zonal mean
            s_masked, _ = rasterio.mask.mask(slope_src, geom, crop=True)
            s_nodata = slope_src.nodata
            s_valid = s_masked[0][(s_masked[0] != s_nodata) & (~np.isnan(s_masked[0]))]
            if len(s_valid) == 0:
                raise ValueError(f"FATAL: No valid slope pixels found for zone '{zone_id}'.")
            mean_slope = float(np.mean(s_valid))

            # 2. Aspect zonal circular mean
            a_masked, _ = rasterio.mask.mask(aspect_src, geom, crop=True)
            a_nodata = aspect_src.nodata
            a_valid = a_masked[0][(a_masked[0] != a_nodata) & (~np.isnan(a_masked[0]))]
            if len(a_valid) == 0:
                raise ValueError(f"FATAL: No valid aspect pixels found for zone '{zone_id}'.")
            
            # Circular mean computation for directional aspect (0° - 360°)
            a_rad = np.deg2rad(a_valid)
            sin_mean = float(np.mean(np.sin(a_rad)))
            cos_mean = float(np.mean(np.cos(a_rad)))
            if abs(sin_mean) < 1e-7 and abs(cos_mean) < 1e-7:
                # Perfectly uniform or flat aspect
                mean_aspect = 0.0
            else:
                mean_aspect_rad = np.arctan2(sin_mean, cos_mean)
                mean_aspect = float(np.rad2deg(mean_aspect_rad) % 360.0)

            # 3. Profile curvature zonal mean
            c_masked, _ = rasterio.mask.mask(curv_src, geom, crop=True)
            c_nodata = curv_src.nodata
            c_valid = c_masked[0][(c_masked[0] != c_nodata) & (~np.isnan(c_masked[0]))]
            if len(c_valid) == 0:
                raise ValueError(f"FATAL: No valid curvature pixels found for zone '{zone_id}'.")
            mean_curvature = float(np.mean(c_valid))

            zone_terrain_stats[zone_id] = {
                "slope": round(mean_slope, 4),
                "aspect": round(mean_aspect, 4),
                "curvature": round(mean_curvature, 6),
                "pixel_count": len(s_valid),
            }

    print("  -> Zone-Level Static Terrain Summary:")
    print(f"  {'Zone ID':<10} | {'Pixels':>6} | {'Slope (deg)':>12} | {'Aspect (deg)':>13} | {'Curvature':>12}")
    print(f"  {'-'*10}-+-{'-'*6}-+-{'-'*12}-+-{'-'*13}-+-{'-'*12}")
    for zid in sorted(zone_terrain_stats.keys()):
        st = zone_terrain_stats[zid]
        print(f"  {zid:<10} | {st['pixel_count']:>6} | {st['slope']:>12.4f} | {st['aspect']:>13.4f} | {st['curvature']:>12.6f}")

    return zone_terrain_stats


def load_sar_backscatter(sar_path: Path) -> pd.DataFrame:
    """Load and validate SAR backscatter time series from data/sar_backscatter.csv."""
    print(f"[Step 3/6] Loading SAR backscatter time series from {sar_path.name}...")
    if not sar_path.exists():
        raise FileNotFoundError(f"FATAL: SAR backscatter file missing at '{sar_path}'.")

    df_sar = pd.read_csv(sar_path)
    expected_sar_cols = ["date", "zone_id", "VV_mean", "VH_mean"]
    if list(df_sar.columns) != expected_sar_cols:
        raise ValueError(
            f"FATAL: Unexpected columns in '{sar_path}'. "
            f"Expected {expected_sar_cols}, got {list(df_sar.columns)}"
        )

    if df_sar.isnull().any().any():
        raise ValueError(f"FATAL: SAR backscatter data contains null values:\n{df_sar.isnull().sum()}")

    print(f"  -> Loaded SAR data: {len(df_sar)} records across {df_sar['date'].nunique()} acquisition dates and {df_sar['zone_id'].nunique()} zones.")
    return df_sar


def load_rainfall(rainfall_path: Path) -> pd.DataFrame:
    """Load and validate AOI daily rainfall records from data/rainfall.csv."""
    print(f"[Step 4/6] Loading AOI rainfall data from {rainfall_path.name}...")
    if not rainfall_path.exists():
        raise FileNotFoundError(f"FATAL: Rainfall file missing at '{rainfall_path}'.")

    df_rain = pd.read_csv(rainfall_path)
    expected_rain_cols = ["date", "rainfall_mm"]
    if list(df_rain.columns) != expected_rain_cols:
        raise ValueError(
            f"FATAL: Unexpected columns in '{rainfall_path}'. "
            f"Expected {expected_rain_cols}, got {list(df_rain.columns)}"
        )

    if df_rain.isnull().any().any():
        raise ValueError(f"FATAL: Rainfall data contains null values:\n{df_rain.isnull().sum()}")

    print(f"  -> Loaded Rainfall data: {len(df_rain)} daily records from {df_rain['date'].min()} to {df_rain['date'].max()}.")
    return df_rain


def assemble_zone_feature_table(
    zone_terrain_stats: Dict[str, Dict[str, float]],
    df_sar: pd.DataFrame,
    df_rain: pd.DataFrame,
) -> pd.DataFrame:
    """Assemble final multi-source zone feature table in canonical long format."""
    print(f"[Step 5/6] Assembling and joining multi-source zone feature table...")

    # Build terrain DataFrame
    terrain_records = []
    for zone_id, stats in zone_terrain_stats.items():
        terrain_records.append({
            "zone_id": zone_id,
            "slope": stats["slope"],
            "aspect": stats["aspect"],
            "curvature": stats["curvature"],
        })
    df_terrain = pd.DataFrame(terrain_records)

    # 1. Merge SAR backscatter with static terrain attributes on zone_id
    df_merged = pd.merge(df_sar, df_terrain, on="zone_id", how="left")
    if len(df_merged) != len(df_sar):
        raise ValueError(f"FATAL: Join row count mismatch: SAR {len(df_sar)} vs Merged {len(df_merged)}")

    # 2. Join AOI rainfall on date (broadcast daily rainfall across all 16 zones per date)
    df_merged = pd.merge(df_merged, df_rain, on="date", how="left")
    if len(df_merged) != len(df_sar):
        raise ValueError(f"FATAL: Join row count mismatch after rainfall merge: {len(df_merged)} rows")

    # 3. Rename SAR columns to match canonical schema
    df_merged = df_merged.rename(columns={
        "VV_mean": "vv_backscatter",
        "VH_mean": "vh_backscatter",
    })

    # 4. Enforce exact canonical column ordering
    df_final = df_merged[CANONICAL_COLUMNS].copy()

    # 5. Sort deterministically by date ascending, zone_id ascending
    df_final = df_final.sort_values(by=["date", "zone_id"]).reset_index(drop=True)

    print(f"  -> Successfully assembled final table: {len(df_final)} rows x {len(df_final.columns)} columns.")
    return df_final


def validate_and_sanity_check(
    df: pd.DataFrame,
    grid_zones: List[Dict[str, Any]],
    df_sar: pd.DataFrame,
) -> None:
    """Execute rigorous sanity checks and cross-file schema consistency validations."""
    print(f"[Step 6/6] Executing comprehensive sanity and cross-file consistency checks...")

    # Check 1: Column Schema and Types
    print("  [Check 1/5] Verifying canonical schema and column names...")
    if list(df.columns) != CANONICAL_COLUMNS:
        raise ValueError(f"FATAL: Schema mismatch! Expected {CANONICAL_COLUMNS}, got {list(df.columns)}")
    print("    -> Schema matches CANONICAL_COLUMNS exactly: PASSED.")

    # Check 2: Row Count Integrity
    print("  [Check 2/5] Verifying total row count (16 zones x 30 dates = 480 rows)...")
    expected_rows = 16 * 30
    if len(df) != expected_rows:
        raise ValueError(f"FATAL: Row count anomaly! Expected {expected_rows} rows, got {len(df)}")
    print(f"    -> Row count is exactly {len(df)} rows: PASSED.")

    # Check 3: Null / NaN Check
    print("  [Check 3/5] Checking for null, NaN, or infinite values across all columns...")
    null_counts = df.isnull().sum()
    if null_counts.any():
        raise ValueError(f"FATAL: Null values detected in final feature table:\n{null_counts}")
    print("    -> Zero null / missing values across all 8 columns: PASSED.")

    # Check 4: Cross-file Zone ID Consistency
    print("  [Check 4/5] Cross-file zone_id validation (zone_grid.json vs sar_backscatter.csv vs zone_features.csv)...")
    grid_zone_set = set(z["zone_id"] for z in grid_zones)
    sar_zone_set = set(df_sar["zone_id"].unique())
    final_zone_set = set(df["zone_id"].unique())

    if grid_zone_set != sar_zone_set:
        diff_1 = grid_zone_set - sar_zone_set
        diff_2 = sar_zone_set - grid_zone_set
        raise ValueError(f"FATAL: Zone ID mismatch between grid and SAR! Grid only: {diff_1}, SAR only: {diff_2}")

    if grid_zone_set != final_zone_set:
        diff_1 = grid_zone_set - final_zone_set
        diff_2 = final_zone_set - grid_zone_set
        raise ValueError(f"FATAL: Zone ID mismatch between grid and final output! Grid only: {diff_1}, Final only: {diff_2}")

    expected_zone_ids = {f"zone_{i:02d}" for i in range(1, 17)}
    if final_zone_set != expected_zone_ids:
        raise ValueError(f"FATAL: Zone IDs do not match 'zone_01'..'zone_16' format: {final_zone_set}")

    print(f"    -> 16/16 Zone IDs perfectly consistent across all inputs and output: PASSED.")

    # Check 5: Numeric Range and Summary Statistics
    print("  [Check 5/5] Summary statistics and geotechnical range verification:")
    numeric_cols = ["slope", "aspect", "curvature", "vv_backscatter", "vh_backscatter", "rainfall_mm"]
    stats_df = df[numeric_cols].describe().T[["min", "mean", "max", "std"]]
    print(f"\n{stats_df.to_string()}\n")

    # Geotechnical bounds sanity
    if (df["slope"] < 0.0).any() or (df["slope"] > 90.0).any():
        raise ValueError("FATAL: Slope values out of physical bounds [0, 90] degrees.")
    if (df["aspect"] < 0.0).any() or (df["aspect"] >= 360.0).any():
        raise ValueError("FATAL: Aspect values out of physical bounds [0, 360) degrees.")
    if (df["vv_backscatter"] > 5.0).any() or (df["vv_backscatter"] < -40.0).any():
        raise ValueError("FATAL: VV backscatter out of typical SAR radar bounds [-40, 5] dB.")
    if (df["vh_backscatter"] > 5.0).any() or (df["vh_backscatter"] < -40.0).any():
        raise ValueError("FATAL: VH backscatter out of typical SAR radar bounds [-40, 5] dB.")
    if (df["rainfall_mm"] < 0.0).any():
        raise ValueError("FATAL: Negative rainfall values detected.")

    print("    -> All numeric features within physical and geotechnical bounds: PASSED.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 6 — Zone Feature Table Assembly Pipeline (SIH25071)"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Run validation checks on existing data/zone_features.csv without regenerating.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ZONE_FEATURES_CSV_PATH,
        help=f"Target output CSV path (default: {ZONE_FEATURES_CSV_PATH})",
    )
    args = parser.parse_args()

    start_time = time.time()
    print("=" * 80)
    print("SIH25071: PHASE 6 — ZONE FEATURE TABLE ASSEMBLY PIPELINE")
    print("=" * 80)

    # 1. Load zone grid
    grid_data = load_zone_grid(ZONE_GRID_PATH)
    zones = grid_data["zones"]

    # 2. Load SAR backscatter
    df_sar = load_sar_backscatter(SAR_CSV_PATH)

    # 3. Load Rainfall
    df_rain = load_rainfall(RAINFALL_CSV_PATH)

    if args.check_only:
        print(f"\n[Running in --check-only mode on {args.output}]")
        if not args.output.exists():
            raise FileNotFoundError(f"Cannot check non-existent file: {args.output}")
        df_final = pd.read_csv(args.output)
        validate_and_sanity_check(df_final, zones, df_sar)
        print(f"\n[DONE ✅] Validation passed for {args.output} in {time.time() - start_time:.2f}s.")
        return

    # 4. Compute zone-level terrain statistics from Phase 3 rasters
    zone_terrain_stats = compute_zone_terrain_statistics(
        zones=zones,
        slope_path=SLOPE_RASTER_PATH,
        aspect_path=ASPECT_RASTER_PATH,
        curvature_path=CURVATURE_RASTER_PATH,
    )

    # 5. Assemble final multi-source feature table
    df_final = assemble_zone_feature_table(
        zone_terrain_stats=zone_terrain_stats,
        df_sar=df_sar,
        df_rain=df_rain,
    )

    # 6. Validate and sanity check
    validate_and_sanity_check(df_final, zones, df_sar)

    # 7. Write to CSV
    print(f"\nWriting finalized zone feature table to {args.output}...")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df_final.to_csv(args.output, index=False)
    file_size_kb = args.output.stat().st_size / 1024.0
    print(f"  -> Successfully written: {args.output} ({file_size_kb:.2f} KB, {len(df_final)} rows)")

    # 8. Print sample rows
    print("\nSample Output (First 5 and Last 5 rows):")
    print(pd.concat([df_final.head(5), df_final.tail(5)]).to_string(index=False))

    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print(f"[DONE ✅] Phase 6 Zone Feature Table Assembly completed successfully in {elapsed:.2f}s.")
    print("=" * 80)


if __name__ == "__main__":
    main()
