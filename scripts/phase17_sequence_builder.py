"""
Phase 17 - LSTM/GRU Sequence Builder
=====================================
SIH25071 Rockfall Prediction

Builds 14-day sliding-window sequences per zone from the raw sensor data,
joined against zone_features.csv using the IDENTICAL merge_asof forward-fill
logic from scripts/phase12_baseline_training.py (sar_forward_fill), so LSTM
input features are byte-for-byte consistent with what RF/XGBoost trained on.

Design decisions (locked, see WORK.md Phase 17):
  - Window length: 14 days
  - Label: the LAST timestep in the window (predict current risk from trailing history)
  - Windows never cross a zone_id boundary
  - Windows are allowed to pull history from train.csv when the target day
    falls in val.csv/test.csv but the window's start predates that split's
    own start date. The label/split assignment always follows the TARGET day,
    not the history. This is not leakage: Phase 10's temporal cutoff still
    strictly gates what labels are visible when — only the input feature
    window reaches backward, exactly as a real deployed model would have
    access to prior days' readings regardless of which "split" they fall in.
  - Windows are NEVER allowed to pull history from AFTER the split's cutoff
    (that would be real leakage - seeing future val/test rows during "train" eval,
    or seeing test rows during val eval). Enforced explicitly below.

Run from repo root: python scripts/phase17_sequence_builder.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths (mirrors phase12_baseline_training.py exactly)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
MODELS_DIR = REPO_ROOT / "models"

FULL_SENSOR_CSV = DATA_DIR / "synthetic_sensors.csv"  # full 5696-row raw file, not a split
ZF_CSV = DATA_DIR / "zone_features.csv"
SPLIT_METADATA_JSON = DATA_DIR / "split_metadata.json"

OUT_DIR = DATA_DIR / "sequences"
OUT_DIR.mkdir(exist_ok=True)

WINDOW = 14

LABEL_ENCODING = {"safe": 0, "warning": 1, "evacuation": 2}
LABEL_NAMES = ["safe", "warning", "evacuation"]

SAR_TERRAIN_FEATURES = ["slope", "aspect", "curvature", "vv_backscatter", "vh_backscatter", "rainfall_mm"]
SENSOR_FEATURES = ["displacement_mm_day", "vibration", "pore_pressure", "strain"]
FEATURE_ORDER = SENSOR_FEATURES + SAR_TERRAIN_FEATURES  # must match models/feature_order.json exactly


# ---------------------------------------------------------------------------
# Reused verbatim from phase12_baseline_training.py (do not fork this logic)
# ---------------------------------------------------------------------------

def sar_forward_fill(sensor_df: pd.DataFrame, zf: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    original_count = len(sensor_df)
    sensor_df = sensor_df.copy()
    sensor_df["_date"] = sensor_df["timestamp"].dt.normalize().dt.tz_localize(None)

    zf = zf.copy()
    zf["_zf_date"] = pd.to_datetime(zf["date"])
    zf = zf.sort_values(["zone_id", "_zf_date"]).reset_index(drop=True)

    zf = zf.rename(columns={"rainfall_mm": "_sar_rainfall_mm"})
    sar_cols_left = ["slope", "aspect", "curvature", "vv_backscatter", "vh_backscatter", "_sar_rainfall_mm"]
    zf_cols = ["zone_id", "_zf_date"] + sar_cols_left

    results = []
    max_staleness = 0

    for zone_id, zone_sensor in sensor_df.groupby("zone_id", sort=False):
        zone_zf = zf.loc[zf["zone_id"] == zone_id, zf_cols].copy()
        zone_sensor = zone_sensor.sort_values("_date")

        merged = pd.merge_asof(
            zone_sensor, zone_zf,
            left_on="_date", right_on="_zf_date",
            by="zone_id", direction="backward",
        )

        staleness = (merged["_date"] - merged["_zf_date"]).dt.days
        zone_max = staleness.max()
        if pd.notna(zone_max):
            max_staleness = max(max_staleness, int(zone_max))

        results.append(merged)

    joined = pd.concat(results, ignore_index=True)

    assert len(joined) == original_count, (
        f"Row count changed after SAR join! Before: {original_count}, After: {len(joined)}"
    )

    joined = joined.drop(columns=["rainfall_mm"]).rename(columns={"_sar_rainfall_mm": "rainfall_mm"})

    print(f"    max forward-fill staleness: {max_staleness} days")
    return joined, max_staleness


# ---------------------------------------------------------------------------
# Sequence construction
# ---------------------------------------------------------------------------

def build_sequences_for_zone(
    zone_df: pd.DataFrame,
    zone_id: str,
    val_cutoff: pd.Timestamp,
    test_cutoff: pd.Timestamp,
) -> list[dict]:
    """
    zone_df: full joined (sensor + SAR/terrain) rows for ONE zone, sorted by date,
             covering the ENTIRE 356-day range (not pre-split).
    Returns one dict per valid window: features (14, 10), label, target_date, split.
    """
    zone_df = zone_df.sort_values("_date").reset_index(drop=True)
    n = len(zone_df)
    sequences = []

    for end_idx in range(WINDOW - 1, n):
        start_idx = end_idx - WINDOW + 1
        window_df = zone_df.iloc[start_idx:end_idx + 1]

        target_date = zone_df.loc[end_idx, "_date"]
        window_start_date = zone_df.loc[start_idx, "_date"]

        # Determine which split the TARGET day belongs to (this drives the label's split)
        if target_date >= test_cutoff:
            split = "test"
        elif target_date >= val_cutoff:
            split = "val"
        else:
            split = "train"

        # Hard leakage guard: window must never reach INTO OR PAST the split boundary
        # that lies ahead of the target's own split. i.e. a train-target window must
        # not touch val/test dates; a val-target window must not touch test dates.
        # (It IS allowed to reach backward past its own split's start into train - that's
        #  the deliberate Option B choice, not a violation.)
        if split == "train" and window_start_date >= val_cutoff:
            continue  # shouldn't happen given target < val_cutoff and window is backward, but assert defensively
        if split == "val":
            # window must not contain any date >= test_cutoff (impossible since target < test_cutoff
            # and window is monotonic backward from target, but kept explicit for clarity)
            assert window_df["_date"].max() < test_cutoff, "val window leaked into test range"
        if split == "test":
            assert True  # test windows may reach into val/train history freely - no future data used

        feat_matrix = window_df[FEATURE_ORDER].to_numpy(dtype=np.float32)
        if np.isnan(feat_matrix).any():
            continue  # incomplete window (shouldn't occur post-forward-fill, skip defensively)

        label_str = zone_df.loc[end_idx, "risk_level"]
        sequences.append({
            "zone_id": zone_id,
            "target_date": target_date.strftime("%Y-%m-%d"),
            "window_start_date": window_start_date.strftime("%Y-%m-%d"),
            "split": split,
            "features": feat_matrix,  # shape (14, 10)
            "label": LABEL_ENCODING[label_str],
        })

    return sequences


def main() -> None:
    print("=" * 60)
    print("  Phase 17 - LSTM/GRU Sequence Builder")
    print("=" * 60)

    print("\n[1] Loading full sensor data + zone_features + split cutoffs ...")
    sensor_df = pd.read_csv(FULL_SENSOR_CSV, parse_dates=["timestamp"])
    zf = pd.read_csv(ZF_CSV)
    split_meta = json.loads(SPLIT_METADATA_JSON.read_text())

    val_cutoff = pd.Timestamp(split_meta["cutoffs"]["val_cutoff_date"])
    test_cutoff = pd.Timestamp(split_meta["cutoffs"]["test_cutoff_date"])
    print(f"  val_cutoff={val_cutoff.date()}  test_cutoff={test_cutoff.date()}")
    print(f"  total raw rows: {len(sensor_df)}  zones: {sensor_df['zone_id'].nunique()}")

    print("\n[2] SAR forward-fill join on FULL dataset (identical logic to Phase 12) ...")
    joined, max_staleness = sar_forward_fill(sensor_df, zf)
    assert len(joined) == len(sensor_df), "row count changed after join"
    print(f"  joined rows: {len(joined)}  max staleness: {max_staleness} days (expect ~23, matches Phase 16)")

    print("\n[3] Building 14-day windows per zone ...")
    all_sequences: list[dict] = []
    for zone_id, zone_df in joined.groupby("zone_id", sort=True):
        zone_seqs = build_sequences_for_zone(zone_df, zone_id, val_cutoff, test_cutoff)
        all_sequences.extend(zone_seqs)

    print(f"  total sequences built: {len(all_sequences)}")

    by_split = {"train": [], "val": [], "test": []}
    for s in all_sequences:
        by_split[s["split"]].append(s)

    print("\n[4] Sequence counts and class balance per split:")
    for split_name in ["train", "val", "test"]:
        seqs = by_split[split_name]
        labels = [s["label"] for s in seqs]
        counts = {name: labels.count(LABEL_ENCODING[name]) for name in LABEL_NAMES}
        total = len(seqs)
        pct = {k: round(100 * v / total, 2) if total else 0 for k, v in counts.items()}
        print(f"  {split_name:5s}: {total:5d} sequences | "
              f"safe={counts['safe']} ({pct['safe']}%)  "
              f"warning={counts['warning']} ({pct['warning']}%)  "
              f"evacuation={counts['evacuation']} ({pct['evacuation']}%)")

    # Sanity flag: evacuation class needs to be non-trivial in val/test to report a meaningful F1
    for split_name in ["val", "test"]:
        evac_count = sum(1 for s in by_split[split_name] if s["label"] == LABEL_ENCODING["evacuation"])
        if evac_count < 30:
            print(f"\n  !! WARNING: {split_name} evacuation-class sequence count ({evac_count}) is thin. "
                  f"F1 on this class may be noisy/unstable. Consider this before treating the "
                  f"LSTM evacuation F1 as directly comparable to RF/XGBoost's row-level numbers.")

    print("\n[5] Saving sequences to disk (train/val/test .npz + metadata json) ...")
    for split_name in ["train", "val", "test"]:
        seqs = by_split[split_name]
        if not seqs:
            continue
        X = np.stack([s["features"] for s in seqs])  # (n, 14, 10)
        y = np.array([s["label"] for s in seqs], dtype=np.int64)
        meta = [{"zone_id": s["zone_id"], "target_date": s["target_date"],
                 "window_start_date": s["window_start_date"]} for s in seqs]

        out_path = OUT_DIR / f"{split_name}_sequences.npz"
        np.savez_compressed(out_path, X=X, y=y)
        (OUT_DIR / f"{split_name}_sequences_meta.json").write_text(json.dumps(meta, indent=2))
        print(f"  {split_name}: X{X.shape} y{y.shape} -> {out_path}")

    manifest = {
        "window_length": WINDOW,
        "feature_order": FEATURE_ORDER,
        "label_encoding": LABEL_ENCODING,
        "val_cutoff": str(val_cutoff.date()),
        "test_cutoff": str(test_cutoff.date()),
        "max_sar_staleness_days": max_staleness,
        "history_boundary_policy": (
            "Windows may pull history from an earlier split (e.g. a val-target window "
            "reaching back into train dates) but NEVER from a later split. Label/split "
            "assignment always follows the target (last-timestep) date only."
        ),
        "counts": {
            split_name: len(by_split[split_name]) for split_name in ["train", "val", "test"]
        },
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"\n  manifest.json written to {OUT_DIR / 'manifest.json'}")

    print("\n" + "=" * 60)
    print("  Phase 17 complete. Sequences ready for Phase 18 (LSTM/GRU training).")
    print("=" * 60)


if __name__ == "__main__":
    main()
