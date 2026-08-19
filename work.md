# WORK.md — SIH25071 Day 1–2 Execution Plan

Research-verified as of Aug 19, 2026. Two corrections from the original plan are folded in below (flagged ⚠️) — both are defensibility issues a domain-literate judge would catch, so fix now while it's free.

⚠️ **Correction 1 — "InSAR" claim.** `COPERNICUS/S1_GRD` in GEE is **amplitude backscatter**, not phase-based interferometry. True InSAR (mm-level deformation) needs SLC data + SNAP interferometric processing — not feasible in a hackathon window. Reframe as **"SAR backscatter change detection"** — a real, defensible proxy signal (used in flood/landslide change-detection literature), not fabricated precision. Say this explicitly in the pitch; don't let a judge catch it first.

⚠️ **Correction 2 — DEM access shortcut.** GLO-30 is directly queryable **inside GEE** as `projects/sat-io/open-datasets/GLO-30`. Pull DEM and SAR in the *same* authenticated GEE session — skip the separate OpenTopography API key entirely. One less credential, one less thing to break Day 6.

---

## Phase 1 — Mine Site Lockdown (blocks everything else)
**Target: first 30–60 min of Day 1. [DONE ✅]**

- [x] Pick one real Indian open-pit mine (coal or iron ore) — do not proceed to Phase 2 without this
  - [x] Shortlist 2–3 candidates: e.g. Kusmunda (SECL, Chhattisgarh — already your pitch anchor for SSR framing), Gevra (SECL), or an NMDC iron-ore pit in Chhattisgarh/Odisha
  - [x] Confirm lat/lon bounding box (rough pit extent, ~2–5 km²) using Google Maps or OpenStreetMap
  - [x] Write bounding box coordinates into a shared file (`data/aoi.json` or similar) — all downstream scripts read from this, nobody eyeballs coordinates independently
- [x] Confirm the mine choice doesn't conflict with the SSR/Kusmunda pitch framing already locked in CONTEXT.md
- [x] Lock and record the final AOI (area of interest) coordinates — this unblocks the entire Day 1–2 geospatial workflow

---

## Phase 2 — GEE + Cloud Auth Setup
**Target: first hour of Day 1. [DONE ✅]**

- [x] Confirm Google Cloud project registered for Earth Engine (should already be done from Day 0 — verify, don't assume)
  - [x] Run `ee.Authenticate()` once, confirm OAuth completes and token persists locally
  - [x] Run `ee.Initialize(project='sih25071-rockfall')` and confirm no error
  - [x] Sanity check: `print(ee.String('GEE session verified').getInfo())` returns successfully
- [x] Install required Python packages in the geospatial venv/environment
  - [x] `pip install earthengine-api geemap richdem rasterio numpy pandas` (Windows `backend/venv` + WSL `~/geo-env`)
- [x] Confirm `richdem` imports cleanly (`import richdem as rd`) — verified working in WSL2 `~/geo-env` (Python 3.10)

---

## Phase 3 — DEM Pull + Terrain Derivatives
**Target: Day 1, hours 2–4. [DONE ✅]**

- [x] Pull Copernicus GLO-30 DEM for the locked AOI via GEE
  - [x] `ee.ImageCollection("projects/sat-io/open-datasets/GLO-30")`, filtered/clipped to AOI bounding box
  - [x] Export as GeoTIFF (`ee.batch.Export.image.toDrive` or direct `geemap.ee_export_image`) — 30m resolution is fine, don't over-fetch
- [x] Load exported DEM locally with `rasterio`, convert to `richdem` array
  - [x] `rd.rdarray(dem_array, no_data=-9999)`
- [x] Derive terrain attributes with `richdem.TerrainAttribute`
  - [x] Slope (`slope_degrees` — standard geotechnical degree units [0, 90] for friction angles)
  - [x] Aspect (`aspect` [0, 360])
  - [x] Profile curvature (`profile_curvature` — Zevenbergen & Thorne flow-acceleration failure surface indicator)
- [x] Sanity-check outputs visually (quick matplotlib plot of slope/aspect) — verified bench geometry in `data/terrain_sanity_check.png`
- [x] Save DEM-derived rasters to a shared `data/` folder with clear filenames (`dem.tif`, `slope.tif`, `aspect.tif`, `curvature.tif`)

---

## Phase 4 — SAR Backscatter Pull (relabeled from "InSAR")
**Target: Day 1, hours 4–6. [DONE ✅]**

- [x] Pull Sentinel-1 GRD (`COPERNICUS/S1_GRD`) time series for the AOI via GEE
  - [x] Filter: `transmitterReceiverPolarisation` contains VV and VH, `instrumentMode = 'IW'`
  - [x] Filter date range: last 6–12 months for a usable time series (2025-08-19 to 2026-08-19, 30 acquisitions locked)
  - [x] Filter to one consistent orbit direction (`DESCENDING` Track 19 locked for 100% spatial containment)
- [x] Compute per-zone mean VV/VH backscatter per image in the time series via server-side `reduceRegions`
- [x] Export as a simple CSV: `data/sar_backscatter.csv` with columns `date, zone_id, VV_mean, VH_mean`
- [x] Persist standardized 16-zone spatial grid to `data/zone_grid.json` for Phase 6 reuse
- [x] **In all docs/pitch material, label this "SAR backscatter change detection," never "InSAR deformation"** — this is the corrected, defensible framing from the top of this file
- [x] Note in project docs: backscatter changes are a proxy for surface disturbance (moisture, roughness, vegetation loss pre-failure), not direct mm-displacement — this is *fine* to say out loud, it's still real signal

---

## Phase 5 — Rainfall Pull
**Target: Day 1, hour 6–7 (fast, low-risk task). [DONE ✅]**

- [x] Call Open-Meteo Historical Archive API for the AOI center point
  - [x] Endpoint: `https://archive-api.open-meteo.com/v1/archive`
  - [x] Params: `latitude`, `longitude`, `start_date`, `end_date` (matched SAR range 2025-08-22 to 2026-08-12), `daily=precipitation_sum`, `timezone=UTC`
  - [x] Verified unauthenticated request succeeds without API key
- [x] Save as CSV: `data/rainfall.csv` with schema `date, rainfall_mm` (356 continuous daily records)
- [x] Evaluated spatial scale: ERA5-Land reanalysis resolution (~9-11 km) exceeds pit footprint (4.8 km diagonal); 0.0 mm variance across zone centroids confirmed AOI center point query is optimal
- [x] Verified zero missing/null records and exact cross-validation alignment with 30 SAR acquisition dates

---

## Phase 6 — Zone Feature Table Assembly
**Target: Day 1 end / Day 2 start. This is the core geospatial deliverable. [DONE ✅]**

- [x] Define zone grid over the AOI (systematic 4x4 N=16 grid cells locked in `data/zone_grid.json`)
- [x] Assign `zone_id` (`zone_01` to `zone_16`) consistent across all phases and `SensorReading` schema contract
- [x] Compute zone terrain stats via rasterio polygon masking: Horn slope, circular mean aspect (arctan2 sin/cos), Zevenbergen & Thorne profile curvature
- [x] Join multi-temporal Sentinel-1 SAR backscatter (`vv_backscatter`, `vh_backscatter` in dB) and broadcast daily rainfall (`rainfall_mm`)
- [x] Output single clean canonical table in long format (480 rows = 16 zones x 30 dates): `zone_id, date, slope, aspect, curvature, vv_backscatter, vh_backscatter, rainfall_mm`
- [x] Validated schema contract alignment with `backend/app/schemas.py` (`SensorReading.zone_id`), 0 null values, 100% cross-file zone_id consistency
- [x] Saved finalized table to `data/zone_features.csv` and created reproducible script `scripts/phase6_zone_features.py`

---

## Phase 7 — Synthetic Sensor Data Generator (Fukuzono-based)
**Target: Day 1–2 — align directly with Phase 6 `zone_id` scheme. [DONE ✅]**

- [x] Confirm `zone_id` scheme against Phase 6 / `data/zone_grid.json` before writing final generator output (`zone_01` through `zone_16` locked)
- [x] Implement the physics-informed precursor curve based on Fukuzono (1985) inverse-velocity method — confirmed still the standard citable basis, used specifically in open-pit mine failure-time studies
  - [x] Core relation: displacement velocity accelerates approaching failure; **1/velocity trends toward zero** as failure time is approached — this is the citable, non-arbitrary shape to base the curve on
  - [x] For "safe" zones: near-flat/noisy low-velocity displacement, no trend toward failure (0–50 mm/day SSR safe threshold)
  - [x] For "warning" zones: early-stage acceleration visible in the inverse-velocity curve, still far from zero (50–120 mm/day SSR warning threshold)
  - [x] For "evacuation" zones: late-stage acceleration, inverse-velocity curve trending sharply toward zero (>120 mm/day SSR evacuation threshold)
- [x] Generate correlated multi-sensor signals per zone: `displacement_mm_day`, `vibration`, `pore_pressure`, `strain`, `rainfall_mm`
  - [x] Rainfall correlates with pore pressure spikes via antecedent precipitation index (infiltration → pore pressure rise → reduced shear strength) using real `data/rainfall.csv`
  - [x] Vibration (0.01–0.90 g) and strain (50–1600 με) co-vary with creep stages (micro-fracturing acoustic emissions and borehole shear deformation)
- [x] Enforce dual class distributions:
  - [x] **Spatial Zone Risk Tier** (10 Low / 4 Medium / 2 High across 16 zones, 62.5% / 25.0% / 12.5%) based on terrain/SAR susceptibility scoring (inherent geological hazard)
  - [x] **Dynamic Row-Level Observed Risk State** (**60.13% Safe [3,425 rows] / 24.98% Warning [1,423 rows] / 14.89% Evacuation [848 rows]** across all 5,696 daily records) strictly derived from each observation's actual `displacement_mm_day` against grounded SSR thresholds (<50 Safe, 50-120 Warning, >120 Evacuation)
- [x] Output strictly matches `SensorReading` schema from Day 0 (`sensor_id`, `zone_id`, `timestamp`, `displacement_mm_day`, `vibration`, `pore_pressure`, `strain`, `rainfall_mm`, `risk_level`) — validated 100% (5,696/5,696 rows) against `backend/app/schemas.py` directly
- [x] Sanity-check against real calibration datasets (Landslide4Sense, NASA Global Landslide Catalog, Dorren et al., Rose & Hungr 2007) — confirmed displacement, pore-pressure, vibration, and strain magnitudes are grounded in literature
- [x] Saved generator output to `data/synthetic_sensors.csv` (5,696 rows, 16 zones x 356 days) and created reproducible script `scripts/phase7_synthetic_sensors.py`

---

## Phase 8 — Backend Mock Stability Check
**Target: Day 1–2, low-effort — most of this is already done from Day 0.**

- [ ] Confirm mock `/predict` endpoint still returns schema-valid `RiskPrediction` objects (60/25/15 weighted) — quick smoke test, not a rebuild
- [ ] Confirm mock WebSocket `/ws/feed` is still broadcasting correctly to a test client
- [ ] If the Phase 6 `zone_id` scheme differs from whatever placeholder was used in the mock backend, update the mock's zone list now — cheap fix today, expensive fix Day 6
- [ ] No new feature work here — Day 1–2 backend focus is about staying stable and unblocking frontend development, not building the real model integration yet (that's Day 4–6)

---

## Phase 9 — End-of-Day-2 Review Checklist
**Target: end of Day 2, 15–20 min self-review.**

- [ ] Review `data/zone_features.csv` — confirm column names match what ML baseline training will expect for features
- [ ] Review synthetic sensor dataset (`data/synthetic_sensors.csv`) — confirm schema compliance against `backend/app/schemas.py`, confirm class balance landed near 60/25/15
- [ ] Confirm mock backend is untouched/stable, ready for frontend dashboard to keep building against
- [ ] Explicitly verify zero schema drift — confirm any schema modifications are reflected across both backend and frontend schemas
- [ ] Confirm unblocked state for Day 2–4 (ML baseline training and frontend dashboard build)

---

## Notes for the pitch deck (carry forward, don't lose these)
- SAR backscatter change detection, not InSAR deformation — say this proactively, it reads as rigor, not a gap
- Rainfall → pore pressure correlation in the synthetic generator is physically grounded (infiltration mechanics), not decorative — usable as a SHAP talking point later
- Fukuzono inverse-velocity method is peer-reviewed and specifically validated on open-pit mine slope failures (not just natural landslides) — strong citation, use it by name in the deck