"""Tests for the corrected active-particle motility dynamics.

The corrected model lives in ``models/motility_simulation/corrected`` and
overrides three defects of the vendored upstream simulator.  These tests pin the
behaviour each correction is supposed to produce, so a regression shows up as a
failing assertion rather than as a shifted figure.

The upstream package itself is checksummed provenance; one test asserts that the
correction did not touch it.
"""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

PROJECT = Path(__file__).resolve().parents[1]
CORRECTED_SRC = PROJECT / "models/motility_simulation/corrected/src"
UPSTREAM = PROJECT / "models/motility_simulation/upstream"
for path in (str(CORRECTED_SRC), str(UPSTREAM / "src")):
    if path not in sys.path:
        sys.path.insert(0, path)

import salmonella_motility_corrected as smc  # noqa: E402
from salmonella_motility_corrected.vendored import (  # noqa: E402
    make_obstacle_field as upstream_make_obstacle_field,
)
from salmonella_motility_corrected.vendored import (  # noqa: E402
    nearest_overlapping_obstacle,
)

make_obstacle_field = smc.make_obstacle_field

ADOPTED_TABLE = (
    PROJECT / "data/processed/motility_adopted_parameters/motility_summary_parameters_adopted.csv"
)


def base_config(dt_s: float = 0.0025, duration_s: float = 4.0, n_cells: int = 12) -> dict:
    """Return the frozen upstream config with a short, cheap run configured."""
    config = yaml.safe_load((UPSTREAM / "data/config.yml").read_text(encoding="utf-8"))
    config["simulation"]["dt_s"] = dt_s
    config["simulation"]["track_duration_s"] = duration_s
    config["simulation"]["n_cells"] = n_cells
    return config


@pytest.fixture(scope="module")
def parameters() -> dict:
    if not ADOPTED_TABLE.exists():
        pytest.skip("adopted parameter table has not been derived")
    return smc.load_parameter_table(ADOPTED_TABLE)


# ---------------------------------------------------------------------------
# Correction 1: instantaneous reorientation
# ---------------------------------------------------------------------------


def test_reorientation_duration_is_not_a_model_parameter() -> None:
    """The retired parameter is gone, not zeroed."""
    params = smc.MotilityParameters("a", "b", "#000", 1, 1, 1, 1, 1, 1, 0, 1)
    assert not hasattr(params, "reorientation_duration_s")
    assert "reorientation_duration_s" not in smc.REQUIRED_COLUMNS
    assert "reorientation_duration_s" in smc.RETIRED_COLUMNS


def test_adopted_table_has_dropped_the_retired_column() -> None:
    """The canonical table the panels read carries no retired parameter."""
    if not ADOPTED_TABLE.exists():
        pytest.skip("adopted parameter table has not been derived")
    assert smc.ignored_columns(ADOPTED_TABLE) == []


def test_reorient_state_is_never_occupied(parameters: dict) -> None:
    """A corrected cell always advances; it never parks in the reorient state."""
    config = base_config()
    result = smc.simulate_population(config, parameters[("WT", "liquid")], None, 1000)
    assert result["reorientations"] > 0, "no turn happened, so the test proves nothing"
    assert not np.any(result["state_history"] == config["states"]["reorient"])


def test_liquid_diffusivity_matches_the_calibrated_persistence_relation(
    parameters: dict,
) -> None:
    """The simulated D_eff reproduces v^2 tau / 2, the relation the fit targets.

    The mean squared displacement of a persistent random walk at a finite lag is
    ``4 D [t - tau (1 - exp(-t / tau))]``, so the plain ``MSD / (4 t)`` estimator
    is biased low by about ``tau / t``.  The bias is divided out here, which is
    exactly the check that the dwell removal restored: with the upstream dwell in
    place this ratio was about 0.6.
    """
    params = parameters[("WT", "liquid")]
    config = base_config(duration_s=20.0, n_cells=26)
    tau = 1.0 / (
        params.rotational_diffusion_rad2_s
        + params.reorientation_rate_s * (1.0 - math.exp(-(params.turn_angle_sd_rad**2) / 2.0))
    )
    expected = params.run_speed_um_s**2 * tau / 2.0

    lag_s = 2.0
    lag_steps = int(round(lag_s / config["simulation"]["dt_s"]))
    estimates = []
    for seed in range(1000, 1006):
        result = smc.simulate_population(config, params, None, seed)
        history, motile = result["history"], result["is_motile"]
        origins = np.arange(0, history.shape[0] - 1 - lag_steps + 1, lag_steps)
        jumps = history[origins + lag_steps][:, motile, :] - history[origins][:, motile, :]
        estimates.append(float((jumps**2).sum(axis=2).mean()) / (4.0 * lag_s))
    bias = 1.0 - (tau / lag_s) * (1.0 - math.exp(-lag_s / tau))
    corrected = float(np.mean(estimates)) / bias
    assert corrected == pytest.approx(expected, rel=0.12)


# ---------------------------------------------------------------------------
# Correction 2: the enlarged domain keeps the published mesh density
# ---------------------------------------------------------------------------


def test_obstacle_count_scales_with_box_area() -> None:
    config = base_config()
    for scale in (2, 4, 8):
        scaled = smc.scaled_config(config, scale)
        assert scaled["obstacles"]["count"] == config["obstacles"]["count"] * scale**2
        assert scaled["simulation"]["box_width_um"] == pytest.approx(
            config["simulation"]["box_width_um"] * scale
        )


def test_enlarged_box_preserves_the_obstacle_area_fraction() -> None:
    """Scaling the count with area holds the mesh density, within seed scatter."""
    config = base_config()
    published = [
        smc.obstacle_area_fraction(
            make_obstacle_field(config, seed=seed),
            config["simulation"]["box_width_um"],
            config["simulation"]["box_height_um"],
        )
        for seed in range(1300, 1320)
    ]
    scaled = smc.scaled_config(config, 8)
    enlarged = smc.obstacle_area_fraction(
        make_obstacle_field(scaled, seed=1300),
        scaled["simulation"]["box_width_um"],
        scaled["simulation"]["box_height_um"],
    )
    assert enlarged == pytest.approx(float(np.mean(published)), rel=0.06)


def test_obstacle_index_matches_the_upstream_linear_scan() -> None:
    """The grid index is an optimisation, not a change of behaviour."""
    config = base_config()
    field = make_obstacle_field(config, seed=1300)
    width = config["simulation"]["box_width_um"]
    height = config["simulation"]["box_height_um"]
    index = smc.ObstacleIndex(field, width, height)
    rng = np.random.default_rng(0)
    points = rng.uniform([0.0, 0.0], [width, height], size=(20000, 2))
    for x, y in points:
        assert index.nearest_overlapping(x, y) == nearest_overlapping_obstacle(x, y, field)


def test_fast_generator_matches_upstream() -> None:
    """The grid-accelerated generator is an optimisation, not a new field.

    It consumes the random stream in the upstream order and applies the upstream
    acceptance rule, so the field is identical disk for disk.
    """
    config = base_config()
    for scale in (1, 2, 4):
        scaled = smc.scaled_config(config, scale)
        for seed in (1300, 1301, 1350):
            fast = smc.make_obstacle_field(scaled, seed=seed)
            slow = upstream_make_obstacle_field(scaled, seed=seed)
            assert np.array_equal(fast.x_um, slow.x_um)
            assert np.array_equal(fast.y_um, slow.y_um)
            assert np.array_equal(fast.r_um, slow.r_um)


def test_obstacle_index_handles_an_empty_field() -> None:
    index = smc.ObstacleIndex(None, 148.0, 96.0)
    assert index.n_obstacles == 0
    assert index.nearest_overlapping(10.0, 10.0) is None


# ---------------------------------------------------------------------------
# Correction 3: one stall draw per contact event
# ---------------------------------------------------------------------------


def test_realised_stall_rate_matches_the_per_encounter_probability(
    parameters: dict,
) -> None:
    """Stalls per contact event reproduce the nominal probability."""
    params = parameters[("WT", "agarose")]
    config = base_config(duration_s=20.0, n_cells=26)
    contacts = stalls = 0
    for seed in range(1000, 1008):
        field = make_obstacle_field(config, seed=seed + 300)
        result = smc.simulate_population(config, params, field, seed)
        contacts += result["contact_events"]
        stalls += result["stall_entries"]
    assert contacts > 500, "too few encounters to estimate a rate"
    assert stalls / contacts == pytest.approx(params.stall_probability, rel=0.15)


def test_stall_rate_does_not_drift_with_the_time_step(parameters: dict) -> None:
    """The per-encounter rate is a model property, not a step-size artefact.

    Under the upstream per-time-step rule the stall occupancy rose without limit
    as the step shrank.  Here the realised per-encounter probability holds across
    an eightfold change of step.
    """
    params = parameters[("WT", "agarose")]
    rates = []
    for dt_s in (0.005, 0.0025, 0.000625):
        config = base_config(dt_s=dt_s, duration_s=10.0, n_cells=26)
        contacts = stalls = 0
        for seed in range(1000, 1004):
            field = make_obstacle_field(config, seed=seed + 300)
            result = smc.simulate_population(config, params, field, seed)
            contacts += result["contact_events"]
            stalls += result["stall_entries"]
        rates.append(stalls / contacts)
    assert max(rates) / min(rates) < 1.35


def test_continued_contact_draws_no_second_stall(parameters: dict) -> None:
    """A cell already touching a disk is never re-tested against the same disk.

    With one disk covering most of the box every motile cell meets it, so the
    number of stall entries can never exceed the number of contact events.
    """
    config = base_config(duration_s=10.0, n_cells=8)
    params = parameters[("WT", "agarose")]
    field = smc.ObstacleField(
        x_um=np.array([74.0]), y_um=np.array([48.0]), r_um=np.array([30.0])
    )
    result = smc.simulate_population(config, params, field, 1000)
    assert result["contact_events"] > 0
    assert result["stall_entries"] <= result["contact_events"]


# ---------------------------------------------------------------------------
# The vendored upstream stays untouched
# ---------------------------------------------------------------------------


def test_upstream_checksums_still_verify() -> None:
    """The correction is additive: vendored provenance is unchanged."""
    completed = subprocess.run(
        ["shasum", "-a", "256", "-c", "CHECKSUMS.sha256"],
        cwd=UPSTREAM,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
