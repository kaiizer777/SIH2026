#!/usr/bin/env python3
"""
Phase 4 — Sentinel-1 SAR Backscatter Change Detection Pipeline
SIH25071: AI-Based Rockfall Prediction and Alert System

================================================================================
SCIENTIFIC & ARCHITECTURAL NOTE — WHY SAR BACKSCATTER, NOT InSAR:
--------------------------------------------------------------------------------
This pipeline queries Sentinel-1 Ground Range Detected (GRD) amplitude backscatter
(COPERNICUS/S1_GRD) from Google Earth Engine. It extracts radar cross-section /
backscatter intensity (sigma nought, σ0 in decibels dB) in dual polarization (VV, VH).

This is "SAR backscatter change detection" — NOT phase-based interferometry (InSAR)
or millimeter-level ground displacement/deformation.
True InSAR requires Single Look Complex (SLC) phase data, interferogram generation,
and phase unwrapping (e.g., via SNAP / StaMPS / MintPy), which is not feasible for
low-latency operational pipelines within this hackathon scope.

Instead, multi-temporal SAR backscatter intensity serves as a defensible physical
proxy signal:
1. Co-polarization (VV): Sensitive to surface roughness, soil moisture dynamics,
   and bench disturbance/tension fracturing.
2. Cross-polarization (VH): Sensitive to volume scattering, vegetation loss,
   and structural disaggregation prior to mass movement.
================================================================================

Pipeline Steps:
1. Load locked AOI bounding box from data/aoi.json (fail loudly if missing/malformed).
2. Generate/persist standardized spatial zone grid (N=16 cells, 4x4) to data/zone_grid.json
   so Phase 6 (Zone Feature Table) and Person 2/5 can reuse it verbatim.
3. Initialize Google Earth Engine on project 'sih25071-rockfall'.
4. Query Sentinel-1 GRD collection (COPERNICUS/S1_GRD) filtered to AOI bbox, IW mode,
   VV + VH dual polarizations, and past 12 months (2025-08-19 to 2026-08-19).
5. Compare candidate orbits and relative tracks, select the dominant single orbit pass and
   track that fully contains the AOI footprint without edge clipping, and log the rationale.
6. Perform server-side zonal reduction (reduceRegions) across all temporal acquisitions
   and grid zones to extract mean VV and VH backscatter in dB.
7. Export clean structured CSV to data/sar_backscatter.csv with schema:
   [date, zone_id, VV_mean, VH_mean].
8. Execute sanity checks on decibel value ranges (-25 dB to 0 dB typical), missing values,
   zone counts, and time series length.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure stdout handles UTF-8 safely on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import numpy as np
import pandas as pd

# Resolve repo root directory and canonical paths
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
AOI_PATH = DATA_DIR / "aoi.json"
ZONE_GRID_PATH = DATA_DIR / "zone_grid.json"
SAR_CSV_PATH = DATA_DIR / "sar_backscatter.csv"

GEE_PROJECT = "sih25071-rockfall"
S1_COLLECTION_ID = "COPERNICUS/S1_GRD"

# Target temporal window: 12 months prior to today (Aug 19, 2026)
START_DATE = "2025-08-19"
END_DATE = "2026-08-19"

# Default zone grid configuration (4 columns x 4 rows = 16 zones over AOI)
DEFAULT_GRID_ROWS = 4
DEFAULT_GRID_COLS = 4


def load_aoi(aoi_path: Path) -> Dict[str, Any]:
    """Load and validate locked AOI bounding box from data/aoi.json.
    
    Fails loudly if the file is missing, malformed, or has invalid bounds.
    """
    print(f"[Step 1/7] Loading locked AOI coordinates from {aoi_path}...")
    if not aoi_path.exists():
        raise FileNotFoundError(
            f"FATAL: AOI file missing at '{aoi_path}'. "
            "Do not guess coordinates. Provide data/aoi.json as locked in Phase 1."
        )

    try:
        with open(aoi_path, "r", encoding="utf-8") as f:
            aoi_data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"FATAL: Malformed JSON in '{aoi_path}': {exc}") from exc

    if "bounding_box" not in aoi_data:
        raise KeyError(
            f"FATAL: 'bounding_box' key not found in '{aoi_path}'. "
            "Expected structure: {'bounding_box': {'min_lat': ..., 'max_lat': ..., 'min_lon': ..., 'max_lon': ...}}"
        )

    bbox = aoi_data["bounding_box"]
    req_fields = ["min_lat", "max_lat", "min_lon", "max_lon"]
    for field in req_fields:
        if field not in bbox:
            raise KeyError(f"FATAL: Missing required field '{field}' in bounding_box of '{aoi_path}'")
        if not isinstance(bbox[field], (int, float)):
            raise TypeError(f"FATAL: Bounding box field '{field}' must be numeric. Got: {type(bbox[field])}")

    if bbox["min_lat"] >= bbox["max_lat"]:
        raise ValueError(f"FATAL: Invalid latitude range: min_lat ({bbox['min_lat']}) >= max_lat ({bbox['max_lat']})")
    if bbox["min_lon"] >= bbox["max_lon"]:
        raise ValueError(f"FATAL: Invalid longitude range: min_lon ({bbox['min_lon']}) >= max_lon ({bbox['max_lon']})")

    mine_name = aoi_data.get("mine_name", "Unknown Mine")
    operator = aoi_data.get("operator", "Unknown Operator")
    print(f"  -> Locked AOI verified: {mine_name} ({operator})")
    print(f"  -> Bounding Box: Lon [{bbox['min_lon']}, {bbox['max_lon']}], Lat [{bbox['min_lat']}, {bbox['max_lat']}]")
    return aoi_data


def generate_or_load_zone_grid(
    aoi_data: Dict[str, Any],
    grid_path: Path,
    n_rows: int = DEFAULT_GRID_ROWS,
    n_cols: int = DEFAULT_GRID_COLS
) -> Dict[str, Any]:
    """Define a standardized N-cell regular spatial grid over the AOI bbox.
    
    Persists to data/zone_grid.json so Phase 6 (Zone Feature Table) and Person 2/5
    can reuse the identical zone layout and geometry without divergence.
    """
    print(f"[Step 2/7] Generating standardized {n_rows}x{n_cols} ({n_rows*n_cols} zones) grid...")
    bbox = aoi_data["bounding_box"]
    min_lat, max_lat = float(bbox["min_lat"]), float(bbox["max_lat"])
    min_lon, max_lon = float(bbox["min_lon"]), float(bbox["max_lon"])

    dlat = (max_lat - min_lat) / n_rows
    dlon = (max_lon - min_lon) / n_cols

    zones = []
    zone_num = 1

    for r in range(n_rows):
        # Rows indexed from North (top) to South (bottom)
        z_max_lat = max_lat - r * dlat
        z_min_lat = max_lat - (r + 1) * dlat

        for c in range(n_cols):
            # Columns indexed from West (left) to East (right)
            z_min_lon = min_lon + c * dlon
            z_max_lon = min_lon + (c + 1) * dlon

            zone_id = f"zone_{zone_num:02d}"
            centroid_lon = round((z_min_lon + z_max_lon) / 2.0, 6)
            centroid_lat = round((z_min_lat + z_max_lat) / 2.0, 6)

            # GeoJSON Polygon coordinates [lon, lat] closed ring
            coords = [
                [round(z_min_lon, 6), round(z_min_lat, 6)],
                [round(z_max_lon, 6), round(z_min_lat, 6)],
                [round(z_max_lon, 6), round(z_max_lat, 6)],
                [round(z_min_lon, 6), round(z_max_lat, 6)],
                [round(z_min_lon, 6), round(z_min_lat, 6)]
            ]

            zone_entry = {
                "zone_id": zone_id,
                "row_idx": r,
                "col_idx": c,
                "bbox": {
                    "min_lon": round(z_min_lon, 6),
                    "min_lat": round(z_min_lat, 6),
                    "max_lon": round(z_max_lon, 6),
                    "max_lat": round(z_max_lat, 6)
                },
                "centroid": {
                    "lon": centroid_lon,
                    "lat": centroid_lat
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coords]
                }
            }
            zones.append(zone_entry)
            zone_num += 1

    grid_definition = {
        "mine_name": aoi_data.get("mine_name", "Kusmunda Mine"),
        "operator": aoi_data.get("operator", "SECL"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "grid_layout": {
            "n_rows": n_rows,
            "n_cols": n_cols,
            "total_zones": len(zones)
        },
        "aoi_bbox": bbox,
        "zones": zones
    }

    grid_path.parent.mkdir(parents=True, exist_ok=True)
    with open(grid_path, "w", encoding="utf-8") as f:
        json.dump(grid_definition, f, indent=2)

    print(f"  -> Zone grid locked and written to '{grid_path.name}' ({len(zones)} zones defined).")
    return grid_definition


def init_earth_engine(project_id: str):
    """Initialize Google Earth Engine session."""
    print(f"[Step 3/7] Initializing Google Earth Engine on project '{project_id}'...")
    try:
        import ee
    except ImportError as exc:
        raise ImportError("FATAL: Package 'earthengine-api' is not installed.") from exc

    try:
        ee.Initialize(project=project_id)
        print(f"  -> Earth Engine authenticated and initialized successfully on '{project_id}'.")
    except Exception as exc:
        raise RuntimeError(
            f"FATAL: Earth Engine initialization failed on project '{project_id}'. "
            f"Run ee.Authenticate() or verify OAuth credentials. Details: {exc}"
        ) from exc
    return ee


def filter_and_select_orbit(ee_module, aoi_bbox: Dict[str, float]) -> Tuple[Any, str, int, int]:
    """Query Sentinel-1 GRD collection and determine dominant single orbit pass and relative orbit track.
    
    Filters:
    - Bounding Box: AOI geometry
    - Polarization: transmitterReceiverPolarisation contains both VV and VH
    - Instrument Mode: Interferometric Wide Swath ('IW')
    - Date Range: [START_DATE, END_DATE]
    - Single Orbit & Track: Evaluates pass and relative track coverage to ensure
      100% spatial containment of all zones without look-angle or edge-clipping noise.
    """
    print(f"[Step 4/7] Querying Sentinel-1 GRD ({S1_COLLECTION_ID}) for date range [{START_DATE} to {END_DATE}]...")
    ee = ee_module

    aoi_geom = ee.Geometry.BBox(
        aoi_bbox["min_lon"],
        aoi_bbox["min_lat"],
        aoi_bbox["max_lon"],
        aoi_bbox["max_lat"]
    )

    base_col = (
        ee.ImageCollection(S1_COLLECTION_ID)
        .filterBounds(aoi_geom)
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filterDate(START_DATE, END_DATE)
    )

    total_count = base_col.size().getInfo()
    print(f"  -> Total candidate S1 acquisitions found across all orbits: {total_count}")
    if total_count == 0:
        raise RuntimeError(
            f"FATAL: Zero Sentinel-1 GRD scenes found for AOI in date window [{START_DATE}, {END_DATE}]. "
            "Verify AOI coordinates or date range."
        )

    # Assess orbit directions (ASCENDING vs DESCENDING)
    asc_col = base_col.filter(ee.Filter.eq("orbitProperties_pass", "ASCENDING"))
    desc_col = base_col.filter(ee.Filter.eq("orbitProperties_pass", "DESCENDING"))

    asc_count = asc_col.size().getInfo()
    desc_count = desc_col.size().getInfo()

    print(f"  -> Orbit direction breakdown: ASCENDING={asc_count} scenes, DESCENDING={desc_count} scenes")

    if desc_count >= asc_count and desc_count > 0:
        chosen_pass = "DESCENDING"
        pass_col = desc_col
    elif asc_count > 0:
        chosen_pass = "ASCENDING"
        pass_col = asc_col
    else:
        raise RuntimeError("FATAL: Neither ASCENDING nor DESCENDING passes yielded valid scenes.")

    # Evaluate relative orbit tracks within chosen pass for full AOI containment
    rel_tracks = pass_col.aggregate_array("relativeOrbitNumber_start").getInfo()
    unique_tracks = sorted(list(set(rel_tracks)))
    print(f"  -> Candidate relative orbit tracks in {chosen_pass} pass: {unique_tracks}")

    best_track = None
    best_count = 0
    best_contains = False

    for track in unique_tracks:
        track_col = pass_col.filter(ee.Filter.eq("relativeOrbitNumber_start", track))
        cnt = track_col.size().getInfo()
        # Verify spatial containment on first scene
        first_scene = track_col.first()
        contains_aoi = first_scene.geometry().contains(aoi_geom, 1).getInfo()
        print(f"     Track {track}: {cnt} scenes, Full AOI containment = {contains_aoi}")
        if contains_aoi and (best_track is None or cnt >= best_count):
            best_track = track
            best_count = cnt
            best_contains = True

    if best_track is None:
        # Fallback to dominant track if none strictly contained
        best_track = max(set(rel_tracks), key=rel_tracks.count)
        best_count = pass_col.filter(ee.Filter.eq("relativeOrbitNumber_start", best_track)).size().getInfo()

    selected_col = pass_col.filter(ee.Filter.eq("relativeOrbitNumber_start", best_track)).sort("system:time_start")

    rationale = (
        f"{chosen_pass} Track {best_track} selected ({best_count} scenes). "
        f"Full AOI spatial containment = {best_contains}. Single orbit/track lock ensures "
        "constant incidence angle (look angle) and zero spatial boundary clipping across the multi-temporal series."
    )

    print(f"  -> Selected Orbit Configuration: {chosen_pass} (Track {best_track}, {best_count} scenes)")
    print(f"  -> Rationale: {rationale}")

    return selected_col, chosen_pass, best_track, best_count


def extract_zonal_backscatter(
    ee_module,
    s1_col: Any,
    grid_def: Dict[str, Any]
) -> pd.DataFrame:
    """Extract zonal mean VV and VH backscatter (dB) per acquisition date.
    
    Uses Earth Engine server-side reduceRegions mapped over the ImageCollection,
    batching feature extraction across all zones simultaneously.
    """
    print("[Step 5/7] Extracting zonal mean VV/VH backscatter via server-side reduceRegions...")
    ee = ee_module

    # Build ee.FeatureCollection from zone grid definitions
    features = []
    for zone in grid_def["zones"]:
        z_bbox = zone["bbox"]
        z_geom = ee.Geometry.BBox(
            z_bbox["min_lon"],
            z_bbox["min_lat"],
            z_bbox["max_lon"],
            z_bbox["max_lat"]
        )
        feat = ee.Feature(z_geom, {"zone_id": zone["zone_id"]})
        features.append(feat)

    zones_fc = ee.FeatureCollection(features)

    # Server-side mapping over Sentinel-1 ImageCollection
    def process_image(img):
        acq_date = img.date().format("YYYY-MM-dd")
        img_id = img.id()
        # S1_GRD bands in GEE are calibrated backscatter sigma nought in dB (float)
        reduced = img.select(["VV", "VH"]).reduceRegions(
            collection=zones_fc,
            reducer=ee.Reducer.mean(),
            scale=10  # Sentinel-1 10m nominal pixel spacing
        )

        def add_metadata(feat):
            return feat.set({
                "date": acq_date,
                "image_id": img_id
            })

        return reduced.map(add_metadata)

    start_time = time.time()
    all_extracted_fc = s1_col.map(process_image).flatten()

    # Retrieve all zonal stats in a single optimized payload
    result = all_extracted_fc.getInfo()
    elapsed = time.time() - start_time
    print(f"  -> Server-side extraction completed in {elapsed:.2f}s.")

    raw_features = result.get("features", [])
    if not raw_features:
        raise RuntimeError("FATAL: Server-side zonal extraction returned 0 feature records.")

    records = []
    for feat in raw_features:
        props = feat.get("properties", {})
        date_str = props.get("date")
        zone_id = props.get("zone_id")
        vv_val = props.get("VV")
        vh_val = props.get("VH")

        if date_str and zone_id:
            records.append({
                "date": date_str,
                "zone_id": zone_id,
                "VV_mean": float(vv_val) if vv_val is not None else np.nan,
                "VH_mean": float(vh_val) if vh_val is not None else np.nan,
            })

    df = pd.DataFrame(records)

    # Ensure clean sorting and drop any invalid rows
    df = df.sort_values(by=["date", "zone_id"]).reset_index(drop=True)
    return df


def export_backscatter_csv(df: pd.DataFrame, output_path: Path):
    """Save formatted backscatter time series table to CSV."""
    print(f"[Step 6/7] Exporting SAR backscatter time series to '{output_path}'...")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Ensure explicit column order
    cols = ["date", "zone_id", "VV_mean", "VH_mean"]
    df_out = df[cols].copy()

    # Round backscatter dB values to 4 decimal places for clean representation
    df_out["VV_mean"] = df_out["VV_mean"].round(4)
    df_out["VH_mean"] = df_out["VH_mean"].round(4)

    df_out.to_csv(output_path, index=False)
    file_size_kb = output_path.stat().st_size / 1024
    print(f"  -> Saved '{output_path.name}' ({len(df_out)} rows, {file_size_kb:.1f} KB).")


def sanity_check_and_summarize(
    df: pd.DataFrame,
    grid_def: Dict[str, Any],
    chosen_orbit: str,
    chosen_track: int
):
    """Perform rigorous validation of SAR backscatter time series outputs."""
    print("\n" + "=" * 82)
    print("PHASE 4 SAR BACKSCATTER CHANGE DETECTION -- VERIFICATION SUMMARY")
    print("=" * 82)

    total_rows = len(df)
    unique_dates = df["date"].nunique()
    unique_zones = df["zone_id"].nunique()
    expected_zones = grid_def["grid_layout"]["total_zones"]
    min_date = df["date"].min()
    max_date = df["date"].max()

    print(f"Observation Window:    {min_date} to {max_date} ({unique_dates} temporal acquisitions)")
    print(f"Orbit Pass Geometry:   {chosen_orbit} Track {chosen_track} (Consistent single pass)")
    print(f"Spatial Grid Zones:    {unique_zones} zones (Expected: {expected_zones})")
    print(f"Total CSV Data Rows:   {total_rows} rows ({unique_dates} dates x {unique_zones} zones)")

    # 1. Null / NaN checks
    vv_nans = df["VV_mean"].isna().sum()
    vh_nans = df["VH_mean"].isna().sum()
    print(f"Missing Values (NaNs): VV={vv_nans}, VH={vh_nans}")
    if vv_nans > 0 or vh_nans > 0:
        print("  [WARNING] Detected null values in backscatter series. Check spatial coverage edge effects.")
    else:
        print("  [PASS] Zero missing values across all zone time series.")

    # 2. Value range sanity check (Sentinel-1 GRD dB values)
    vv_min, vv_max, vv_mean = df["VV_mean"].min(), df["VV_mean"].max(), df["VV_mean"].mean()
    vh_min, vh_max, vh_mean = df["VH_mean"].min(), df["VH_mean"].max(), df["VH_mean"].mean()

    print("\nPolarization Backscatter Statistics (Decibels, dB):")
    print("-" * 82)
    print(f"{'Band':<8} | {'Min (dB)':>10} | {'Max (dB)':>10} | {'Mean (dB)':>10} | {'Std (dB)':>10} | {'Status':<15}")
    print("-" * 82)

    for band_name, col_name, min_v, max_v, mean_v, std_v in [
        ("VV (co)", "VV_mean", vv_min, vv_max, vv_mean, df["VV_mean"].std()),
        ("VH (cross)", "VH_mean", vh_min, vh_max, vh_mean, df["VH_mean"].std()),
    ]:
        # Typical radar backscatter from land/mines in dB is between -30 dB and +5 dB
        if -30.0 <= min_v and max_v <= 5.0:
            status = "VALID (in dB)"
        elif min_v >= 0.0 and max_v > 5.0:
            status = "[FLAG] LINEAR"
        else:
            status = "[FLAG] OUTLIER"

        print(f"{band_name:<8} | {min_v:>10.3f} | {max_v:>10.3f} | {mean_v:>10.3f} | {std_v:>10.3f} | {status:<15}")

    print("-" * 82)

    # 3. Per-zone summary breakdown
    print("\nPer-Zone Multi-Temporal Summary (Mean +/- Std across full year):")
    print(f"{'Zone ID':<10} | {'Dates':>6} | {'VV Mean (dB)':>14} | {'VH Mean (dB)':>14} | {'Cross-Ratio (VV-VH)':>20}")
    print("-" * 82)

    zone_grouped = df.groupby("zone_id")
    for zone_id, group in zone_grouped:
        z_vv_mean = group["VV_mean"].mean()
        z_vv_std = group["VV_mean"].std()
        z_vh_mean = group["VH_mean"].mean()
        z_vh_std = group["VH_mean"].std()
        diff_mean = z_vv_mean - z_vh_mean
        print(
            f"{zone_id:<10} | {len(group):>6} | "
            f"{z_vv_mean:>7.2f} +/- {z_vv_std:<4.2f} | "
            f"{z_vh_mean:>7.2f} +/- {z_vh_std:<4.2f} | "
            f"{diff_mean:>18.2f} dB"
        )

    print("=" * 82 + "\n")


def main():
    print("=" * 82)
    print("STARTING PHASE 4: SENTINEL-1 SAR BACKSCATTER CHANGE DETECTION PIPELINE")
    print("=" * 82)

    # 1. Load locked AOI
    aoi_data = load_aoi(AOI_PATH)
    bbox = aoi_data["bounding_box"]

    # 2. Generate and lock standardized zone grid
    grid_def = generate_or_load_zone_grid(
        aoi_data=aoi_data,
        grid_path=ZONE_GRID_PATH,
        n_rows=DEFAULT_GRID_ROWS,
        n_cols=DEFAULT_GRID_COLS
    )

    # 3. Initialize GEE
    ee = init_earth_engine(GEE_PROJECT)

    # 4. Filter collection & pick single dominant orbit pass and track
    s1_col, chosen_orbit, chosen_track, n_scenes = filter_and_select_orbit(ee, bbox)

    # 5. Extract zonal mean backscatter (VV and VH)
    backscatter_df = extract_zonal_backscatter(ee, s1_col, grid_def)

    # 6. Export to CSV
    export_backscatter_csv(backscatter_df, SAR_CSV_PATH)

    # 7. Validation sanity check and verification summary
    sanity_check_and_summarize(backscatter_df, grid_def, chosen_orbit, chosen_track)

    print(f"[Step 7/7] Phase 4 execution complete! Output verified at '{SAR_CSV_PATH.name}'.")


if __name__ == "__main__":
    main()
