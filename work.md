
# WORK.md — SIH25071 Day 4–6: Deep Learning + Real Backend Integration

Research-verified Aug 20, 2026. Continues from WORK.md (Phases 10–16, DONE — RF/XGBoost v2 baseline locked, test-set evacuation F1 0.99 both models). Scope here: LSTM/GRU benchmark, swap mock backend for real models, wire live feed, Render deploy started early.

Four corrections folded in below (⚠️) — verified against current docs, not memory.

---

## Phase 17 — LSTM/GRU Sequence Framing (blocks all DL work) `[DONE ✅ 2026-08-21]`
**Target: first 45 min of Day 4.**

Your RF/XGBoost baseline treats each row as an independent observation (correct for tree models, given Phase 10's temporal split). LSTM/GRU is different — it needs actual *sequences*. Reused Phase 12's `sar_forward_fill()` join logic exactly (verified identical max staleness: 23 days) rather than reimplementing it, so LSTM input features are byte-for-byte consistent with what RF/XGBoost trained on.

- [x] **Window length: 14 days**, sequence of last 14 days per zone → predict `risk_level` of the window's **final (last) timestep** — deployment-realistic framing (a live feed gives you sensor history, you want today's risk).
- [x] Sequences built **per zone**, sliding window, verified never crossing a zone boundary (grouped by `zone_id` before windowing).
- [x] **Actual policy implemented (Option B, deliberately chosen over the original "drop any straddling window" plan below):** windows may pull history **backward** from an earlier split — e.g. a val-target window (target date ≥ `2026-04-07`) is allowed to reach back into train-period dates for its preceding 13 days. **Windows may never reach forward into a later split** (a train-target window cannot touch val/test dates; a val-target window cannot touch test dates) — this remains a hard leakage guard, enforced with explicit assertions in `build_sequences_for_zone()`. Label/split assignment always follows the **target (last-timestep) date only**, never the history dates.
  - *Rationale for Option B over the original plan's "drop straddling windows":* dropping would have cost the first 13 days of evacuation-class signal in val/test — exactly the class already thinnest. Option B recovers those rows at zero leakage cost, since the model predicting on April 8th would have legitimate access to April 1st–7th's readings regardless of which "split" those dates were labeled for evaluation bookkeeping. This is not the same failure mode as Phase 10 (which was about the *label* leaking early) — only input history reaches backward here.
- [x] Sequence counts computed and verified before training (ran `scripts/phase17_sequence_builder.py`, full console output reviewed):
  - **train: 3,440 sequences** (down from 4,560 train rows — train's own first 13 days per zone have no earlier split to borrow history from, so these are genuinely dropped, not a bug)
  - **val: 912 sequences** — matches Phase 10's val row count exactly (every val day gets a full window via train-borrowed history)
  - **test: 1,136 sequences** — matches Phase 10's test row count exactly, same reason
  - Evacuation-class counts: **train 403, val 113, test 197** — all comfortably above the thin-class warning threshold (30), so LSTM's evacuation F1 can be treated as directly comparable to RF/XGBoost's row-level numbers.
- [x] Feature set per timestep: same 10 features as RF/XGB (4 sensor + 6 terrain/SAR), order-matched to `models/feature_order.json`. Confirmed terrain features (`slope`/`aspect`/`curvature`) are constant within a zone's window (expected — static per zone) and SAR/rainfall features (`vv_backscatter`/`vh_backscatter`/`rainfall_mm`) step only when a new SAR acquisition date is crossed within the 30-date series (expected — not a bug if a window looks "flat" on these columns).
- [x] Output saved: `data/sequences/{train,val,test}_sequences.npz` (X shape `(n, 14, 10)`, y shape `(n,)`), plus per-sequence metadata JSON and `data/sequences/manifest.json` recording window length, cutoffs, feature order, label encoding, and the history-boundary policy verbatim — this is the paper trail if asked how history/label boundaries were handled.
- [x] Script: `scripts/phase17_sequence_builder.py` — reuses `sar_forward_fill()` verbatim from `phase12_baseline_training.py`, do not fork this join logic a second time.

> **Note for Phase 18:** RF/XGBoost remain row-based on the original `train.csv`/`val.csv`/`test.csv` — Phase 17's sequence files are consumed **only** by the LSTM/GRU pipeline. No change to the existing tree-model artifacts or their SHAP numbers.

---

## Phase 18 — LSTM/GRU Implementation
**Target: Day 4, 2–3 hrs.**

⚠️ **Correction — class weighting API is different from sklearn, don't reuse Phase 11's approach as-is.** PyTorch's `nn.CrossEntropyLoss` takes a `weight` tensor of per-class weights (length = num_classes), not a per-sample weight array like sklearn's `sample_weight`. Compute inverse-frequency class weights from **train split only** (same rule as Phase 11 — never from full dataset), convert to a `torch.tensor`, pass via `weight=` to the loss constructor:
  ```python
  from sklearn.utils.class_weight import compute_class_weight
  import torch

  class_weights = compute_class_weight('balanced', classes=np.array([0,1,2]), y=y_train_seq)
  weight_tensor = torch.tensor(class_weights, dtype=torch.float32)
  criterion = nn.CrossEntropyLoss(weight=weight_tensor)
  ```
  If using Keras/TF instead: `class_weight` param on `.fit()` takes a `{0: w0, 1: w1, 2: w2}` dict — different shape again, don't copy-paste the PyTorch tensor in.

⚠️ **Second correction — `y_train_seq` must come from `data/sequences/train_sequences.npz`'s `y` array (3,440 labels), NOT from `train.csv`'s `risk_level` column (4,560 labels).** Phase 17 confirmed these two counts genuinely diverge — sequence-building drops each zone's first 13 days (no history available), so the sequence-level class distribution is not identical to the row-level one. Load weights like this:
  ```python
  train_npz = np.load("data/sequences/train_sequences.npz")
  X_train_seq, y_train_seq = train_npz["X"], train_npz["y"]  # y_train_seq: (3440,) int labels 0/1/2
  class_weights = compute_class_weight('balanced', classes=np.array([0,1,2]), y=y_train_seq)
  ```
  Computing weights against the wrong (row-level) label array won't error — it'll just silently produce a weight vector calibrated to a distribution the LSTM was never actually trained on. Double check `y_train_seq.shape[0] == 3440` before proceeding.

- [ ] Framework choice: if you already have PyTorch/TF installed and comfortable, use it — don't add a new dependency this close to demo for marginal benefit. If starting fresh, PyTorch has the more direct class-weight path shown above.
- [ ] Architecture: start simple — single LSTM/GRU layer (64–128 hidden units) → dropout (0.2–0.3) → dense → softmax(3). This is a hackathon benchmark, not a research contribution; an over-engineered stack that overfits your ~3-4K sequences will score worse than the RF baseline and undermine the "progression" story.
- [ ] Same train/val/test sequence sets from Phase 17. Use the val split for early stopping (patience 5–10 epochs on val loss), not the test set.
- [ ] Reuse the class-weighted loss exactly as computed above. Do not additionally rebalance via oversampling — same rationale as Phase 11 (physically correlated channels), now compounded by sequence structure (oversampling a sequence duplicates a whole 14-day trajectory verbatim, which is an even worse leakage-adjacent risk than duplicating a single row).
- [ ] Save the trained model (`.pt` or `.h5`) with a clear versioned filename matching your existing convention: `models/lstm-v1-20260821.pt` (adjust date).

---

## Phase 19 — LSTM/GRU Evaluation (same rules as Phase 13, no new rubric)
**Target: Day 4, 1 hr.**

- [ ] Run the identical `classification_report` from Phase 13 on the LSTM/GRU test-set predictions. Per-class precision/recall/F1, evacuation class headlined — not accuracy. Reusing the same eval code from Phase 13/14 (parameterize on model instead of duplicating) keeps the RF/XGB/LSTM numbers directly comparable, which is the whole point of the comparison table.
- [ ] Confusion matrix, same style as Phase 13 (evacuation row/column highlighted, raw counts not just percentages).
- [ ] Fill in the `LSTM/GRU (Target)` column in the comparison table from WORK.md Phase 16 — this table is a pitch asset, keep it live, don't recreate it.
- [ ] **Expected outcome, know this going in**: on a synthetic dataset this clean (RF/XGB already at 97-100% test accuracy, 0.99 evacuation F1), LSTM/GRU is very unlikely to beat the tree baseline — sequence models earn their keep on messier temporal dependencies than a physics-generated Fukuzono curve with 10 clean features. **That's fine and expected — do not manufacture a win.** The honest story for the pitch: *"Tree baselines already capture the strong physical signal in our synthetic data extremely well. LSTM/GRU is included to benchmark against the literature-standard model progression (RF/XGBoost → LSTM/GRU → hybrid ensemble) and to validate our architecture scales to a deep-learning approach when moving from synthetic to real noisy sensor data, where temporal dependencies would matter more."* This is a stronger, more defensible answer than an inflated LSTM number a judge might probe and find inconsistent with your SHAP/eval methodology elsewhere.
- [ ] If LSTM/GRU does meaningfully underperform, do NOT quietly drop it from the deck — the comparison table with an honest "tree models win on this data, here's why" is more credible than showing only your best model.

---

## Phase 20 — Backend: Swap Mock `/predict` for Real Model
**Target: Day 4–5, 2–3 hrs.**

⚠️ **Correction — load the model in FastAPI's `lifespan`, not at import time or inside the endpoint.** Verified current best practice: use the `lifespan` async context manager (the `@app.on_event("startup")` decorator is deprecated), store the loaded model on `app.state`, and — critically — **let load failure crash startup rather than serving a broken endpoint**. A worker that can't load the model should fail fast so Render's process manager flags it, not silently serve 500s on first request.

```python
from contextlib import asynccontextmanager
import joblib

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model = joblib.load("models/rf-v2-20260820.joblib")
    app.state.feature_order = json.load(open("models/feature_order.json"))
    app.state.label_encoding = json.load(open("models/label_encoding.json"))
    yield
    del app.state.model

app = FastAPI(lifespan=lifespan)

@app.post("/predict", response_model=RiskPrediction)
async def predict(reading: SensorReading, request: Request):
    model = request.app.state.model
    # build feature vector in app.state.feature_order, run model.predict_proba, map back via label_encoding
    ...
```

- [ ] Pick the model to ship first: **RF v2**, not XGBoost — RF's evacuation recall (0.9848) is marginally behind XGBoost's (1.0000) but RF's precision is higher (0.9949 vs 0.9704) and its terrain/SAR SHAP contribution is stronger (17.03% vs 6.90%), which is the more interesting story for judges ("our model genuinely uses the geospatial pipeline"). If asked why not XGBoost: you have the answer — XGBoost's perfect recall came with more false evacuation alarms, and you can show both in the table.
- [ ] Load `feature_order.json` and `label_encoding.json` from Phase 15 alongside the model — the endpoint must assemble the feature vector in the **exact trained column order**, and decode `predict()`'s integer output back through `label_encoding.json`, not a hardcoded guess at the mapping.
- [ ] `/predict` input is a `SensorReading` (per the Day 0 contract) but the model needs terrain/SAR features too — the endpoint must look up the zone's static terrain/SAR values (from `data/zone_features.csv`, loaded once at startup into `app.state`, not re-read from disk per request) and join them to the incoming sensor reading before calling `model.predict()`.
- [ ] Output must validate against the existing `RiskPrediction` Pydantic schema unchanged — this is the contract-first payoff from Day 0. If the mock and real endpoint both satisfy the same schema, frontend needs zero changes.
- [ ] Add a `model_version` field value that reflects the real artifact (`"rf-v2-20260820"`), not the mock's placeholder — the frontend/dashboard can display this, useful for demo credibility ("here's exactly which model version is live").
- [ ] Smoke test: call `/predict` with a known evacuation-class input from your test set, confirm the returned `risk_level` matches what Phase 14's offline evaluation predicted for that row. If it doesn't match, the feature-order or label-encoding wiring is wrong — catch this now, not during the Day 6 integration test.

---

## Phase 21 — Backend: Wire Real Generator into Live Feed
**Target: Day 5, 2 hrs.**

- [ ] **Before anything else, open `scripts/phase7_synthetic_sensors.py` and confirm it's structured as importable functions (e.g. `def generate_next_reading(zone_id, prev_state) -> SensorReading`), not a standalone `if __name__ == "__main__":` script that only writes a CSV and exits.** If it's the latter, this phase needs a refactor pass first (extract the per-timestep generation logic into a callable function) before it can be looped inside a FastAPI background task. Don't discover this mid-implementation — check it first, it changes the shape of this phase's work.
- [ ] Replace the Day 1 random mock generator behind `/ws/feed` with the Phase 7 physics-informed generator, run in "live" mode — instead of writing a static 356-day CSV, step it forward one timestep at a time on a loop (e.g. every 2-5 seconds) and broadcast via the existing `ConnectionManager` pattern from Day 1. Reuse the broadcast pattern; don't build a second channel.
- [ ] Each broadcast tick: generate the next `SensorReading` for a zone (or all 16 in rotation), run it through the now-real `/predict` logic (call the same function the endpoint uses, don't duplicate model-loading code), and push both `SensorReading` + `RiskPrediction` in the existing WebSocket envelope shape.
- [ ] Alert-trigger logic: when a tick's `risk_level` crosses into `warning` or `evacuation`, emit an `AlertEvent` over the same channel. Trigger on **class crossing a threshold**, not on every warning/evacuation tick — otherwise a zone sitting in evacuation for 10 consecutive ticks fires 10 alerts instead of 1, which will look broken on the dashboard's alert log during the live demo.
- [ ] Keep a per-zone "last known state" in `app.state` so the crossing-detection above has something to compare against between ticks.
- [ ] This is the piece most likely to have subtle bugs (async loop timing, broadcast to disconnected clients, alert de-dup) — test it standalone with a WebSocket test client (as you already did in Phase 8) before touching the frontend.

---

## Phase 22 — Frontend: Point at Real Backend
**Target: Day 5, 1–2 hrs.**

- [ ] Switch dashboard's API base URL from mock to local real backend first (`http://localhost:8000` or whatever your dev port is) — confirm end-to-end locally before touching deployment.
- [ ] Fix any schema drift now. You already flagged one in Phase 9: `frontend/lib/types.ts`'s `SensorReading` is missing the optional `risk_level?: RiskLevel | null` field present in the backend Pydantic model. Add it now — this is exactly the Day 6 blocker Phase 9 warned about, don't let it slide further.
- [ ] Confirm the heatmap's three risk-band colors still map correctly against **real** model outputs, not just the mock's weighted-random values — real model output distribution may cluster differently than the 60/25/15 mock weighting did visually, double check the map doesn't look "off" (e.g., all-green or all-red) with real predictions live.
- [ ] No new UI work here — Day 5 frontend scope is re-pointing and fixing drift, not new features. Polish is Day 6.

---

## Phase 23 — Render Deployment (start now, not Day 7)
**Target: Day 5–6, 2–3 hrs. Deploy early on purpose — this is a known failure point if left late.**

⚠️ **Correction — Render's free tier sleeps after 15 min idle, causing a 30–60s cold start on the next request.** This directly threatens your live demo: if the backend hasn't received traffic in the last 15 minutes before you present, the judges' first request (or your dashboard's first WebSocket connect) will hang for up to a minute looking exactly like a broken deploy. Plan around this explicitly — see the demo-day mitigation below, don't discover it live.

- [ ] `requirements.txt` must be complete and pinned — Render's build command is `pip install -r requirements.txt`, nothing more. Test this in a clean venv locally before pushing (`python -m venv fresh-test && pip install -r requirements.txt`) to catch anything you have installed locally but forgot to freeze.
- [ ] Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT` — **`$PORT` must stay the literal environment variable, not a hardcoded port number.** Render assigns the port dynamically; a hardcoded port produces a "no open ports detected" failure that looks like a code bug but is actually a config bug.
- [ ] Pin Python version explicitly (`runtime.txt` with `python-3.12.x` or Render's environment settings) — don't let Render pick a default that may not match the 3.12 you've developed and tested against; a version mismatch is exactly the kind of thing WORKFLOW.md's Day 4-6 section already warned you to surface early.
- [ ] Model artifacts (`models/*.joblib`, `models/*.json`) and `data/zone_features.csv` must be committed to the repo (or otherwise available at deploy time) — Render's build only runs `pip install`, it doesn't run your data pipeline. If these files aren't in git, the deployed `lifespan` startup will crash on `joblib.load()`, and per Phase 20's fail-fast design, the whole service won't start. Verify these files are tracked (`git status` / `.gitignore` check) before the first deploy attempt.
- [ ] Environment variables (if any — GEE credentials are NOT needed at runtime since your geospatial pipeline is a Day 1-2 offline step whose *output* is the checked-in CSV, not a live dependency) — confirm nothing in the real `/predict` path tries to re-authenticate to GEE at request time. It shouldn't, per your architecture, but verify.
- [ ] After first successful deploy: test the actual `.onrender.com` URL from a browser/curl, not just "build succeeded" in the Render dashboard. A clean build with a broken runtime path is a common false-positive.
- [ ] **Demo-day mitigation for the cold-start issue**: ping the deployed `/predict` or a lightweight health-check endpoint yourself 2-3 minutes before you go on stage/present, so the instance is warm when judges interact with it. Consider adding a trivial `GET /health` endpoint now if you don't have one — cheap to build, useful both for this and for Phase 24's integration test.

---

## Phase 24 — End-of-Day-6 Review Checklist
**Target: end of Day 6, 20–30 min self-review. Do not skip — this is your last checkpoint before Day 7's integration test in WORKFLOW.md.**

- [ ] ✅ LSTM/GRU trained, evaluated with the same per-class precision/recall/F1 rubric as RF/XGBoost, comparison table (WORK.md Phase 16 table) fully filled in across all three models.
- [ ] ✅ Honest LSTM/GRU narrative locked and rehearsed (Phase 19) — not inflated, ties back to the RF/XGB/LSTM/hybrid progression from CONTEXT.md's literature reference.
- [ ] ✅ Real `/predict` endpoint live locally, loading via `lifespan`, validated against Phase 15's known-good test-set predictions (Phase 20 smoke test passed).
- [ ] ✅ Live feed (`/ws/feed`) broadcasting real generator output through the real model, alert-trigger logic confirmed to fire once per threshold-crossing, not per-tick (Phase 21).
- [ ] ✅ Frontend re-pointed at real backend, `types.ts` drift from Phase 9 fixed, heatmap verified against real (not mock) prediction distribution (Phase 22).
- [ ] ✅ Backend deployed and reachable at a live `.onrender.com` URL, tested from outside the dev machine, `$PORT`/`runtime.txt`/committed model artifacts all verified (Phase 23).
- [ ] ✅ Confirm unblocked for Day 6-7's full integration test (WORKFLOW.md): real generator → real model → FastAPI → WebSocket → dashboard, end to end, zero mocks remaining anywhere in the loop.
- [ ] Note anything **not** done here honestly — if LSTM/GRU or Render deploy slipped, WORKFLOW.md Day 6-7 explicitly says edge deployment is droppable-to-slide-only if core isn't solid; the same logic applies here: a fully working RF-only real backend beats a half-wired LSTM integration on demo day.

---

## Notes for the pitch deck (carry forward)
- Model progression story is now complete and honest end-to-end: RF/XGBoost baseline (near-perfect on synthetic data, terrain/SAR genuinely learned per SHAP) → LSTM/GRU benchmarked on identical split/metrics (included for architectural completeness and forward-compatibility with real noisy sensor data, not because it won). This is a *stronger* pitch than a single-model system — it shows deliberate methodology, not just "we trained a model."
- `lifespan`-based model loading with fail-fast startup is a small but real engineering-maturity signal if a technical judge inspects your repo — worth a one-line mention if the conversation goes there.
- Cold-start mitigation (warm the Render instance pre-demo) is an operational detail, not a pitch talking point — just don't get caught by it live.
- Class-weighted loss now applied consistently across all three model families (sklearn `sample_weight` for RF/XGB, `CrossEntropyLoss(weight=...)` for LSTM) — same underlying principle (inverse-frequency, train-split-only), correctly adapted per-framework. If asked "did you handle imbalance the same way for your deep learning model," the honest answer is "same principle, framework-appropriate implementation" — say that, don't claim identical code.

---

## Deferred to Day 7-8 (per WORKFLOW.md, do not pull forward)
- ONNX export (`skl2onnx` for RF works directly via `to_onnx()`; **XGBoost does not convert via skl2onnx alone** — it requires `onnxmltools` plus `update_registered_converter` to register XGBoost's converter. Know this now so it's not a surprise if you do attempt the edge slide, but do not spend Day 4-6 time on it — WORKFLOW.md is explicit that this is a nice-to-have that gets cut first if core isn't solid.)
- Edge/Raspberry Pi live demo — architecture-slide-only unless there's genuine slack after Phase 24 is fully green.