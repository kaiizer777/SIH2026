# WORK.md — SIH25071 Day 2–4: ML Baseline (RF + XGBoost)

Research-verified Aug 20, 2026. Continues from session-done-01.md (Phases 1–9, DONE). Scope here: baseline models only — LSTM/GRU is Day 4–6.

Three corrections folded in below (⚠️) — one is a real bug risk in your current plan (naive split), one is a stale-code trap (old SHAP output shape), one is a wrong-default trap (SMOTE over sample_weight). Fix now, free.

---

## Phase 10 — Train/Test Split Strategy (blocks everything else)
**Target: first 30 min of Day 2. Do not train anything before this is locked. [DONE ✅]**

⚠️ **Correction — a naive random row split will leak.** `synthetic_sensors.csv` is 5,696 rows = 16 zones × 356 days, not 5,696 independent observations. Two failure modes if you `train_test_split(shuffle=True)`:
- **Temporal leakage**: day 200 of zone_07 in train, day 199 of zone_07 in test — the model sees a point adjacent in the same precursor trajectory and trivially "predicts" it. Inflates recall on the exact class that matters most (evacuation), which is the one number a judge will scrutinize.
- **Autocorrelated features**: displacement/vibration/pore_pressure/strain within one zone's Fukuzono curve are heavily serially correlated (you already verified r=0.92–0.97 zone-to-zone). Random split doesn't break that correlation, it just hides it inside "test accuracy."

**Correct approach for this shape: temporal split, not group split.** Zones aren't independent entities you're generalizing across (that's what GroupKFold is for — held-out patients, held-out customers). Here all 16 zones share one clock and you need the model to generalize *forward in time* across all of them. So:
- [x] Sort by `date`, split on a **date cutoff**, not a row shuffle: train = first ~285 days (~80%), test = last ~71 days (~20%) — held out across **all 16 zones simultaneously**.
- [x] This means the evacuation-risk zones' most acute late-stage precursor window should fall mostly in test if the AOI's real event timing lands late in the 356-day window — check this before finalizing the cutoff date; if it doesn't, the test set won't have enough evacuation-class signal to report a meaningful minority-class F1. Verify class balance in the test split before proceeding.
- [x] Do NOT use `GroupKFold` on `zone_id` here — that would hold out entire zones, which tests "does this generalize to an unseen zone's terrain" (a different, harder question you're not claiming to answer) instead of "does this generalize forward in time" (the actual deployment scenario: same mine, same zones, tomorrow's readings).
- [x] If you want a validation split for hyperparameter tuning, take it from the tail of the train period (a second cutoff before the test cutoff), never randomly from train.
- [x] Record the exact cutoff date in `scripts/phase10_split.py` — this is a number you'll get asked to defend.

---

## Phase 11 — Class Imbalance Handling (required deliverable)
**Target: Day 2, 1–2 hrs.**

⚠️ **Correction — pick `sample_weight`, not SMOTE, and be ready to say why.** Current consensus (verified, not assumed): for tree ensembles on tabular data, class weighting is the stronger default over SMOTE — SMOTE synthesizes interpolated points in feature space, which is a real risk here specifically because your features are physically correlated (displacement/vibration/pore_pressure/strain move together per the Fukuzono curve). A synthetic minority sample that interpolates between two real evacuation-class points can land in a physically implausible region of feature space — you'd be training on data that violates your own precursor model. Class weighting reweights the loss on real observations only; nothing fake enters the dataset.

- [DONE ✅] This is **3-class**, not binary — `scale_pos_weight` (XGBoost's binary-only shortcut) doesn't apply. Use `sample_weight` at `.fit()` time for both models.
- [DONE ✅] Compute weights with `sklearn.utils.class_weight.compute_sample_weight(class_weight='balanced', y=y_train)` — inverse-frequency weighting, computed from **train split only** (post-Phase-10 cutoff, never from the full dataset — that's leakage too).
- [DONE ✅] XGBoost: `model.fit(X_train, y_train, sample_weight=weights)`. RF: same param, sklearn's `RandomForestClassifier` accepts `sample_weight` in `.fit()` directly, or set `class_weight='balanced'` at construction (equivalent for RF, but compute explicitly to keep XGBoost and RF using the identical weight vector for a fair baseline comparison).
- [DONE ✅] Do **not** also apply SMOTE on top "for extra safety" — combining both is a documented way to double-count the minority class and overcorrect, not a free improvement.
- [DONE ✅] One sentence for the pitch, memorize it: *"We use class-weighted loss rather than SMOTE because our sensor channels are physically correlated by construction — synthetic interpolation risks generating physically implausible readings. Weighting keeps every training point real."*

---

## Phase 12 — Baseline Model Training
**Target: Day 2–3.**

- [ ] Train `RandomForestClassifier` and `XGBClassifier` (multiclass, `objective='multi:softprob'`) on `data/zone_features.csv` joined against `data/synthetic_sensors.csv` on `zone_id` — confirm join keys match exactly (`zone_01`..`zone_16`, already validated in Phase 6/7, but re-check post-join row count = expected).
- [ ] Feature set: `slope, aspect, curvature, vv_backscatter, vh_backscatter, rainfall_mm` (terrain/SAR, Phase 6) + `displacement_mm_day, vibration, pore_pressure, strain` (sensor, Phase 7). Target: `risk_level` (safe/warning/evacuation).
- [ ] Note the temporal granularity mismatch and handle it explicitly: `zone_features.csv` is 30 SAR acquisition dates, `synthetic_sensors.csv` is 356 daily dates. Forward-fill or nearest-date-join the sparser SAR/terrain features onto the daily sensor rows — don't silently drop to 480 rows, that guts your minority-class sample count. Document which join strategy you used; a judge asking "why do you have two different time granularities" wants to hear you handled it deliberately.
- [ ] Baseline hyperparameters first (don't tune before you have a working end-to-end pipeline): RF `n_estimators=300, max_depth=None`; XGBoost `n_estimators=300, max_depth=6, learning_rate=0.1`. Tune only after Phase 13 metrics are in hand and only if time allows — a tuned model with an unverified split is worse than an untuned model with a correct one.
- [ ] Fit both on the Phase 10 train split with Phase 11 sample weights.

---

## Phase 13 — Evaluation: Minority-Class Metrics as the Headline
**Target: Day 3, 1 hr. This is the section you rehearse out loud.**

- [ ] Generate `sklearn.metrics.classification_report(y_test, y_pred, target_names=['safe','warning','evacuation'])` — report **per-class precision/recall/F1**, not just weighted average.
- [ ] The number that goes in the pitch deck headline slide: **evacuation-class recall** (of all real evacuation events, what fraction did the model catch) and **evacuation-class precision** (of all evacuation alarms raised, what fraction were real). State both — recall alone invites "so it just screams evacuation constantly?" as the follow-up.
- [ ] Confusion matrix, plotted, with the evacuation row/column highlighted (bold border or a distinct color from the safe/warning cells) and annotated with **raw counts, not just normalized percentages** — a judge should see the actual number of missed evacuations (real evacuation predicted as safe), not just a rate. "2 missed out of 848" and "12 missed out of 848" both round to a similar-looking percentage on a small test set; the raw count is the number that actually matters here and the one you'll be asked for directly.
- [ ] **Rehearsed answer, verbatim, know this cold:**
  > *"On this class distribution, a model that always predicts 'safe' scores roughly 60% accuracy and is worthless — it never once catches a real evacuation event. That's exactly why we don't report accuracy as our headline metric. We report precision and recall on the evacuation class specifically, using class-weighted training so the loss function itself penalizes missing a rare evacuation event far more than misclassifying a safe reading. A missed evacuation is a life-safety failure; a false alarm is an inconvenience — our metric choice reflects that asymmetry, our model's don't."*
- [ ] Do this same evaluation for **both** RF and XGBoost — the comparison table (not just XGBoost alone) is a pitch asset per WORKFLOW.md Day 4–6; start the table now with baseline numbers, deep learning model gets added to the same table later.

---

## Phase 14 — SHAP Feature Importance
**Target: Day 3, 1–2 hrs.**

⚠️ **Correction — SHAP's multiclass output shape changed from older tutorials, and pin the version.** `TreeExplainer` on a multiclass model returns an array of shape `(n_samples, n_features, n_classes)` as of **SHAP 0.45.0** (list→ndarray change) — **not** the older list-of-per-class-arrays format (`shap_values[0]`, `shap_values[1]`, ...) you'll see in a lot of cached tutorial code and Stack Overflow answers predating that release. Pin `shap>=0.45.0` explicitly in `requirements.txt` — don't leave the version unconstrained. On an older pinned version, indexing with the new-style syntax below will raise, not silently misbehave, but you don't want to find that out on Day 3.

⚠️ **Second correction — RF and XGBoost are not guaranteed shape-consistent with each other.** There's an open, unresolved SHAP bug (GitHub issue #3432) where `RandomForestClassifier` and `XGBClassifier` behave inconsistently under `model_output='probability'` — RF can require different indexing than XGBoost/HistGradientBoosting in that mode. Don't assume one indexing helper works for both models. **Sidestep this entirely: use `model_output='raw'` (the default) for both models.** You don't need probability-space SHAP for a feature-importance summary plot or for the terrain/SAR tie-back — raw/log-odds contribution ranking is sufficient and keeps RF and XGBoost on an identical code path.

- [ ] `explainer = shap.TreeExplainer(model)` — works natively on both RF and XGBoost, no wrapper needed. Use `feature_perturbation='tree_path_dependent'` (default, no separate background dataset needed) and leave `model_output='raw'` (default) for both models — see correction above.
- [ ] Compute on the **test set**, not train — SHAP on train data shows what the model memorized, not what generalizes; another near-certain "wait, is that overfit?" deflector.
- [ ] **Before indexing, assert the shape**: `assert shap_values.shape == (len(X_test), n_features, 3)` — fail loud here rather than silently plotting the wrong class if a version or model-output mismatch slipped through.
- [ ] To index the evacuation class specifically from the `(n_samples, n_features, n_classes)` array: `shap_values[:, :, 2]` (confirm evacuation is class index 2 in your label encoding before hardcoding this).
- [ ] Summary plot (`shap.summary_plot`) for the evacuation class specifically — this is the plot that goes in the deck, not the raw feature_importances_ bar chart (SHAP handles correlated features, like your r=0.92–0.97 sensor channels, honestly; naive impurity-based importance doesn't and will misleadingly split credit).
- [ ] **Explicit tie-back to geospatial features, this is the interpretability payoff CONTEXT.md calls for**: check where `slope`, `curvature`, and `vv_backscatter`/`vh_backscatter` rank relative to the raw sensor channels. If terrain/SAR features show meaningful SHAP contribution to evacuation-class predictions (not just displacement dominating everything), that's your strongest single pitch point — it means the system isn't just a displacement-threshold detector wearing an ML costume, it's actually using the geospatial fusion you built in Phase 3–6. If terrain/SAR contribution turns out to be negligible, say that too — don't cherry-pick the plot; a judge who asks "what does terrain contribute" and gets a dodge will remember it more than a modest honest number.

---

## Phase 15 — Model Artifact Export
**Target: Day 3, 30 min.**

- [ ] Export both models: `joblib.dump(model, f'models/{model_name}_{version}.joblib')`.
- [ ] `model_version` string **must match the field in `backend/app/schemas.py`** — check the exact type/format expected there (likely a plain string) before inventing a scheme. Suggested format if unconstrained: `rf-v1-20260820` / `xgb-v1-20260820` (algo, version int, date) — deterministic, sortable, and the backend can log which artifact served which prediction without ambiguity.
- [ ] Save alongside the artifact: the feature column order (as a list, e.g. `models/feature_order.json`) and the label encoding (`{0: 'safe', 1: 'warning', 2: 'evacuation'}`) — these are exactly the two things that silently break inference if the backend integration (Day 4–6) reconstructs the DataFrame in a different column order or decodes labels differently than training assumed. This is a real, common bug class — pin it now while it's free.
- [ ] Smoke-test: reload the saved artifact in a fresh script, run one prediction, confirm output shape and class order match what `RiskPrediction` in `schemas.py` expects before calling this phase done.

---

## Phase 16 — End-of-Day-4 Review Checklist
**Target: end of Day 4, 15–20 min self-review.**

- [ ] Split strategy: confirmed temporal cutoff (not random, not zone-grouped), cutoff date recorded, test-set class balance checked and non-degenerate for evacuation class.
- [ ] Both models trained with identical `sample_weight` vector — apples-to-apples comparison, not two different imbalance strategies accidentally.
- [ ] Comparison table exists: RF vs XGBoost, per-class precision/recall/F1, evacuation class highlighted — this table gets a new column when the LSTM/GRU lands in Day 4–6, don't rebuild it from scratch then.
- [ ] SHAP plots generated on test set, evacuation class, terrain/SAR contribution explicitly checked and the honest answer noted (strong or weak — either way, know which).
- [ ] **Confirm max forward-fill staleness** between a sensor row's date and its joined SAR/terrain reading (Phase 12's granularity fix — 30 SAR dates onto 356 daily rows). Compute this as a number of days, not just "handled it" — e.g. "worst case, a row's SAR feature is N days old." Have this bound ready to state if a judge asks how current the terrain/SAR signal is on any given day.
- [ ] Artifacts saved with correct `model_version` format, feature order and label encoding pinned alongside.
- [ ] Confirm unblocked state for Day 4–6 (backend swaps mock `/predict` for real artifact; LSTM/GRU benchmarking begins against this same test split and same metrics).

---

## Notes for the pitch deck (carry forward)
- Temporal split, not random or zone-grouped — deliberate choice matching the deployment scenario (same mine, forward in time), not an oversight. State the cutoff date if asked.
- Class-weighted loss over SMOTE — physically-correlated sensor channels make synthetic interpolation risky; weighting only touches real observations. Have the one-liner ready verbatim (Phase 11).
- Evacuation-class precision AND recall, not accuracy, as the headline — with the "always predicts safe" rebuttal rehearsed cold (Phase 13).
- SHAP ties predictions back to terrain/SAR features, not just raw sensor thresholds — this is the line that separates "ML-flavored threshold alarm" from "actually fusing the geospatial pipeline." Know your real number here, don't oversell it.
- RF vs XGBoost comparison table is a running asset — starts here, gains a column when LSTM/GRU joins in Day 4–6, same metrics throughout.