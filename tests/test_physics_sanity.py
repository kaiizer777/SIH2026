"""
tests/test_physics_sanity.py -- Phase 21 Physics Generator Sanity Checks.

Validates that step_zone() produces physically reasonable values over a full
356-day simulation cycle for each of the three risk tiers.
"""
import sys
import numpy as np
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))
sys.path.insert(0, str(_REPO_ROOT / "backend"))

from app.physics_generator import (
    load_generator_data,
    initialize_all_zone_states,
    step_zone,
    _T_PEAK_FAILURE,
)
from app.schemas import WARNING_DISPLACEMENT_MAX_MM_DAY


def test_physics_sanity():
    api_norm, rainfall, sim_dates, risk_map, multipliers = load_generator_data(_REPO_ROOT)
    states = initialize_all_zone_states(risk_map, multipliers)

    # Pick one zone from each tier
    safe_zone = next(z for z, s in states.items() if s.tier == "safe")
    warning_zone = next(z for z, s in states.items() if s.tier == "warning")
    evac_zone = next(z for z, s in states.items() if s.tier == "evacuation")

    test_zones = [
        ("Safe Tier", states[safe_zone]),
        ("Warning Tier", states[warning_zone]),
        ("Evacuation Tier", states[evac_zone]),
    ]

    for label, state in test_zones:
        print(f"\n--- Testing {label} (zone: {state.zone_id}, mult: {state.mult:.4f}) ---")
        
        # Ensure we start at t=0
        state.current_t = 0
        
        readings = []
        for i in range(356):
            # t before step_zone
            current_t = state.current_t
            r = step_zone(state, api_norm, rainfall, sim_dates)
            readings.append(r)
            
            # 1. NON-NEGATIVE ASSERTIONS
            assert r.displacement_mm_day >= 0, f"t={current_t}: Negative displacement {r.displacement_mm_day}"
            assert r.vibration >= 0, f"t={current_t}: Negative vibration {r.vibration}"
            assert r.pore_pressure >= 0, f"t={current_t}: Negative pore_pressure {r.pore_pressure}"
            assert r.strain >= 0, f"t={current_t}: Negative strain {r.strain}"
            assert r.rainfall_mm >= 0, f"t={current_t}: Negative rainfall {r.rainfall_mm}"

        # Get displacement series
        disp_series = [r.displacement_mm_day for r in readings]
        
        # 2. EVACUATION-TIER FUKUZONO BEHAVIOR
        if state.tier == "evacuation":
            evac_ticks_near_peak = 0
            # Test window: t=300 to t=_T_PEAK_FAILURE (338)
            window_len = _T_PEAK_FAILURE - 300 + 1
            for t in range(300, _T_PEAK_FAILURE + 1):
                if readings[t].risk_level.value == "evacuation":
                    evac_ticks_near_peak += 1
            
            percent_evac = (evac_ticks_near_peak / window_len) * 100
            print(f"  Evacuation behavior: {percent_evac:.1f}% ticks in evac band near peak (t=300..{_T_PEAK_FAILURE})")
            assert percent_evac > 50.0, (
                f"FAIL: Fukuzono acceleration weak. Only {percent_evac:.1f}% ticks "
                f"in evac band near peak."
            )

        # 3. SAFE-TIER RISK BOUNDARY
        if state.tier == "safe":
            spikes = sum(1 for r in readings if r.risk_level.value == "evacuation")
            print(f"  Safe boundary: {spikes} ticks breached evacuation threshold")
            assert spikes == 0, f"FAIL: Safe zone spiked into evacuation territory {spikes} times"

        # 4. WRAPAROUND DISCONTINUITY CHECK
        # Compare jump from t=355 -> t=0 against the typical distribution of jumps.
        # Run one more tick to get the wrap-around reading
        wrap_reading = step_zone(state, api_norm, rainfall, sim_dates)
        
        jumps = [abs(disp_series[i] - disp_series[i-1]) for i in range(1, 356)]
        median_jump = np.median(jumps)
        max_normal_jump = np.max(jumps)
        
        wrap_jump = abs(wrap_reading.displacement_mm_day - disp_series[-1])
        
        print(f"  Wraparound jump (t=355 -> t=0): {wrap_jump:.2f} mm/day")
        print(f"  Normal jumps: median={median_jump:.2f}, max={max_normal_jump:.2f}")
        
        # We assert the wrap jump isn't more than 2.5x the max normal jump during the year
        # (gives leeway for the rainfall series discontinuity but catches wild glitches)
        allowable_jump = max_normal_jump * 2.5 + 5.0
        assert wrap_jump <= allowable_jump, (
            f"FAIL: Wraparound jump ({wrap_jump:.2f}) is wildly discontinuous "
            f"from normal max jump ({max_normal_jump:.2f})"
        )

        print("  [OK] All assertions passed for this tier.")

if __name__ == "__main__":
    test_physics_sanity()
    print("\n[PASS] All Physics Sanity tests passed.")
