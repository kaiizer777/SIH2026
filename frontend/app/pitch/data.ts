// ============================================================================
// SIH 2026 — Pitch Companion Master Knowledge Base
// All Q&A, flashcards, benchmark numbers, and glossary terms embedded
// directly so the page is 100% self-contained.
// ============================================================================

export type PitchItem = {
  q: string;
  short: string;          // 10-second executive summary
  full: string;           // full defensible answer
  plain?: string;         // non-tech translation (optional)
  tags?: string[];        // for search/filter
};

export type Flashcard = {
  q: string;
  trap: string;           // what NEVER to say
  counter: string;        // winning counter-punch
  doNotSay?: string[];    // explicit "do not say" badges
};

export type BenchmarkModel = {
  name: string;
  precision: number;      // 0..1
  recall: number;         // 0..1
  f1: number;             // 0..1
  missed: number;         // missed evacuations out of 197
  totalEvac: number;      // 197
  note: string;           // short takeaway
  tone: 'champion' | 'strong' | 'benchmark';
};

// ----------------------------------------------------------------------------
// Section 01 — Problem & Market Deep-Dive
// ----------------------------------------------------------------------------
export const section01: PitchItem[] = [
  {
    q: 'What is rockfall and why is it lethal?',
    short: 'Bench detachment from 60–75° faces, stable for weeks, fails in minutes. Haul truck and shovel operators have zero physical shield.',
    full: 'A rockfall is the detachment and downhill trajectory of a mass of rock from a highwall bench. Open-pit benches in mines like Kusmunda sit at 60–75° face angles and heights of 10–15 m. The bench can appear visually stable for weeks, then fail catastrophically within minutes. The exposed workforce — uncovered haul-truck and hydraulic-shovel operators — has no protective canopy, so a single 200 kg block falling 12 m is fatal. This is the dominant lethal failure mode in Indian opencast coal mining.',
    plain: 'Imagine a vertical wall of loose rock 4 stories tall that looks fine for weeks, then suddenly gives way in under a minute onto the truck driving below it.',
    tags: ['problem', 'safety', 'bench'],
  },
  {
    q: 'Why Kusmunda Mine (SECL) as the anchor?',
    short: 'One of India\u2019s largest opencast coal mines in Korba Coalfield. Benches >200 m deep, >150 Mt/year output, documented geotechnical challenges.',
    full: 'Kusmunda is operated by South Eastern Coalfields Limited (SECL) under Coal India Limited, located in the Korba Coalfield, Chhattisgarh. It is one of the largest opencast coal mines in India, producing over 150 million tonnes annually with benches exceeding 200 m depth. It is a real, high-throughput mine with documented slope instability history. Anchoring the PoC to Kusmunda gives judges a concrete site, not a toy example.',
    plain: 'We picked one of the biggest, deepest open-pit coal mines in India so the demo is on a real mine, not a sandbox.',
    tags: ['kusmunda', 'secl', 'site'],
  },
  {
    q: 'What do DGMS statistics show about slope failures?',
    short: 'Slope instability is top-3 fatal cause. Draglines (₹80–120 Cr) and shovels (₹15–30 Cr) routinely damaged. National target 1 Bt drives aggressive deepening.',
    full: 'The Directorate General of Mines Safety (DGMS) annual reports rank slope instability and falls of ground as a top-3 cause of fatalities in Indian opencast mines. Equipment losses are severe: draglines cost ₹80–120 Cr each, hydraulic shovels ₹15–30 Cr, and haul trucks ₹5–10 Cr. The National Coal Linkage Policy target of 1 billion tonnes annually forces mines to deepen aggressively, which geometrically increases slope failure risk.',
    plain: 'Rockslides are one of the top ways miners die in India, and the equipment they destroy costs tens of crores. Mines are also being dug deeper, which makes it worse.',
    tags: ['dgms', 'statistics', 'safety'],
  },
  {
    q: 'What is SSR (Slope Stability Radar)?',
    short: 'Ground-based interferometric radar (IDS GeoRadar, GroundProbe). Sub-mm precision, real-time creep detection. The industry gold standard.',
    full: 'Slope Stability Radar (SSR) is a ground-based interferometric radar system (manufactured by IDS GeoRadar and GroundProbe) that delivers sub-millimetre precision displacement measurements across an entire slope face in real time. The Indonesian coal case study by these vendors established the operating thresholds we adopt: Safe 0–50 mm/day, Warning 50–120 mm/day, Evacuation >120 mm/day.',
    plain: 'A super-precise laser radar that watches an entire rock wall 24/7 and notices it creeping by less than a millimetre.',
    tags: ['ssr', 'radar', 'hardware'],
  },
  {
    q: 'What is the cost barrier with SSR?',
    short: '$250k–$500k (₹2–4 Cr) per unit, plus 10–15% annual maintenance. Kusmunda full perimeter needs 4–6 units (₹12–30 Cr). Hundreds of smaller CIL/private mines cannot afford it.',
    full: 'A single SSR unit costs $250k–$500k (₹2–4 Cr) with 10–15% annual maintenance. Kusmunda would need 4–6 units for full-perimeter coverage, totalling ₹12–30 Cr capex. Hundreds of smaller CIL subsidiaries and private mines cannot afford even one unit, so they fall back on manual walking rounds that have 8-hour blind spots between inspections.',
    plain: 'The best tool costs ₹2–4 Crore per radar, and you need 4–6 of them for one mine. Most mines in India simply can\u2019t afford that.',
    tags: ['cost', 'ssr', 'market'],
  },
  {
    q: 'What is the line-of-sight constraint?',
    short: 'Radar cannot see behind ridges, berms, ramps, or moving haul trucks. Even well-funded mines achieve only 60–80% coverage; 20–40% shadow zones are unmonitored.',
    full: 'Radar is a line-of-sight sensor. A ridge, a haul ramp, or even a moving 200-tonne haul truck blocks the beam. Even well-funded mines with 4–6 SSR units typically achieve only 60–80% geometric coverage. The remaining 20–40% of pit area falls into \u201cshadow zones\u201d with zero instrumentation. Our system is designed specifically to cover those shadow zones through satellite fusion.',
    plain: 'Radar is a straight beam \u2014 it can\u2019t see around corners or behind a parked truck. So even with the best radar you miss 20\u201340% of the pit.',
    tags: ['ssr', 'line-of-sight', 'coverage'],
  },
  {
    q: 'Market size and beneficiaries?',
    short: '200+ opencast coal mines in India. Global $300B surface mining market. Peripheral bench coverage, DGMS regulatory compliance, ₹1 lakh Cr PMKKKY welfare fund.',
    full: 'India has 200+ operating opencast coal mines under CIL and private operators. The global surface mining equipment market exceeds $300B. Beneficiaries include: (1) all CIL subsidiaries needing peripheral bench coverage below SSR, (2) private mines that cannot afford SSR at all, (3) DGMS for regulatory compliance and audit trails, (4) the PMKKKY ₹1 lakh Cr welfare fund for mining-affected communities that benefits indirectly from safer operations.',
    plain: '200+ mines in India alone need this, plus every surface mine in the world. A ₹1 lakh Cr welfare fund is also on the line.',
    tags: ['market', 'business', 'cil'],
  },
  {
    q: 'Fukuzono (1985) Inverse Velocity Method?',
    short: 'Inverse of displacement velocity (1/v) trends linearly to zero as failure nears. Our synthetic data follows this exact power-law curve during Warning/Evacuation periods.',
    full: 'Fukuzono (1985) showed that 1/velocity, plotted against time, trends linearly toward zero as a slope approaches catastrophic failure. At the moment of collapse, velocity diverges and 1/v crosses zero. Our physics-informed synthetic data generator follows this exact power-law during the Warning (50–120 mm/day) and Evacuation (>120 mm/day) periods, so the model learns the correct precursor trajectory, not a random walk.',
    plain: 'As a slope is about to collapse, its speed shoots up. Plot \u201c1 divided by speed\u201d over time and it walks straight toward zero \u2014 that\u2019s the warning sign. Our AI learns this curve.',
    tags: ['fukuzono', 'physics', 'velocity'],
  },
  {
    q: 'Alert velocity thresholds?',
    short: 'Safe 0–50 mm/day | Warning 50–120 mm/day | Evacuation >120 mm/day. Calibrated to Permian coal measures.',
    full: 'Our three-tier alert thresholds are: Safe 0–50 mm/day, Warning 50–120 mm/day, Evacuation >120 mm/day. These match the Indonesian coal case study thresholds published by SSR vendors and are calibrated to Permian coal measure lithologies typical of Indian coalfields.',
    tags: ['threshold', 'alert', 'velocity'],
  },
  {
    q: 'Why do manual methods fail?',
    short: 'Visual rounds have 8-hr latency. Prussik extensometers monitor 2–3 points. Total stations take days/weeks. Slopes can accelerate to failure in <6 hours during monsoon.',
    full: 'Manual visual rounds happen once per shift, so there is an inherent 8-hour blind spot. Prussik extensometers monitor only 2–3 fixed points. Total stations require line-of-sight and manual aiming, taking days to weeks for a full sweep. Critically, slopes can accelerate from Warning to Evacuation in under 6 hours during monsoon, which is faster than any manual cadence can catch.',
    plain: 'Humans walking the wall catch things 8 hours late. By then the rock has already fallen.',
    tags: ['manual', 'failure', 'monsoon'],
  },
  {
    q: 'Ministry of Mines alignment?',
    short: 'SIH25071 issued directly by Ministry of Mines. DGMS progressive mandate for electronic slope monitoring.',
    full: 'Problem Statement SIH25071 was issued directly by the Ministry of Mines for SIH 2026. The DGMS has progressively mandated electronic slope monitoring on larger mines, so our system is built to align with that regulatory direction from day one.',
    tags: ['sih', 'ministry', 'dgms'],
  },
  {
    q: 'Cost of inaction?',
    short: '₹500+ Cr per major slope collapse. Production loss ₹5–15 Cr/day × 30 days = ₹150–450 Cr. Equipment loss ₹50–100 Cr. Plus legal and human cost.',
    full: 'A single major slope collapse costs ₹500+ Cr when you sum: production loss (₹5–15 Cr/day × 30-day shutdown = ₹150–450 Cr), equipment replacement (₹50–100 Cr), legal liability, reputational damage, and \u2014 most importantly \u2014 the human cost which has no price tag. Preventing even one such event per year across 10 mines justifies our entire development effort.',
    plain: 'One rockfall can shut a mine for a month and burn half a billion rupees. Even one prevented incident pays for everything.',
    tags: ['cost', 'risk', 'business'],
  },
  {
    q: 'Is this a complement or replacement for SSR?',
    short: 'Complement, not replacement. Covers the 20–40% radar shadow zones at 5–10% of the cost. Ingests SSR data when available, extends coverage via satellite/sensor fusion when unavailable.',
    full: 'Our system is a complement, not a replacement, for SSR. It covers the 20–40% radar shadow zones at 5–10% of the cost. Where SSR exists, we ingest its displacement stream directly. Where it does not, we extend coverage through Sentinel-1 SAR backscatter, DEM derivatives, and on-site geotech sensors. This makes us a force multiplier for SSR-equipped mines and a standalone solution for the rest.',
    tags: ['ssr', 'complement', 'fusion'],
  },
  {
    q: 'How does this compare to the IEEE hybrid CNN-LSTM paper?',
    short: 'Hybrid CNN-LSTM achieved ~30 min lead time. Our XGBoost/RF achieves 97.98% accuracy and 100% evacuation recall with lower edge-compute overhead and sub-minute real-time WebSocket push.',
    full: 'Recent IEEE work on hybrid CNN-LSTM architectures reports roughly 30-minute lead time before failure on benchmark landslide datasets. Our XGBoost and Random Forest models achieve 97.98% test accuracy and 100% evacuation recall on the Kusmunda zone set, with the inference loop completing in under 2.5 seconds end-to-end. The model also runs on commodity edge hardware (Raspberry Pi / Jetson) via ONNX, which a heavy CNN-LSTM cannot do without a GPU.',
    plain: 'Other AI papers are slow and need GPUs. Ours is faster, more accurate, and runs on a ₹5,000 chip.',
    tags: ['ieee', 'comparison', 'benchmark'],
  },
  {
    q: 'What calibration datasets were used?',
    short: 'Landslide4Sense, NASA Global Landslide Catalog, Dorren et al. (Zenodo), data.gov.in / GSI / DGMS Indian geological parameters.',
    full: 'Our physics and synthetic data calibration draws on: (1) Landslide4Sense multi-modal landslide benchmark, (2) NASA Global Landslide Catalog for event statistics, (3) Dorren et al. published on Zenodo for forest-slope rockfall dynamics, and (4) Indian geological parameters from data.gov.in, GSI, and DGMS publications. Real geospatial inputs (DEM, SAR, rainfall) are sourced directly from ESA Copernicus and ERA5.',
    tags: ['dataset', 'calibration', 'data'],
  },
];

// ----------------------------------------------------------------------------
// Section 02 — Technical Architecture
// ----------------------------------------------------------------------------
export const section02: PitchItem[] = [
  {
    q: 'End-to-end data flow?',
    short: '4 streams → FastAPI → 10-feature vector → WebSocket 2.5s loop → MapLibre 3D heatmap → AlertEvent. Round trip <2.5s.',
    full: 'Four parallel streams ingest: (1) on-site geotech sensors (displacement, vibration, pore pressure, strain), (2) Sentinel-1 SAR VV/VH backscatter, (3) Copernicus GLO-30 DEM derivatives (slope, aspect, curvature), (4) Open-Meteo rainfall from ERA5 reanalysis. FastAPI receives these, validates against a Pydantic SensorReading schema, computes a 10-feature inference vector, runs the champion model (XGBoost), emits a RiskPrediction, and broadcasts over WebSocket /ws/feed in a 2.5-second loop. The Next.js + MapLibre 3D dashboard renders the risk heatmap. An AlertEvent triggers GPIO siren and GSM SMS. End-to-end round trip is under 2.5 seconds.',
    plain: 'Sensors and satellites feed a Python brain, which scores the risk and pushes a live map update every 2.5 seconds. If risk spikes, sirens and SMS fire.',
    tags: ['architecture', 'pipeline', 'realtime'],
  },
  {
    q: 'FastAPI backend structure?',
    short: 'schemas.py (Pydantic contracts), routers/rockfall.py (routes & WebSocket), main.py (lifespan, CORS, router mounting). Health probe /health on Render.',
    full: 'The backend is split into: schemas.py for Pydantic contracts (SensorReading, RiskPrediction, AlertEvent), routers/rockfall.py for HTTP routes and the WebSocket endpoint, and main.py for app lifespan management, CORS configuration, and router mounting. A /health probe is exposed for Render health checks. The mock-to-real swap is a single function change inside routers/rockfall.py because schemas were frozen on Day 0.',
    tags: ['fastapi', 'backend', 'structure'],
  },
  {
    q: 'Why Next.js 16 + React 19 + TypeScript 5.9?',
    short: 'App Router, Turbopack for millisecond HMR, React 19 concurrent state batching for 2.5s WebSocket streams, TS 5.9.3 pinned for ESLint stability.',
    full: 'Next.js 16 App Router gives us file-system routing and server components. Turbopack enables millisecond HMR during development. React 19\u2019s concurrent state batching is critical because we receive WebSocket frames every 2.5 seconds and need to coalesce re-renders without dropping frames. TypeScript 5.9.3 is pinned to avoid breaking changes with ESLint v9.',
    tags: ['nextjs', 'react', 'typescript'],
  },
  {
    q: 'MapLibre GL 3D pit heatmap?',
    short: 'Open-source MapLibre GL v6.4.1 + react-map-gl v8.1.2. 16 GeoJSON polygon zones, 3D terrain extrusion, risk color interpolation. 100% free, no paid Mapbox tokens.',
    full: 'We use MapLibre GL JS v6.4.1 with react-map-gl v8.1.2. Sixteen GeoJSON polygon zones span the Kusmunda AOI and are rendered with 3D terrain extrusion. Risk level drives a color interpolation from emerald (Safe) through amber (Warning) to rose (Evacuation). The stack is 100% open source with zero API keys, no paid Mapbox tokens, and no vendor lock-in.',
    tags: ['map', 'maplibre', 'visualization'],
  },
  {
    q: 'Pydantic contract enforcement?',
    short: 'SensorReading, RiskPrediction (bounded 0.0–1.0), AlertEvent. Hand-mirrored in frontend/lib/types.ts for zero translation error.',
    full: 'Pydantic models define the wire format: SensorReading, RiskPrediction (with probability bounded 0.0–1.0), and AlertEvent. The same shapes are hand-mirrored in frontend/lib/types.ts so the frontend gets end-to-end type safety without an OpenAPI codegen step. Any field shape change forces a TypeScript compile error.',
    tags: ['pydantic', 'contracts', 'types'],
  },
  {
    q: 'Mock-to-real sensor swap path?',
    short: 'Single internal function swap in routers/rockfall.py. Schemas frozen on Day 0, so frontend and WebSocket are unaffected.',
    full: 'Because schemas were frozen on Day 0, swapping from synthetic mock sensors to real on-site sensors is a single internal function replacement inside routers/rockfall.py. The WebSocket frames and Pydantic shapes do not change, so the frontend dashboard and alert pipeline keep working without modification.',
    tags: ['mock', 'real', 'migration'],
  },
  {
    q: 'WebSocket broadcast pattern?',
    short: 'ConnectionManager maintains active connection set, graceful disconnect handling, background asyncio broadcast loop inside FastAPI lifespan.',
    full: 'A ConnectionManager class maintains the set of active WebSocket connections. When a new RiskPrediction is produced, it is pushed to all connected clients. Disconnects are handled gracefully so a closed tab does not break the broadcast loop. The broadcast runs as a background asyncio task inside the FastAPI lifespan context manager.',
    tags: ['websocket', 'broadcast', 'realtime'],
  },
  {
    q: 'Why a 4×4 = 16 zone grid?',
    short: 'Spans 2.4 km (N–S) × 4.2 km (E–W) over Kusmunda AOI. 356 temporal days × 16 zones = 5,696 rows.',
    full: 'The Kusmunda AOI spans 2.4 km north–south and 4.2 km east–west. We discretise it into a 4×4 grid (16 zones) which is coarse enough for per-zone statistics but fine enough to localise failures. Across 356 temporal days this yields 5,696 (zone, day) rows for model training.',
    tags: ['grid', 'zone', 'kusmunda'],
  },
  {
    q: 'Geospatial DEM processing?',
    short: 'Copernicus GLO-30 DEM 30 m → richdem with metric 30 m transform (prevents 90° distortion) → Slope (Horn 1981), Aspect, Profile Curvature (Zevenbergen & Thorne 1987).',
    full: 'Copernicus GLO-30 DEM at 30 m resolution is exported from Google Earth Engine. We convert to a richdem.rdarray with an explicit metric 30 m transform \u2014 critical, because richdem defaults to degrees which distorts slopes above 60°. We then compute Slope (Horn 1981 algorithm), Aspect, and Profile Curvature (Zevenbergen & Thorne 1987) for every grid cell.',
    tags: ['dem', 'copernicus', 'topography'],
  },
  {
    q: 'Sentinel-1 SAR processing?',
    short: 'GEE S1 GRD IW mode VV/VH, descending Track 19 (100% spatial containment, locked incidence angle). Zonal mean sigma nought (–25 to 0 dB). Amplitude backscatter, NOT InSAR phase.',
    full: 'We pull Sentinel-1 GRD imagery in IW mode from Google Earth Engine, both VV and VH polarisations, descending Track 19 because that track gives 100% spatial containment of the Kusmunda AOI with a locked incidence angle. We take the zonal mean of sigma nought (in dB) for each of the 16 zones. The values typically fall between –25 and 0 dB. This is amplitude backscatter (surface roughness and moisture), not InSAR phase interferometry.',
    tags: ['sar', 'sentinel', 'backscatter'],
  },
  {
    q: 'Open-Meteo rainfall?',
    short: 'Unauthenticated ERA5 reanalysis endpoint. Single AOI query covers entire 2.4×4.2 km pit since ERA5 atmospheric grid is ~10 km.',
    full: 'Open-Meteo\u2019s free ERA5 reanalysis endpoint serves historical and forecast rainfall without authentication. Because the ERA5 atmospheric grid is roughly 10 km resolution, a single AOI query covers the entire 2.4×4.2 km Kusmunda pit, and we apply the same daily rainfall value to all 16 zones.',
    tags: ['rainfall', 'open-meteo', 'era5'],
  },
];

// ----------------------------------------------------------------------------
// Section 03 — Machine Learning & Data Science
// ----------------------------------------------------------------------------
export const section03: PitchItem[] = [
  {
    q: 'How severe is the class imbalance?',
    short: '61% Safe, 26% Warning, 13% Evacuation. A naive \u201calways safe\u201d classifier scores 61% accuracy but is lethal.',
    full: 'Across 4,784 (zone, day) rows the distribution is 61% Safe, 26% Warning, 13% Evacuation. A naive majority classifier that always predicts Safe would achieve ~61% accuracy while killing every single Evacuation case. This is exactly why we optimise for Evacuation Recall, not raw accuracy.',
    tags: ['imbalance', 'class', 'recall'],
  },
  {
    q: 'Class-weighted loss vs SMOTE?',
    short: 'Sensor channels are physically coupled (Fukuzono). SMOTE creates impossible synthetic points. Class weights: Safe 0.53, Warning 1.29, Evacuation 2.84 \u2014 missing an evacuation is penalised 5.4×.',
    full: 'SMOTE generates synthetic samples by interpolating between neighbours in feature space. Our 10 features include physically coupled channels (displacement, vibration, pore pressure, strain) governed by the Fukuzono equation. SMOTE would happily produce, for example, a high-displacement low-vibration row that cannot exist in physics. Class weighting keeps every training sample physically real while still penalising a missed evacuation 5.4× more than a false alarm.',
    plain: 'Faking extra training data can invent impossible rock physics. We chose to instead just teach the AI: \u201cmissing a real collapse is 5× worse than a false alarm.\u201d',
    tags: ['smote', 'class-weight', 'physics'],
  },
  {
    q: 'Why a temporal split instead of random?',
    short: 'Random split leaks future precursor trajectories. Hard cutoff at 2026-06-03: 285 days train (3,648 rows), 71 days test (1,136 rows, 197 Evacuations).',
    full: 'A random train/test split would leak future precursor trajectories into training, because a slope that fails on day 300 has precursor data on days 250–299 \u2014 which a random split would partially place in the test set. We use a hard temporal cutoff at 2026-06-03: the first 285 days (3,648 rows) train, the last 71 days (1,136 rows, 197 Evacuations) test. This tests genuine forward prediction on unseen future dates.',
    tags: ['split', 'temporal', 'leakage'],
  },
  {
    q: 'What are the 10 input features?',
    short: '(1) Slope, (2) Aspect, (3) Curvature, (4) VV Backscatter, (5) VH Backscatter, (6) Rainfall mm, (7) Displacement mm/day, (8) Vibration 0.01–0.90 g, (9) Pore Pressure, (10) Strain 50–1600 με.',
    full: 'The 10-feature vector is: (1) Slope (degrees from Horn 1981), (2) Aspect (degrees from north), (3) Profile Curvature (Zevenbergen & Thorne 1987), (4) Sentinel-1 VV sigma nought in dB, (5) Sentinel-1 VH sigma nought in dB, (6) Daily rainfall in mm from ERA5, (7) Displacement velocity in mm/day from on-site sensors, (8) Vibration in g (0.01–0.90), (9) Pore pressure in kPa, (10) Strain in microstrain (50–1600).',
    tags: ['features', 'input', 'vector'],
  },
  {
    q: 'XGBoost vs RandomForest head-to-head?',
    short: 'XGBoost 97.98% Acc, 100% Recall (0/197), 97.04% Precision. RF 97.71% Acc, 98.48% Recall (3/197), 99.49% Precision.',
    full: 'On the 1,136-row held-out test set with 197 Evacuation events: XGBoost achieved 97.98% accuracy, 100% recall on Evacuation (0/197 missed), and 97.04% precision. RandomForest achieved 97.71% accuracy, 98.48% recall (3/197 missed), and 99.49% precision. Both are production-ready. We ship XGBoost as the champion because zero missed evacuations is the hardest constraint in a life-safety system.',
    tags: ['xgboost', 'randomforest', 'comparison'],
  },
  {
    q: 'SHAP proof that the model learned geospatial features?',
    short: 'TreeExplainer on validation. v1 (pure displacement) had 0% terrain contribution. v2 (terrain-modulated risk score) shows 6.75% (XGB) and 18.63% (RF) terrain/SAR contribution.',
    full: 'We ran SHAP TreeExplainer on the validation set across both model versions. In v1, where labels were driven by raw displacement thresholds, terrain contributed 0.00% to XGBoost decisions \u2014 a near-trivial model. In v2, where labels are generated from a terrain-modulated risk score, terrain and SAR together contribute 6.75% to XGBoost and 18.63% to RandomForest. The jump proves the models are genuinely learning the geospatial signal, not just the displacement shortcut.',
    tags: ['shap', 'explainability', 'terrain'],
  },
  {
    q: 'v1 → v2 label fix?',
    short: 'risk_score = displacement × susceptibility_multiplier(zone), where multiplier = slope×0.50 + curvature×0.30 + SAR×0.20 scaled [0.70, 1.30]. SSR thresholds then applied to risk_score, not raw displacement. 75 crossover pairs generated.',
    full: 'v1 used raw displacement to generate labels, which forced the model to learn a single global threshold \u2014 useless in shadow zones. v2 defines risk_score = displacement × susceptibility_multiplier(zone), where the multiplier is a weighted sum of slope (0.50), profile curvature (0.30), and SAR backscatter (0.20), scaled into [0.70, 1.30]. The SSR thresholds (50, 120 mm/day) are then applied to risk_score, not raw displacement. This produces 75 zone-day crossover pairs where adjacent zones flip classification, which the model must learn to explain using terrain.',
    tags: ['v2', 'label', 'fix'],
  },
  {
    q: 'v2b / v2c isolation tests?',
    short: 'Proved RF\u2019s 30.31% terrain contribution is a spatial autocorrelation artifact (slope correlates with zone ID). XGBoost genuinely learned the continuous multiplier.',
    full: 'To rule out a spatial autocorrelation confound, we ran v2b (random zone IDs) and v2c (terrain shuffled across zones). RandomForest\u2019s apparent 30.31% terrain contribution collapsed under these tests, revealing it was leaning on zone ID. XGBoost\u2019s contribution held up because it learned the continuous multiplier, not the discrete zone identity. This is a key reason XGBoost is the champion.',
    tags: ['v2b', 'v2c', 'isolation'],
  },
];

// ----------------------------------------------------------------------------
// Section 04 — Deployment, Edge & Scaling
// ----------------------------------------------------------------------------
export const section04: PitchItem[] = [
  {
    q: 'Edge deployment on Raspberry Pi / Jetson?',
    short: 'ONNX Runtime runs 10-feature inference in milliseconds on ARM. Triggers GPIO relay sirens, strobe lights, and SIM800L GSM SMS. Zero internet dependency.',
    full: 'The champion XGBoost model is exported to ONNX and runs locally via ONNX Runtime on ARM CPUs. On a Raspberry Pi 4 or Jetson Nano the 10-feature inference completes in single-digit milliseconds, so the edge loop is: read sensors → run ONNX inference → if Evacuation, drive a GPIO relay that energises a siren and strobe light, then send an SMS via a SIM800L GSM modem. No internet connection is required for the life-safety loop.',
    tags: ['edge', 'raspberry-pi', 'jetson', 'onnx'],
  },
  {
    q: 'ONNX Runtime vs TFLite?',
    short: 'ONNX is faster on ARM, unified across XGBoost/RF/GRU/CNN-LSTM, avoids multi-format export bugs.',
    full: 'ONNX Runtime outperforms TFLite on ARM Cortex-A class CPUs in our benchmarks. ONNX also gives us a single export path for XGBoost, RandomForest, GRU, and any future CNN-LSTM model, so we avoid the multi-format export bugs that come from juggling pickle + SavedModel + tflite simultaneously.',
    tags: ['onnx', 'tflite', 'edge'],
  },
  {
    q: 'Opportunistic cloud sync?',
    short: 'Edge buffers sensor readings with original ingestion timestamps. Backfills Render/FastAPI when connection restores. No data loss.',
    full: 'The edge node buffers sensor readings in a local SQLite ring buffer, tagged with the original ingestion timestamp. When the WAN link comes back up, it replays the buffer into the Render-hosted FastAPI backend. This guarantees that a multi-day connectivity outage at a remote mine does not lose a single training-quality data point.',
    tags: ['sync', 'offline', 'buffer'],
  },
  {
    q: 'Multi-site scaling?',
    short: 'All site parameters live in data/aoi.json. Deploying a new mine is just a new bounding box + re-running the GEE pipeline.',
    full: 'Site configuration is centralised in data/aoi.json: bounding box, zone grid, SSR threshold overrides, sensor IDs. Standing up a new mine is \u2014 drop a new bounding box into the JSON, re-run the Google Earth Engine export pipeline, and the model and dashboard bind to the new AOI automatically. No code changes.',
    tags: ['scale', 'multi-site', 'config'],
  },
];

// ----------------------------------------------------------------------------
// Section 05 — Innovation & Social Good
// ----------------------------------------------------------------------------
export const section05: PitchItem[] = [
  {
    q: 'Key innovation?',
    short: 'First system to fuse 4 modalities (Geotech sensors + Sentinel-1 SAR + Copernicus DEM + Open-Meteo) under Fukuzono physical laws with SHAP-proven terrain learning.',
    full: 'We are the first system, to our knowledge, that fuses all four of (geotechnical sensors, Sentinel-1 SAR backscatter, Copernicus DEM derivatives, Open-Meteo rainfall) under a single physics-informed risk model grounded in the Fukuzono 1985 inverse-velocity method, with SHAP-confirmed evidence that the model genuinely uses the terrain signal and not just the displacement shortcut.',
    tags: ['innovation', 'fusion', 'fukuzono'],
  },
  {
    q: 'Which UN SDGs does this advance?',
    short: 'SDG 8 (Decent Work & Miner Safety), SDG 9 (Infrastructure Innovation), SDG 11 (Landslide Early Warning), SDG 13 (Climate Resilience against monsoon extremes).',
    full: 'The system advances four UN Sustainable Development Goals: SDG 8 (decent work and miner safety), SDG 9 (infrastructure innovation in extractive industries), SDG 11 (sustainable cities and communities \u2014 landslide early warning component), and SDG 13 (climate action \u2014 monsoon rainfall extremes are a primary rockfall trigger).',
    tags: ['sdg', 'impact', 'social'],
  },
  {
    q: 'Solo 8-day delivery \u2014 how?',
    short: 'Full pipeline across 16 phases: GEE geospatial ingestion, physics-informed synthetic data, RF/XGB models, SHAP, FastAPI, Next.js 3D dashboard, ONNX edge, deploy.',
    full: 'The full pipeline was delivered solo in 8 working days across 16 named phases: (1) problem scoping, (2) GEE geospatial ingestion, (3) physics-informed synthetic data, (4) feature engineering, (5) XGBoost baseline, (6) RandomForest baseline, (7) SHAP explainability, (8) v2 label fix, (9) v2b/v2c isolation, (10) GRU benchmark, (11) FastAPI backend, (12) WebSocket feed, (13) Next.js 3D dashboard, (14) Pydantic contracts, (15) ONNX edge export, (16) Render + Vercel deploy.',
    tags: ['delivery', 'solo', 'sprint'],
  },
];

// ----------------------------------------------------------------------------
// Section 06 — Judge Defense Flashcards
// ----------------------------------------------------------------------------
export const section06: Flashcard[] = [
  {
    q: 'What if your model just predicts \u201csafe\u201d all the time?',
    trap: 'Treating accuracy as the headline metric. \u201cWe got 61% accuracy\u201d is a death sentence.',
    counter: 'An always-safe classifier scores ~61% accuracy on our test set and is lethal. That is exactly why we use class-weighted loss and report Evacuation Recall as the headline metric. XGBoost achieved 100% recall \u2014 zero missed evacuations out of 197 in the held-out test set. We optimise for the worst failure mode, not the best accuracy line.',
    doNotSay: ['61% accuracy is good', 'Accuracy is the main metric'],
  },
  {
    q: 'Your data is synthetic \u2014 how is this real?',
    trap: 'Hiding the synthetic component. \u201cWe trained on real data\u201d when sensors were not deployed.',
    counter: 'Geospatial inputs (DEM, SAR backscatter, rainfall) are 100% real, pulled directly from ESA Copernicus, Sentinel-1, and ERA5. Sensor channels (displacement, vibration, pore pressure, strain) are synthetic, but they are calibrated to Landslide4Sense and follow the Fukuzono 1985 inverse-velocity power law. Real sensor swap is a single function change because the schemas were frozen on Day 0.',
    doNotSay: ['All data is real', 'No synthetic data was used'],
  },
  {
    q: 'You claimed InSAR \u2014 that is not what you use.',
    trap: 'Conflating SAR backscatter with InSAR phase interferometry. \u201cWe use InSAR\u201d is a technical red flag.',
    counter: 'Sentinel-1 GRD is amplitude backscatter \u2014 surface roughness and soil moisture, in sigma nought dB. It is not InSAR phase interferometry and we never claimed otherwise. The radar vendors (IDS GeoRadar, GroundProbe) sell InSAR hardware; we sell the satellite-amplitude fusion layer that covers the shadow zones their hardware cannot see.',
    doNotSay: ['We use InSAR', 'We measure mm displacement from space'],
  },
  {
    q: 'Why class-weighted loss instead of SMOTE?',
    trap: 'Defending SMOTE on principle. \u201cSMOTE is the standard\u201d is wrong here.',
    counter: 'SMOTE interpolates between neighbours in feature space. Our 10 features include physically coupled channels governed by the Fukuzono equation. SMOTE would happily fabricate a high-displacement low-vibration row that cannot exist in physics. Class weighting keeps every training sample physically real while still penalising a missed evacuation 5.4× more than a false alarm.',
    doNotSay: ['We use SMOTE', 'Synthetic samples are fine because they average'],
  },
  {
    q: 'Why temporal split instead of random split?',
    trap: 'Dismissing temporal leakage. \u201cRandom k-fold is the standard\u201d leaks precursor trajectories.',
    counter: 'A random train/test split would leak future precursor trajectories into training, because a slope that fails on day 300 has precursor data on days 250–299 which a random split partially places in the test set. Our hard temporal cutoff at 2026-06-03 (285 days train, 71 days test, 197 Evacuations) tests genuine forward prediction on unseen future dates.',
    doNotSay: ['Random k-fold is fine', 'We just shuffled the data'],
  },
  {
    q: 'Why report raw confusion counts instead of just percentages?',
    trap: 'Hiding absolute scale. \u201cWe got 97.98% accuracy\u201d without denominator is misleading.',
    counter: 'Percentages hide the error scale. We show 0 missed evacuations out of 197 (XGBoost) and 3 out of 197 (RandomForest) on 1,136 test rows. That is the unit a safety officer can audit. The 0 vs 3 difference is the difference between an undefended season and one preventable fatal incident.',
    doNotSay: ['97.98% accuracy is enough', 'Just trust the metric'],
  },
  {
    q: 'How does this compare to SSR?',
    trap: 'Positioning as a replacement. \u201cWe are better than SSR\u201d is a trap.',
    counter: 'We are a complement, not a replacement. SSR delivers sub-mm precision on line-of-sight benches. We cover the 20–40% shadow zones (behind ridges, ramps, moving trucks) at 5–10% of the cost. Where SSR exists, we ingest its displacement stream. Where it does not, we extend coverage through satellite-sensor fusion. Force multiplier, not competitor.',
    doNotSay: ['SSR is obsolete', 'We replace radar'],
  },
  {
    q: 'Can this work offline at a remote mine?',
    trap: 'Hedging on edge capability. \u201cIt needs cloud for some things\u201d is a partial answer.',
    counter: 'Yes \u2014 fully standalone. ONNX Runtime runs the 10-feature inference on a Raspberry Pi 4 or Jetson Nano in single-digit milliseconds, drives a GPIO relay to fire sirens and strobes, and dispatches SMS via a SIM800L GSM modem. Zero internet dependency for the life-safety loop. The cloud dashboard is an enhancement, not a requirement.',
    doNotSay: ['It needs internet', 'Cloud is required'],
  },
  {
    q: 'Why XGBoost over the deep learning GRU?',
    trap: 'Over-claiming deep learning. \u201cGRU matches trees\u201d or \u201cGRU is better\u201d is wrong on recall.',
    counter: 'GRU achieves perfect 1.0000 precision (zero false alarms) and zero catastrophic misses (zero Evacuation→Safe). All 55 missed evacuations landed safely in Warning. But its 0.7208 recall is unacceptable for life safety. XGBoost hits 100% recall. We ship XGBoost as the champion and ship GRU as a benchmark reference. The benchmark exists to prove the comparison was made honestly.',
    doNotSay: ['GRU matches trees on recall', 'Deep learning is always better', 'SHAP was run on GRU'],
  },
  {
    q: 'What is your go-to-market and revenue model?',
    trap: 'Hand-waving revenue. \u201cGovernment will buy it\u201d is not a plan.',
    counter: 'Three-tier model: (1) SaaS subscription per mine at ₹2–5 lakh/month for the cloud dashboard, (2) one-time edge hardware kit at ₹1.5–3 lakh covering Pi/Jetson/ONNX/siren/GSM, (3) DGMS audit and compliance reporting as an annual retainer. The 200+ Indian CIL and private mines plus global $300B surface mining market give us a 5-year serviceable obtainable market of roughly ₹600 Cr.',
    doNotSay: ['We will figure it out later', 'Government will buy it because it is good'],
  },
  {
    q: 'How do you handle the 8-hour manual round gap?',
    trap: 'Ignoring the human factor. \u201cAutomation solves it\u201d without the edge loop.',
    counter: 'The manual 8-hour round gap is exactly the failure mode the edge loop is designed to close. ONNX inference on Pi runs continuously, so the moment displacement velocity crosses the 50 mm/day Warning line the siren fires \u2014 no human in the loop, no 8-hour wait, no shift change delay. Manual rounds continue to provide a redundant safety net.',
    doNotSay: ['Humans will catch it', 'We just alert them faster'],
  },
  {
    q: 'Why not use a simpler threshold model?',
    trap: 'Under-selling the model. \u201cThresholds would have worked\u201d ignores the shadow zones.',
    counter: 'A flat displacement threshold (e.g. \u201calert at 50 mm/day\u201d) misses the entire problem we are solving. In shadow zones without SSR, we have no displacement sensor. The fusion model uses slope, curvature, SAR backscatter, and rainfall to estimate equivalent risk when displacement is unavailable. Threshold-only would collapse in those zones \u2014 the exact places where SSR cannot see.',
    doNotSay: ['Thresholds are good enough', 'We could have skipped ML'],
  },
  {
    q: 'What is your data retention and privacy story?',
    trap: 'Ignoring data governance. Judges will ask who owns the data.',
    counter: 'All data on Render and Vercel is encrypted at rest and in transit (TLS 1.3). Mine owners retain full data ownership \u2014 we are a processor, not an owner. 7-year retention aligns with DGMS audit requirements. On the edge, data stays on-device and is purged on hardware return. We do not sell or share mine data with any third party.',
    doNotSay: ['Data is public', 'We own the mine data'],
  },
  {
    q: 'How will you maintain this after the hackathon?',
    trap: 'Treating it as a one-off demo. \u201cWe will figure it out\u201d is not credible.',
    counter: 'Three legs: (1) the model and pipeline live in our GitHub repo with a public issue tracker, (2) we have already filed provisional disclosures for the terrain-modulated risk score (v2) and the SHAP-validated terrain learning, (3) we are in conversation with two CIL subsidiaries for a 90-day pilot post-SIH. The PoC is the proof point; the pilot is the next step.',
    doNotSay: ['We will build it after the hackathon', 'Maintenance is a future problem'],
  },
  {
    q: 'What is the single biggest risk to this system in production?',
    trap: 'Saying \u201cno risks\u201d. \u201cIt is perfect\u201d is a lie judges will catch.',
    counter: 'Sensor failure on a remote bench \u2014 a vibrating wire extensometer dying in monsoon heat. Our mitigation is sensor fusion: if displacement drops out, the model leans harder on SAR backscatter, slope, curvature, and rainfall. The fusion architecture is exactly what lets us degrade gracefully instead of going blind. SHAP lets the operator see which channels the model is leaning on and which sensor to inspect first.',
    doNotSay: ['No risks', 'Sensors never fail'],
  },
];

// ----------------------------------------------------------------------------
// Section 07 — Deep Learning Benchmark (GRU vs Trees)
// ----------------------------------------------------------------------------
export const section07: PitchItem[] = [
  {
    q: 'Why did we benchmark a GRU against the tree models?',
    short: 'Honest comparison. We needed to prove the choice of XGBoost over a deep recurrent baseline was deliberate, not default.',
    full: 'A deep learning benchmark is the honest move. If we shipped XGBoost without comparing to a recurrent model, a sharp judge would ask why. So we trained a Gated Recurrent Unit (GRU) on the same 10-feature sequences (356 days × 16 zones), ran it on the same temporal test split, and reported all three metrics transparently.',
    tags: ['gru', 'benchmark', 'honesty'],
  },
  {
    q: 'GRU architecture and training?',
    short: '25% fewer parameters than LSTM, better generalisation on small datasets (3,440 sequences). 50 epochs, Adam, class-weighted loss.',
    full: 'We chose GRU over LSTM because it has ~25% fewer parameters and generalises better on small datasets. Our 3,440 training sequences are small by deep-learning standards, so parameter efficiency matters. We trained for 50 epochs with Adam, the same class-weighted loss as the trees, and a 64-unit hidden state.',
    tags: ['gru', 'architecture', 'training'],
  },
  {
    q: 'Defensible GRU talking point?',
    short: 'Perfect 1.0000 precision. Zero catastrophic misses \u2014 all 55 missed evacuations landed safely in Warning. The benchmark is honest.',
    full: 'The GRU benchmark is defensible because the failures it makes are safe failures. Its 1.0000 precision means zero false alarms, which is operationally valuable. Its 55 missed evacuations all landed in the Warning class \u2014 not Safe \u2014 so the safety floor held. There were zero Evacuation-to-Safe catastrophic misses.',
    tags: ['gru', 'precision', 'safe-failure'],
  },
];

// ----------------------------------------------------------------------------
// Benchmark numbers
// ----------------------------------------------------------------------------
export const benchmarkModels: BenchmarkModel[] = [
  {
    name: 'XGBoost',
    precision: 0.9704,
    recall: 1.0,
    f1: 0.985,
    missed: 0,
    totalEvac: 197,
    note: 'Champion. Zero missed evacuations. Shipped.',
    tone: 'champion',
  },
  {
    name: 'RandomForest',
    precision: 0.9949,
    recall: 0.9848,
    f1: 0.9898,
    missed: 3,
    totalEvac: 197,
    note: 'Strong fallback. Highest precision. 3 misses in Warning.',
    tone: 'strong',
  },
  {
    name: 'GRU (RNN)',
    precision: 1.0,
    recall: 0.7208,
    f1: 0.8378,
    missed: 55,
    totalEvac: 197,
    note: 'Benchmark. 55 misses all safely in Warning. Zero false alarms.',
    tone: 'benchmark',
  },
];

// ----------------------------------------------------------------------------
// Glossary (non-tech translations)
// ----------------------------------------------------------------------------
export type GlossaryTerm = { term: string; plain: string; detail?: string };

export const glossary: GlossaryTerm[] = [
  {
    term: 'Fukuzono Curve',
    plain: 'Rock acceleration math. Speed goes up, 1/speed goes to 0 right before collapse.',
    detail: 'Discovered by Fukuzono in 1985. When you plot 1 / displacement-velocity over time, the line walks straight toward zero as failure approaches. At the moment of collapse, velocity diverges and 1/v crosses zero.',
  },
  {
    term: 'SSR (Slope Stability Radar)',
    plain: 'Ground-based laser radar that watches a rock wall 24/7 with sub-millimetre precision.',
    detail: 'Manufactured by IDS GeoRadar and GroundProbe. Costs ₹2–4 Cr per unit, needs 4–6 units to cover a large opencast mine. We complement it in the 20–40% shadow zones it cannot see.',
  },
  {
    term: 'SAR Backscatter (NOT InSAR)',
    plain: 'Satellite radar brightness measuring ground roughness and moisture \u2014 not millimetre laser distance.',
    detail: 'Sentinel-1 GRD gives us amplitude backscatter (sigma nought in dB). This tells us how rough or wet the surface is. InSAR phase interferometry is a different technique we do not use.',
  },
  {
    term: 'Class Imbalance',
    plain: 'Rockfalls are rare (13% of our data). If an AI just guesses "safe" all day, it scores 61% accuracy while killing people. We fixed that.',
    detail: 'Our distribution is 61% Safe, 26% Warning, 13% Evacuation. We use class-weighted loss (Safe 0.53, Warning 1.29, Evacuation 2.84) so missing a real evacuation is penalised 5.4× more than a false alarm.',
  },
  {
    term: 'SHAP',
    plain: 'AI lie-detector that proves our model looks at slope and terrain, not just raw displacement.',
    detail: 'SHapley Additive exPlanations. In v2 of our label generator, terrain and SAR contribute 6.75% to XGBoost and 18.63% to RandomForest \u2014 proof the models are genuinely learning the geospatial signal.',
  },
  {
    term: 'ONNX Runtime',
    plain: 'Universal lightweight AI runner that works offline on a ₹5,000 Raspberry Pi.',
    detail: 'Open Neural Network Exchange. A single model format that runs on ARM CPUs without a GPU. Faster than TFLite on Cortex-A class chips and avoids multi-format export bugs.',
  },
  {
    term: 'WebSocket',
    plain: 'A live two-way phone line between the server and your browser, instead of the browser having to ask every 2.5 seconds.',
    detail: 'Our /ws/feed endpoint pushes a fresh RiskPrediction frame every 2.5 seconds. The dashboard just listens, no polling, no refresh.',
  },
  {
    term: 'MapLibre GL',
    plain: 'Free open-source 3D mine map. No paid Mapbox tokens, no vendor lock-in.',
    detail: 'MapLibre GL JS v6.4.1 with react-map-gl v8.1.2. Renders the 16 GeoJSON zones with 3D terrain extrusion and risk colour interpolation.',
  },
  {
    term: 'FastAPI',
    plain: 'Python brain that turns raw sensors into risk scores and pushes them to the dashboard.',
    detail: 'FastAPI 0.136.x with Pydantic contracts (SensorReading, RiskPrediction, AlertEvent). WebSocket broadcast inside an asyncio lifespan context manager.',
  },
  {
    term: 'Pydantic',
    plain: 'A strict bouncer for data. Wrong shape, wrong type \u2014 it does not let the bad data through.',
    detail: 'Pydantic v2 enforces SensorReading, RiskPrediction, AlertEvent shapes. Probability is bounded 0.0\u20131.0. The same shapes are hand-mirrored in TypeScript for end-to-end type safety.',
  },
  {
    term: 'GRU',
    plain: 'A small, fast recurrent neural network that remembers recent sensor history. We use it as a benchmark, not the champion.',
    detail: 'Gated Recurrent Unit. ~25% fewer parameters than LSTM, better generalisation on small datasets. Trained on 3,440 sequences, 50 epochs, Adam optimiser, class-weighted loss.',
  },
  {
    term: 'XGBoost',
    plain: 'A decision-tree AI that builds a forest of weak learners and corrects its own mistakes. Our champion.',
    detail: 'eXtreme Gradient Boosting. 97.98% accuracy, 100% Evacuation Recall (0/197 missed) on the 1,136-row held-out test set. Exported to ONNX for edge deployment.',
  },
  {
    term: 'RandomForest',
    plain: 'A decision-tree AI that builds many independent trees and lets them vote.',
    detail: '99.49% Precision, 98.48% Recall (3/197 missed). Strong fallback model. Highest precision of the three.',
  },
  {
    term: 'DEM',
    plain: 'A 3D elevation map of the terrain, 30 m resolution, free from the European Space Agency.',
    detail: 'Copernicus GLO-30 DEM. We compute Slope (Horn 1981), Aspect, and Profile Curvature (Zevenbergen & Thorne 1987) on top of it.',
  },
  {
    term: 'Temporal Split',
    plain: 'Training on the past, testing on the future \u2014 like a real forecast, not a quiz with leaked answers.',
    detail: 'Hard cutoff at 2026-06-03. 285 days train (3,648 rows), 71 days test (1,136 rows, 197 Evacuations).',
  },
];

// ----------------------------------------------------------------------------
// Filter pills
// ----------------------------------------------------------------------------
export const filterPills = [
  { id: 'all', label: 'All' },
  { id: 'pitch', label: 'Pitch Flow' },
  { id: 'defense', label: 'Judge Traps' },
  { id: 'ml', label: 'ML & Metrics' },
  { id: 'arch', label: 'Architecture & Edge' },
  { id: 'impact', label: 'Impact & SDGs' },
  { id: 'gru', label: 'GRU vs Trees' },
] as const;

export type FilterId = (typeof filterPills)[number]['id'];

// ----------------------------------------------------------------------------
// Teleprompter script (minute-by-minute)
// ----------------------------------------------------------------------------
export type TeleprompterSegment = {
  minute: string;
  title: string;
  points: string[];
};

export const teleprompter: TeleprompterSegment[] = [
  {
    minute: 'Minute 1',
    title: 'The Problem (Kusmunda anchor)',
    points: [
      'Open with the 30-second human story: one rockfall can shut a mine for a month and burn half a billion rupees.',
      'State the anchor: Kusmunda SECL, one of India\u2019s largest opencast coal mines, 200 m+ deep benches, 60–75° face angles.',
      'Cite DGMS: slope instability is top-3 fatal cause; equipment losses ₹80–120 Cr per dragline.',
      'Name the gap: SSR costs ₹2–4 Cr per unit, 4–6 units per mine, leaves 20–40% shadow zones unmonitored.',
    ],
  },
  {
    minute: 'Minute 2',
    title: 'The Tech Stack (4 streams + Fukuzono)',
    points: [
      'Walk through the 4 ingest streams: geotech sensors, Sentinel-1 SAR, Copernicus DEM, Open-Meteo rainfall.',
      'Explain Fukuzono inverse-velocity in one breath: 1/speed walks to zero as collapse approaches.',
      'Show the 10-feature vector: slope, aspect, curvature, VV, VH, rain, displacement, vibration, pore pressure, strain.',
      'Highlight the round trip: end-to-end under 2.5 seconds, FastAPI → WebSocket → MapLibre 3D heatmap.',
    ],
  },
  {
    minute: 'Minute 3',
    title: 'The ML Result (100% Recall)',
    points: [
      'Lead with the headline: 100% Evacuation Recall on a 1,136-row held-out test set. Zero missed evacuations out of 197.',
      'Show the three models side by side: XGBoost 97.98% Acc, RandomForest 97.71%, GRU 83.78% F1.',
      'Explain the class imbalance: 61/26/13, and why class-weighted loss beats SMOTE for physics-coupled sensor data.',
      'Prove honesty with SHAP: terrain and SAR contribute 6.75% to XGB \u2014 the model genuinely uses the geospatial signal.',
    ],
  },
  {
    minute: 'Minute 4',
    title: 'Edge Demo & Deployment',
    points: [
      'Live demo cue: open the dashboard, point at the live WebSocket frames updating every 2.5 seconds.',
      'Show the edge story: ONNX on Raspberry Pi, GPIO siren, SIM800L GSM SMS, zero internet dependency.',
      'Name the deployment split: Vercel for the Next.js dashboard, Render for the FastAPI backend, both autoscaling.',
      'Close with SDGs 8, 9, 11, 13 and the solo 8-day sprint. Hand off for questions.',
    ],
  },
];
