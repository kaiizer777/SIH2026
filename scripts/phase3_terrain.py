#!/usr/bin/env python3
"""
Phase 3 — DEM Pull + Terrain Derivatives Pipeline
SIH25071: AI-Based Rockfall Prediction and Alert System

Pipeline Steps:
1. Load locked AOI bounding box from data/aoi.json (fail loudly if missing/malformed).
2. Initialize Google Earth Engine and fetch Copernicus GLO-30 DEM (projects/sat-io/open-datasets/GLO-30).
3. Export clipped 30m DEM GeoTIFF to data/dem.tif.
4. Load DEM with rasterio and wrap in richdem rdarray.
5. Compute terrain derivatives using richdem.TerrainAttribute:
   - slope_degrees (Horn 1981: standard geotechnical slope angle in degrees [0, 90])
   - aspect (azimuth in degrees [0, 360])
   - profile_curvature (Zevenbergen & Thorne 1987: flow-acceleration failure surface indicator)
6. Export derived rasters to data/slope.tif, data/aspect.tif, data/curvature.tif with matching CRS/transform.
7. Generate a 2x2 matplotlib visual sanity check saved as data/terrain_sanity_check.png.
8. Output array shapes, CRS, and resolution verification stats.
"""

import json
import os
import sys
import time
from pathlib import Path
import numpy as np

# Resolve repo root directory
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
AOI_PATH = DATA_DIR / "aoi.json"
DEM_PATH = DATA_DIR / "dem.tif"
SLOPE_PATH = DATA_DIR / "slope.tif"
ASPECT_PATH = DATA_DIR / "aspect.tif"
CURVATURE_PATH = DATA_DIR / "curvature.tif"
SANITY_PLOT_PATH = DATA_DIR / "terrain_sanity_check.png"

GEE_PROJECT = "sih25071-rockfall"
DEM_COLLECTION_ID = "projects/sat-io/open-datasets/GLO-30"


def load_aoi(aoi_path: Path) -> dict:
    """Load and validate locked AOI bounding box from data/aoi.json."""
    print(f"[Step 1/7] Loading AOI coordinates from {aoi_path}...")
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
            raise TypeError(f"FATAL: Bounding box field '{field}' must be a numeric value. Got: {type(bbox[field])}")

    if bbox["min_lat"] >= bbox["max_lat"]:
        raise ValueError(f"FATAL: Invalid latitude range: min_lat ({bbox['min_lat']}) >= max_lat ({bbox['max_lat']})")
    if bbox["min_lon"] >= bbox["max_lon"]:
        raise ValueError(f"FATAL: Invalid longitude range: min_lon ({bbox['min_lon']}) >= max_lon ({bbox['max_lon']})")

    mine_name = aoi_data.get("mine_name", "Unknown Mine")
    operator = aoi_data.get("operator", "Unknown Operator")
    print(f"  -> Locked AOI verified: {mine_name} ({operator})")
    print(f"  -> Bounding Box: Lon [{bbox['min_lon']}, {bbox['max_lon']}], Lat [{bbox['min_lat']}, {bbox['max_lat']}]")
    return aoi_data


def fetch_and_export_dem(bbox: dict, output_path: Path):
    """Query Earth Engine for Copernicus GLO-30 DEM and export to GeoTIFF."""
    print("[Step 2/7] Initializing Earth Engine and querying Copernicus GLO-30 DEM...")
    try:
        import ee
        import geemap
    except ImportError as exc:
        raise ImportError("FATAL: Required packages 'earthengine-api' or 'geemap' are not installed.") from exc

    try:
        ee.Initialize(project=GEE_PROJECT)
        print(f"  -> Earth Engine initialized successfully on project '{GEE_PROJECT}'.")
    except Exception as exc:
        raise RuntimeError(
            f"FATAL: Failed to initialize Earth Engine for project '{GEE_PROJECT}'. "
            f"Ensure authentication token is valid. Details: {exc}"
        ) from exc

    geom = ee.Geometry.BBox(
        bbox["min_lon"],
        bbox["min_lat"],
        bbox["max_lon"],
        bbox["max_lat"]
    )

    glo30_col = ee.ImageCollection(DEM_COLLECTION_ID).filterBounds(geom)
    tile_count = glo30_col.size().getInfo()
    print(f"  -> GLO-30 DEM collection query returned {tile_count} intersecting tile(s).")
    if tile_count == 0:
        raise RuntimeError(f"FATAL: No GLO-30 DEM tiles found intersecting AOI geometry in '{DEM_COLLECTION_ID}'.")

    # Mosaic tiles, select elevation band 'b1', clip to AOI bounding box
    dem_image = glo30_col.mosaic().clip(geom).select("b1")

    print(f"[Step 3/7] Exporting 30m DEM GeoTIFF to '{output_path}'...")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Use geemap.ee_export_image for direct REST retrieval
    start_time = time.time()
    try:
        geemap.ee_export_image(
            dem_image,
            filename=str(output_path),
            scale=30,
            region=geom,
            crs="EPSG:4326",
            file_per_band=False,
            timeout=300
        )
    except Exception as exc:
        print(f"  -> Direct export warning: {exc}. Attempting batch export polling fallback...")
        task = ee.batch.Export.image.toDrive(
            image=dem_image,
            description="dem_glo30_export",
            folder="earthengine",
            fileNamePrefix="dem",
            scale=30,
            region=geom,
            crs="EPSG:4326"
        )
        task.start()
        print(f"  -> Batch export task started (ID: {task.id}). Polling status...")
        while task.active():
            print(f"     Task status: {task.status().get('state')}... waiting 10s")
            time.sleep(10)
        final_state = task.status().get("state")
        if final_state != "COMPLETED":
            raise RuntimeError(f"FATAL: GEE export task failed with state: {final_state}. Error: {task.status().get('error_message')}")
        print("  -> Batch export completed to Google Drive.")

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise FileNotFoundError(f"FATAL: DEM file was not created or is empty at '{output_path}'")

    elapsed = time.time() - start_time
    print(f"  -> DEM exported successfully ({output_path.stat().st_size / 1024:.1f} KB in {elapsed:.2f}s).")


def compute_terrain_derivatives(dem_path: Path):
    """Load DEM with rasterio, compute slope, aspect, profile curvature via richdem."""
    print(f"[Step 4/7] Loading '{dem_path}' with rasterio & richdem...")
    try:
        import rasterio
        import richdem as rd
    except ImportError as exc:
        raise ImportError("FATAL: Required packages 'rasterio' or 'richdem' are not installed.") from exc

    with rasterio.open(dem_path) as src:
        dem_data = src.read(1)
        profile = src.profile.copy()
        transform = src.transform
        crs = src.crs

    print(f"  -> DEM loaded: Shape={dem_data.shape}, CRS={crs}, Res=({transform.a:.6f}°, {abs(transform.e):.6f}°)")
    print(f"  -> Raw DEM Elevation: min={np.nanmin(dem_data):.2f}m, max={np.nanmax(dem_data):.2f}m")

    # Clean nodata / NaNs
    dem_clean = dem_data.astype(np.float32)
    if np.isnan(dem_clean).any():
        dem_clean = np.nan_to_num(dem_clean, nan=-9999.0)

    # Convert to richdem rdarray
    rd_dem = rd.rdarray(dem_clean, no_data=-9999.0)

    # Set geotransform with 30.0m cell spacing in meters.
    # Because geographic coordinates (EPSG:4326) have degrees as spatial units (~0.00027 deg)
    # while elevation is in meters, richdem needs metric cell sizes (30m) to calculate
    # true gradient dz/dx without distorting slope to ~90 deg.
    rd_dem.geotransform = (transform.c, 30.0, 0.0, transform.f, 0.0, -30.0)

    print("[Step 5/7] Calculating terrain attributes via richdem.TerrainAttribute...")

    # 1. Slope (Degrees)
    # Horn's 1981 method: calculates angle of steepest descent in degrees [0, 90].
    # slope_degrees is chosen over slope_riserun because degree angles directly map
    # to geological friction angles, pit bench safety limits, and slope stability thresholds.
    print("  -> Computing slope (slope_degrees)...")
    slope = rd.TerrainAttribute(rd_dem, attrib="slope_degrees")

    # 2. Aspect (Degrees)
    # Identifies downslope direction [0, 360] clockwise from North (0°=N, 90°=E, 180°=S, 270°=W).
    # Critical for directional structural discontinuity mapping and sun/wind weathering exposure.
    print("  -> Computing aspect...")
    aspect = rd.TerrainAttribute(rd_dem, attrib="aspect")

    # 3. Profile Curvature (1/m)
    # Zevenbergen & Thorne (1987) profile curvature measures rate of change of slope along maximum gradient.
    # Negative curvature = convex (accelerating flow, high tension/shear detachment zones).
    # Positive curvature = concave (decelerating flow, material accumulation/ponding zones).
    # Essential for physical rockfall initiation zone characterization.
    print("  -> Computing profile_curvature...")
    curvature = rd.TerrainAttribute(rd_dem, attrib="profile_curvature")

    # Convert back to standard numpy ndarrays
    slope_arr = np.asarray(slope, dtype=np.float32)
    aspect_arr = np.asarray(aspect, dtype=np.float32)
    curv_arr = np.asarray(curvature, dtype=np.float32)

    return {
        "dem": dem_clean,
        "slope": slope_arr,
        "aspect": aspect_arr,
        "curvature": curv_arr,
        "profile": profile,
        "transform": transform,
        "crs": crs
    }


def save_geotiff(array: np.ndarray, output_path: Path, profile: dict):
    """Save 2D numpy array as GeoTIFF matching input profile."""
    import rasterio

    out_profile = profile.copy()
    out_profile.update({
        "driver": "GTiff",
        "dtype": "float32",
        "count": 1,
        "nodata": -9999.0
    })

    with rasterio.open(output_path, "w", **out_profile) as dst:
        dst.write(array.astype(np.float32), 1)
    print(f"  -> Saved '{output_path.name}' ({output_path.stat().st_size / 1024:.1f} KB)")


def generate_sanity_check_plot(terrain_data: dict, output_path: Path):
    """Generate 2x2 grid sanity-check plot for DEM, slope, aspect, curvature."""
    print(f"[Step 6/7] Generating visual sanity check plot to '{output_path}'...")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise ImportError("FATAL: Package 'matplotlib' is required for sanity check visualization.") from exc

    dem = terrain_data["dem"]
    slope = terrain_data["slope"]
    aspect = terrain_data["aspect"]
    curv = terrain_data["curvature"]

    # Mask nodata values (-9999) for clean visualization
    dem_plot = np.where(dem == -9999.0, np.nan, dem)
    slope_plot = np.where(slope == -9999.0, np.nan, slope)
    aspect_plot = np.where(aspect == -9999.0, np.nan, aspect)
    curv_plot = np.where(curv == -9999.0, np.nan, curv)

    fig, axes = plt.subplots(2, 2, figsize=(14, 11), dpi=300)
    plt.subplots_adjust(wspace=0.25, hspace=0.3)

    # Panel 1: DEM Elevation
    im0 = axes[0, 0].imshow(dem_plot, cmap="terrain", origin="upper")
    axes[0, 0].set_title("Copernicus GLO-30 DEM (Elevation)", fontsize=13, fontweight="bold", pad=8)
    cbar0 = fig.colorbar(im0, ax=axes[0, 0], fraction=0.046, pad=0.04)
    cbar0.set_label("Elevation (m)", fontsize=10)

    # Panel 2: Slope (degrees)
    im1 = axes[0, 1].imshow(slope_plot, cmap="magma", origin="upper", vmin=0, vmax=np.nanpercentile(slope_plot, 99))
    axes[0, 1].set_title("Slope Angle (Horn 1981)", fontsize=13, fontweight="bold", pad=8)
    cbar1 = fig.colorbar(im1, ax=axes[0, 1], fraction=0.046, pad=0.04)
    cbar1.set_label("Slope (degrees)", fontsize=10)

    # Panel 3: Aspect (degrees)
    im2 = axes[0, 2 if False else 0].imshow(aspect_plot, cmap="twilight", origin="upper", vmin=0, vmax=360) # axes[1,0]
    axes[1, 0].clear()
    im2 = axes[1, 0].imshow(aspect_plot, cmap="twilight", origin="upper", vmin=0, vmax=360)
    axes[1, 0].set_title("Aspect (Downslope Azimuth)", fontsize=13, fontweight="bold", pad=8)
    cbar2 = fig.colorbar(im2, ax=axes[1, 0], fraction=0.046, pad=0.04)
    cbar2.set_label("Azimuth (° from North)", fontsize=10)

    # Panel 4: Profile Curvature
    # Center colorbar around 0 for convex vs concave
    vlim = np.nanpercentile(np.abs(curv_plot), 98)
    vlim = max(vlim, 0.1)
    im3 = axes[1, 1].imshow(curv_plot, cmap="coolwarm", origin="upper", vmin=-vlim, vmax=vlim)
    axes[1, 1].set_title("Profile Curvature (Zevenbergen & Thorne)", fontsize=13, fontweight="bold", pad=8)
    cbar3 = fig.colorbar(im3, ax=axes[1, 1], fraction=0.046, pad=0.04)
    cbar3.set_label("Curvature (convex < 0 < concave)", fontsize=10)

    for ax in axes.flat:
        ax.set_xlabel("Pixel X (Columns)", fontsize=9)
        ax.set_ylabel("Pixel Y (Rows)", fontsize=9)
        ax.grid(False)

    fig.suptitle(
        "Kusmunda Mine (SECL) — Phase 3 Terrain Derivatives Sanity Check\n"
        f"Resolution: 30m | Grid: {dem.shape[0]}x{dem.shape[1]} cells | CRS: {terrain_data['crs']}",
        fontsize=14,
        fontweight="bold",
        y=0.98
    )

    plt.savefig(output_path, bbox_inches="tight", dpi=300)
    plt.close(fig)
    print(f"  -> Sanity check plot saved successfully ({output_path.stat().st_size / 1024:.1f} KB)")


def print_verification_summary(terrain_data: dict):
    """Print clean verification summary for eyeball inspection."""
    print("\n" + "=" * 78)
    print("PHASE 3 TERRAIN DERIVATIVES — VERIFICATION SUMMARY")
    print("=" * 78)

    t = terrain_data["transform"]
    crs = terrain_data["crs"]
    shape = terrain_data["dem"].shape

    layers = [
        ("DEM Elevation", terrain_data["dem"], "m"),
        ("Slope", terrain_data["slope"], "degrees"),
        ("Aspect", terrain_data["aspect"], "degrees (0-360)"),
        ("Profile Curvature", terrain_data["curvature"], "1/m")
    ]

    print(f"{'Layer':<20} | {'Shape':<12} | {'Min':>10} | {'Max':>10} | {'Mean':>10} | {'Unit'}")
    print("-" * 78)
    for name, arr, unit in layers:
        valid_mask = arr != -9999.0
        vmin = np.nanmin(arr[valid_mask]) if np.any(valid_mask) else np.nan
        vmax = np.nanmax(arr[valid_mask]) if np.any(valid_mask) else np.nan
        vmean = np.nanmean(arr[valid_mask]) if np.any(valid_mask) else np.nan
        print(f"{name:<20} | {str(shape):<12} | {vmin:>10.3f} | {vmax:>10.3f} | {vmean:>10.3f} | {unit}")

    print("-" * 78)
    print(f"Grid Dimensions: {shape[0]} rows x {shape[1]} cols ({shape[0] * shape[1]} total cells)")
    print(f"Spatial Reference: {crs}")
    print(f"Pixel Resolution: dx={t.a:.6f} deg, dy={abs(t.e):.6f} deg (~30.0m ground resolution)")
    print(f"Origin (Upper-Left): Lon={t.c:.6f}, Lat={t.f:.6f}")
    print("=" * 78 + "\n")


def main():
    print("=" * 78)
    print("STARTING PHASE 3: DEM PULL + TERRAIN DERIVATIVES")
    print("=" * 78)

    # 1. Load locked AOI
    aoi_data = load_aoi(AOI_PATH)
    bbox = aoi_data["bounding_box"]

    # 2 & 3. Export DEM from GEE
    fetch_and_export_dem(bbox, DEM_PATH)

    # 4 & 5. Derive terrain attributes
    terrain_data = compute_terrain_derivatives(DEM_PATH)

    # Save derivative GeoTIFF rasters
    print("[Step 6/7] Saving terrain derivative rasters...")
    save_geotiff(terrain_data["slope"], SLOPE_PATH, terrain_data["profile"])
    save_geotiff(terrain_data["aspect"], ASPECT_PATH, terrain_data["profile"])
    save_geotiff(terrain_data["curvature"], CURVATURE_PATH, terrain_data["profile"])

    # 6. Generate sanity check visualization
    generate_sanity_check_plot(terrain_data, SANITY_PLOT_PATH)

    # 7. Print summary
    print_verification_summary(terrain_data)

    print("[Step 7/7] Phase 3 execution complete! All artifacts generated idempotently.")


if __name__ == "__main__":
    main()
