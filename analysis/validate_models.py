"""Deterministic verification and structural checks for the simulation sandbox."""
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

from individual_microsimulation import ARM_CONFIGS, simulate_arm
from service_queue_simulation import CONFIGS, generate_random_stream, simulate_one


def validate_individual_model() -> None:
    seed = 314159
    screen_a, weekly_a = simulate_arm(ARM_CONFIGS["screen_agent"], n=400, weeks=6, seed=seed)
    screen_b, weekly_b = simulate_arm(ARM_CONFIGS["screen_agent"], n=400, weeks=6, seed=seed)
    pd.testing.assert_frame_equal(screen_a, screen_b)
    pd.testing.assert_frame_equal(weekly_a, weekly_b)

    robot, _ = simulate_arm(ARM_CONFIGS["robot_hitl"], n=400, weeks=6, seed=seed)
    np.testing.assert_allclose(screen_a["baseline_phq9"], robot["baseline_phq9"])

    assert screen_a["week12_phq9_locf"].between(0, 27).all()
    assert (screen_a["engaged_sessions"] <= 6).all()
    assert (screen_a["missed_crises"] <= screen_a["crisis_weeks"]).all()
    assert screen_a["physical_near_misses"].sum() == 0
    assert screen_a["fallback_sessions"].sum() == 0
    assert robot["physical_near_misses"].ge(0).all()
    assert robot["downtime_sessions"].ge(robot["fallback_sessions"]).all()


def validate_queue_model() -> None:
    screen_cfg = replace(CONFIGS["screen"], days=7, warmup_days=2, arrivals_per_day=12.0)
    robot_cfg = replace(CONFIGS["robot_hitl"], days=7, warmup_days=2, arrivals_per_day=12.0)
    a = simulate_one(screen_cfg, seed=271828)
    b = simulate_one(screen_cfg, seed=271828)
    assert a == b
    assert a["arrivals"] == a["completed"] + a["abandoned"]
    assert 0 <= a["missed_high_acuity_percent"] <= 100
    assert 0 <= a["abandonment_percent"] <= 100
    assert a["warmup_days"] == 2
    assert a["observation_days"] == 7

    # Common-random-number pathways must see the same observed demand.
    robot = simulate_one(robot_cfg, seed=271828)
    assert robot["arrivals"] == a["arrivals"]
    screen_stream = generate_random_stream(screen_cfg, seed=271828)[1]
    robot_stream = generate_random_stream(robot_cfg, seed=271828)[1]
    assert screen_stream == robot_stream

    manual = simulate_one(
        replace(CONFIGS["manual"], days=7, warmup_days=2, arrivals_per_day=12.0),
        seed=271828,
    )
    assert manual["failover_percent"] == 0
    assert manual["physical_resets_per_day"] == 0
    assert manual["incomplete_rework_percent"] == 0


def main() -> None:
    validate_individual_model()
    validate_queue_model()
    print("All deterministic verification checks passed.")


if __name__ == "__main__":
    main()
