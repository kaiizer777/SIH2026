"""
tests/test_alert_dedup.py -- Phase 21 alert de-duplication and transition tests.

Tests classify_alert() directly (no running server required).

Key scenarios verified:
  1. 10 consecutive evacuation ticks from None -> exactly 1 upgrade alert
  2. 10 consecutive warning ticks from None -> exactly 1 upgrade alert
  3. Full cycle (10 evac + 5 warning + 3 safe) -> exactly 3 alerts total
     (1 upgrade on entry, 1 downgrade advisory on evac->warning, 1 on warning->safe)
  4. None->safe fires no alert (initial safe state -- nothing to report)
  5. safe->evacuation in one tick (skip warning) -> 1 upgrade
  6. evacuation->safe in one tick (skip warning) -> 1 downgrade advisory

Run with:
    python tests/test_alert_dedup.py
"""
import sys
from pathlib import Path

# Make the backend package importable from repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "backend"))

try:
    from backend.routers.rockfall import classify_alert
except ImportError:
    from routers.rockfall import classify_alert  # type: ignore


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def simulate_ticks(
    ticks: list[str],
    initial_level: str | None,
) -> list[tuple[str | None, str, str]]:
    """
    Run a sequence of risk level ticks through classify_alert() and collect
    all (old_level, new_level, alert_type) tuples where an alert fires.
    """
    last_level = initial_level
    fired: list[tuple[str | None, str, str]] = []
    for new_level in ticks:
        alert_type = classify_alert(last_level, new_level)
        if alert_type is not None:
            fired.append((last_level, new_level, alert_type))
        last_level = new_level
    return fired


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_evacuation_dedup_10_ticks() -> None:
    """
    10 consecutive evacuation ticks from initial state (None) must produce
    EXACTLY 1 upgrade alert -- at the first tick only.
    This is the canonical de-dup test from WORK.md Phase 21.
    """
    ticks = ["evacuation"] * 10
    fired = simulate_ticks(ticks, initial_level=None)

    assert len(fired) == 1, (
        f"FAIL: Expected exactly 1 alert for 10 consecutive evacuation ticks, "
        f"got {len(fired)}: {fired}"
    )
    assert fired[0] == (None, "evacuation", "upgrade"), (
        f"FAIL: Expected (None, 'evacuation', 'upgrade'), got {fired[0]}"
    )
    print("[OK] test_evacuation_dedup_10_ticks: 10 evac ticks -> exactly 1 upgrade alert")


def test_warning_dedup_10_ticks() -> None:
    """10 consecutive warning ticks from None -> exactly 1 upgrade alert."""
    ticks = ["warning"] * 10
    fired = simulate_ticks(ticks, initial_level=None)

    assert len(fired) == 1, (
        f"FAIL: Expected 1 alert for 10 warning ticks, got {len(fired)}: {fired}"
    )
    assert fired[0][2] == "upgrade", f"FAIL: Expected upgrade, got {fired[0][2]}"
    assert fired[0][1] == "warning", f"FAIL: Expected new_level=warning, got {fired[0][1]}"
    print("[OK] test_warning_dedup_10_ticks: 10 warning ticks -> exactly 1 upgrade alert")


def test_full_cycle_18_ticks() -> None:
    """
    Full escalation + de-escalation cycle across 18 ticks:
      - 10 evacuation ticks: 1 upgrade alert at tick 1, 0 at ticks 2-10
      - 5 warning ticks: 1 downgrade advisory at tick 11, 0 at ticks 12-15
      - 3 safe ticks: 1 downgrade advisory at tick 16, 0 at ticks 17-18
    Total: exactly 3 alerts (1 upgrade + 2 downgrade advisories).
    """
    ticks = ["evacuation"] * 10 + ["warning"] * 5 + ["safe"] * 3
    fired = simulate_ticks(ticks, initial_level=None)

    assert len(fired) == 3, (
        f"FAIL: Expected exactly 3 alerts in full cycle, got {len(fired)}: {fired}"
    )

    alert_types = [f[2] for f in fired]
    assert alert_types == ["upgrade", "downgrade", "downgrade"], (
        f"FAIL: Expected [upgrade, downgrade, downgrade], got {alert_types}"
    )

    # Validate each transition
    assert fired[0] == (None, "evacuation", "upgrade"), (
        f"FAIL: First alert wrong: {fired[0]}"
    )
    assert fired[1] == ("evacuation", "warning", "downgrade"), (
        f"FAIL: Second alert wrong (evac->warning): {fired[1]}"
    )
    assert fired[2] == ("warning", "safe", "downgrade"), (
        f"FAIL: Third alert wrong (warning->safe): {fired[2]}"
    )
    print("[OK] test_full_cycle_18_ticks: 18 ticks -> exactly 3 alerts (1 upgrade + 2 downgrade)")


def test_initial_safe_no_alert() -> None:
    """
    None->safe must NOT fire any alert.
    The zone has never been in a dangerous state -- nothing to report.
    """
    fired = simulate_ticks(["safe"] * 5, initial_level=None)
    assert len(fired) == 0, (
        f"FAIL: None->safe should produce no alerts, got {len(fired)}: {fired}"
    )
    print("[OK] test_initial_safe_no_alert: None->safe fires no alert")


def test_skip_class_upgrade_safe_to_evac() -> None:
    """safe->evacuation in one tick (skipping warning) -> exactly 1 upgrade alert."""
    fired = simulate_ticks(["evacuation"], initial_level="safe")
    assert len(fired) == 1, f"FAIL: Expected 1 alert, got {len(fired)}: {fired}"
    assert fired[0] == ("safe", "evacuation", "upgrade"), (
        f"FAIL: Expected (safe, evacuation, upgrade), got {fired[0]}"
    )
    print("[OK] test_skip_class_upgrade_safe_to_evac: safe->evac in 1 tick -> 1 upgrade")


def test_skip_class_downgrade_evac_to_safe() -> None:
    """evacuation->safe in one tick (skipping warning) -> exactly 1 downgrade advisory."""
    fired = simulate_ticks(["safe"], initial_level="evacuation")
    assert len(fired) == 1, f"FAIL: Expected 1 alert, got {len(fired)}: {fired}"
    assert fired[0] == ("evacuation", "safe", "downgrade"), (
        f"FAIL: Expected (evacuation, safe, downgrade), got {fired[0]}"
    )
    print("[OK] test_skip_class_downgrade_evac_to_safe: evac->safe in 1 tick -> 1 downgrade")


def test_warning_to_evacuation_upgrade() -> None:
    """warning->evacuation -> upgrade (escalation within trigger levels)."""
    fired = simulate_ticks(["evacuation"], initial_level="warning")
    assert len(fired) == 1
    assert fired[0] == ("warning", "evacuation", "upgrade"), f"FAIL: {fired[0]}"
    print("[OK] test_warning_to_evacuation_upgrade: warning->evac -> upgrade")


def test_safe_sustained_no_alert() -> None:
    """A zone staying safe for many ticks never fires any alert."""
    fired = simulate_ticks(["safe"] * 50, initial_level="safe")
    assert len(fired) == 0, f"FAIL: Sustained safe should produce 0 alerts, got {len(fired)}"
    print("[OK] test_safe_sustained_no_alert: 50 consecutive safe ticks -> 0 alerts")


def test_evacuation_sustained_then_new_evac_spike() -> None:
    """
    Zone at evacuation, drops to safe, re-enters evacuation.
    Should produce exactly: 1 downgrade (evac->safe) + 1 upgrade (safe->evac).
    The second evacuation entry is a new crossing -- must fire a new alert.
    """
    ticks = (
        ["evacuation"] * 5  # initial sustained evac -- 1 alert already fired (from None)
        + ["safe"] * 3      # downgrade: 1 advisory
        + ["evacuation"] * 5  # new crossing into evac: 1 upgrade
    )
    fired = simulate_ticks(ticks, initial_level=None)

    assert len(fired) == 3, (
        f"FAIL: Expected 3 alerts (1 initial upgrade + 1 downgrade + 1 re-entry upgrade), "
        f"got {len(fired)}: {fired}"
    )
    assert fired[0][2] == "upgrade"   # None->evac
    assert fired[1][2] == "downgrade" # evac->safe
    assert fired[2][2] == "upgrade"   # safe->evac (re-entry)
    print("[OK] test_evacuation_sustained_then_new_evac_spike: re-entry fires correct new alert")


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Phase 21 Alert De-duplication Tests")
    print("=" * 60)
    print()

    test_evacuation_dedup_10_ticks()
    test_warning_dedup_10_ticks()
    test_full_cycle_18_ticks()
    test_initial_safe_no_alert()
    test_skip_class_upgrade_safe_to_evac()
    test_skip_class_downgrade_evac_to_safe()
    test_warning_to_evacuation_upgrade()
    test_safe_sustained_no_alert()
    test_evacuation_sustained_then_new_evac_spike()

    print()
    print("[PASS] All 9 alert de-duplication tests passed.")
    print()
