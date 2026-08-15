#!/usr/bin/env python3
"""Derive a motility parameter table with one global, literature-anchored turn angle.

Why this variant exists
-----------------------
The delivered table gives every phenotype-by-medium row its own
``turn_angle_sd_rad``.  Those six values have no source.  The first version of
the simulator was written by a language model, and the turn width was never
measured and never taken from a publication.  One row, ``PproB``, carries less
than half the width of the others, which no measurement of ours supports.  See
``docs/revision_2026-08-12/motility_parameter_sources.md``, section 3.

This module builds the alternative: a single turn width for all six rows, fixed
by the only published number the source review could verify.

The anchor
----------
Taute KM, Gude S, Tans SJ, Shimizu TS (2015) Nat Commun 6:8776,
`10.1038/ncomms9776 <https://doi.org/10.1038/ncomms9776>`_, PMID 26522289.
They report a population mean turn angle of 57 deg from 8058 turns of
*E. coli* AW405.

The simulator draws ``theta += rng.normal(0, sigma)``.  For a zero-mean normal
the mean absolute turn is ``sigma * sqrt(2 / pi)``.  Matching that to 57 deg
gives ``sigma = radians(57) / sqrt(2 / pi) = 1.2468 rad``.

Two limits of the anchor, stated plainly:

* Taute et al. measured in three dimensions.  This simulator is two-dimensional.
  The mapping used here matches the mean turn *magnitude*, which is the
  comparison the repository's own source review already makes.
* A wrapped heading has a period of 2*pi, so draws beyond +/-pi fold back.  At
  ``sigma = 1.2468`` that is 1.2 % of draws, which lowers the realised mean
  turn magnitude by about 2 %.  The effect is small and is reported by
  ``turn_angle_diagnostics``.

Method
------
Identical to ``analyses/motility_parameter_calibration/calibrate.py`` except for
one substitution: ``turn_angle_sd_rad`` becomes the global value in every row
before the persistence closure runs.  The closure is unchanged,

    tau = 1 / (D_r + lambda * (1 - exp(-sigma^2 / 2)))

and ``rotational_diffusion_rad2_s`` and ``reorientation_rate_s`` keep their
delivered ratio while both are scaled by the single factor that makes the model
tau equal the measured tau.  Every other column passes through as delivered.

Because tau is closed on the same measured value under both tables, the two
models differ only in how the same persistence is split between continuous
heading wander and discrete turns.

Nothing is hardcoded.  The global sigma is computed from the published angle at
import time, and every calibrated number is recomputed from the two frozen
inputs on each run.  The delivered table and the existing calibrated table are
never written to.

Setup:
    PYTHONPATH=$PWD/src .venv/bin/python \
        analyses/motility_turn_angle_comparison/calibrate_global_turn_angle.py

Complexity is O(rows); the derivation runs in well under a second.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "analyses/motility_parameter_calibration"))

# The published calibration is imported, never edited.  Editing it would change
# the recorded input checksum of the Figure 5 panels and force a rebuild.
from calibrate import (  # noqa: E402
    DELIVERED,
    EXCLUDED_PHENOTYPES,
    SELF_CHECK_ATOL,
    TAU_CLOSURE_ATOL,
    measured_summary,
    model_tau,
)

PROCESSED = PROJECT / "data/processed/motility_turn_angle_comparison"
GLOBAL_TABLE = PROCESSED / "motility_summary_parameters_global_turn_angle.csv"
CHECKSUM = PROCESSED / "motility_summary_parameters_global_turn_angle.sha256"
AUDIT = PROCESSED / "global_turn_angle_calibration_audit.csv"
RECORD = Path(__file__).resolve().parent / "metadata/derivation.json"

# Taute et al. 2015, Nat Commun 6:8776. Population mean turn angle, n = 8058
# turns, E. coli AW405, three-dimensional tracking.
TAUTE_MEAN_TURN_ANGLE_DEG = 57.0
TAUTE_TURN_COUNT = 8058
TAUTE_DOI = "10.1038/ncomms9776"
TAUTE_PMID = "26522289"

# Mean absolute value of a zero-mean normal, in units of its standard deviation.
MEAN_ABS_OVER_SD = math.sqrt(2.0 / math.pi)

#: The single turn width used by every row of the variant table, in radians.
GLOBAL_TURN_ANGLE_SD_RAD = math.radians(TAUTE_MEAN_TURN_ANGLE_DEG) / MEAN_ABS_OVER_SD


def turn_angle_diagnostics(
    turn_angle_sd_rad: float = GLOBAL_TURN_ANGLE_SD_RAD,
    n_draws: int = 2_000_000,
    seed: int = 20260813,
) -> dict[str, float]:
    """Return the realised turn statistics of the wrapped Gaussian turn.

    The nominal mean absolute turn is ``sigma * sqrt(2 / pi)``.  A heading is
    periodic, so a draw beyond +/-pi folds back onto a smaller turn.  This
    function reports both the nominal and the wrapped mean, so the loss is a
    measured number rather than an assumption.

    Example:
        >>> stats = turn_angle_diagnostics(1.246843, n_draws=200_000)
        >>> round(stats["nominal_mean_abs_turn_deg"], 1)
        57.0
        >>> stats["wrapped_mean_abs_turn_deg"] < stats["nominal_mean_abs_turn_deg"]
        True
    """
    rng = np.random.default_rng(seed)
    draws = rng.normal(0.0, turn_angle_sd_rad, size=n_draws)
    wrapped = np.abs((draws + math.pi) % (2.0 * math.pi) - math.pi)
    return {
        "turn_angle_sd_rad": float(turn_angle_sd_rad),
        "turn_angle_sd_deg": float(math.degrees(turn_angle_sd_rad)),
        "nominal_mean_abs_turn_deg": float(math.degrees(turn_angle_sd_rad * MEAN_ABS_OVER_SD)),
        "wrapped_mean_abs_turn_deg": float(math.degrees(wrapped.mean())),
        "fraction_wrapped": float(np.mean(np.abs(draws) > math.pi)),
        "n_draws": int(n_draws),
        "seed": int(seed),
    }


def calibrate_global(
    turn_angle_sd_rad: float = GLOBAL_TURN_ANGLE_SD_RAD,
) -> pd.DataFrame:
    """Derive the global-turn-angle table from the two frozen inputs.

    The returned frame keeps the delivered columns plus audit columns, so the
    caller can see the substitution and the closure in one place.
    """
    delivered = pd.read_csv(DELIVERED)
    delivered = delivered[~delivered.phenotype.isin(EXCLUDED_PHENOTYPES)].copy()
    measured = measured_summary()
    merged = delivered.merge(measured, on=["phenotype", "medium"], how="left", validate="1:1")
    if merged[["measured_tau_s", "measured_run_speed_um_s"]].isna().any().any():
        raise ValueError("A delivered row has no matching measurement.")

    # Same self-check as the published calibration: the delivered table really
    # was built on these two measured quantities.
    for column, measured_column in (
        ("run_speed_um_s", "measured_run_speed_um_s"),
        ("motile_fraction", "measured_motile_fraction"),
    ):
        deviation = float(np.abs(merged[column] - merged[measured_column]).max())
        if deviation > SELF_CHECK_ATOL:
            raise AssertionError(
                f"Delivered {column} does not match the measurement it was built from "
                f"(max deviation {deviation:.3e} > {SELF_CHECK_ATOL:.0e})."
            )

    merged["delivered_turn_angle_sd_rad"] = merged.turn_angle_sd_rad
    merged["turn_angle_sd_rad"] = float(turn_angle_sd_rad)

    # The closure runs with the global sigma already in place, so the scale
    # factor absorbs both the delivered tau mismatch and the wider turn.
    merged["delivered_model_tau_s"] = [
        model_tau(row.rotational_diffusion_rad2_s, row.reorientation_rate_s, row.turn_angle_sd_rad)
        for row in merged.itertuples()
    ]
    merged["turning_scale_factor"] = merged.delivered_model_tau_s / merged.measured_tau_s
    merged["rotational_diffusion_rad2_s"] = (
        merged.rotational_diffusion_rad2_s * merged.turning_scale_factor
    )
    merged["reorientation_rate_s"] = merged.reorientation_rate_s * merged.turning_scale_factor
    merged["run_speed_um_s"] = merged.measured_run_speed_um_s
    merged["motile_fraction"] = merged.measured_motile_fraction

    merged["calibrated_model_tau_s"] = [
        model_tau(row.rotational_diffusion_rad2_s, row.reorientation_rate_s, row.turn_angle_sd_rad)
        for row in merged.itertuples()
    ]
    residual = float(np.abs(merged.calibrated_model_tau_s - merged.measured_tau_s).max())
    if residual > TAU_CLOSURE_ATOL:
        raise AssertionError(
            f"Calibrated tau does not close on the measured tau (residual {residual:.3e})."
        )
    return merged


def parameter_table(calibration: pd.DataFrame) -> pd.DataFrame:
    """Return only the columns the upstream loader requires, in delivered order."""
    columns = list(pd.read_csv(DELIVERED, nrows=0).columns)
    return calibration[columns].copy()


def _artifact(path: Path) -> dict[str, object]:
    item: dict[str, object] = {
        "relative_path": path.relative_to(PROJECT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
    }
    if path.suffix == ".csv":
        item["rows"] = max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1)
    return item


def write_global_calibration() -> pd.DataFrame:
    """Derive, write and checksum the variant table plus its derivation record."""
    calibration = calibrate_global()
    PROCESSED.mkdir(parents=True, exist_ok=True)
    parameter_table(calibration).to_csv(GLOBAL_TABLE, index=False)
    digest = hashlib.sha256(GLOBAL_TABLE.read_bytes()).hexdigest()
    CHECKSUM.write_text(f"{digest}  {GLOBAL_TABLE.name}\n", encoding="utf-8")

    audit_columns = [
        "phenotype",
        "medium",
        "delivered_turn_angle_sd_rad",
        "turn_angle_sd_rad",
        "delivered_model_tau_s",
        "measured_tau_s",
        "turning_scale_factor",
        "rotational_diffusion_rad2_s",
        "reorientation_rate_s",
        "calibrated_model_tau_s",
        "n_units",
    ]
    calibration[audit_columns].to_csv(AUDIT, index=False)

    diagnostics = turn_angle_diagnostics()
    residual = float(np.abs(calibration.calibrated_model_tau_s - calibration.measured_tau_s).max())
    record = {
        "schema_version": "1.0.0",
        "record_type": "derived_parameter_calibration",
        "record_id": "motility_turn_angle_comparison_global",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "command": [
            ".venv/bin/python3.12",
            "analyses/motility_turn_angle_comparison/calibrate_global_turn_angle.py",
        ],
        "inputs": [
            _artifact(Path(__file__).resolve()),
            _artifact(PROJECT / "analyses/motility_parameter_calibration/calibrate.py"),
            _artifact(DELIVERED),
            _artifact(
                PROJECT / "data/processed/figure_07_revision"
                "/paired_experimental_unit_measurements.csv"
            ),
        ],
        "outputs": [_artifact(GLOBAL_TABLE), _artifact(CHECKSUM), _artifact(AUDIT)],
        "software": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "parameters": {
            "persistence_relation": "tau = 1 / (D_r + lambda * (1 - exp(-sigma^2 / 2)))",
            "global_turn_angle_sd_rad": GLOBAL_TURN_ANGLE_SD_RAD,
            "global_turn_angle_sd_deg": math.degrees(GLOBAL_TURN_ANGLE_SD_RAD),
            "anchor_mean_turn_angle_deg": TAUTE_MEAN_TURN_ANGLE_DEG,
            "anchor_turn_count": TAUTE_TURN_COUNT,
            "anchor_source": (
                "Taute KM, Gude S, Tans SJ, Shimizu TS (2015) Nat Commun 6:8776, "
                f"doi:{TAUTE_DOI}, PMID {TAUTE_PMID}"
            ),
            "anchor_mapping": "sigma = radians(mean turn angle) / sqrt(2 / pi)",
            "delivered_turn_angle_sd_rad_range": [
                float(calibration.delivered_turn_angle_sd_rad.min()),
                float(calibration.delivered_turn_angle_sd_rad.max()),
            ],
            "turn_angle_diagnostics": diagnostics,
            "excluded_phenotypes": list(EXCLUDED_PHENOTYPES),
            "tau_closure_residual_s": residual,
            "turning_scale_factor_range": [
                float(calibration.turning_scale_factor.min()),
                float(calibration.turning_scale_factor.max()),
            ],
        },
        "random_seeds": {"turn_angle_diagnostics": diagnostics["seed"]},
        "findings": [
            (
                "The delivered turn width varies from 0.301 to 0.804 rad across the six "
                "phenotype-by-medium rows with no stated source. This table replaces all six "
                f"with one value, {GLOBAL_TURN_ANGLE_SD_RAD:.4f} rad, derived from the only "
                "published mean turn angle the source review could verify."
            ),
            (
                "The persistence time closes on the same measured tau as the published "
                "calibration, so the two tables describe the same persistence. They differ "
                "only in how that persistence is split between continuous heading wander and "
                "discrete turns."
            ),
        ],
        "limitations": [
            (
                "The anchor was measured in three dimensions for E. coli. The simulator is "
                "two-dimensional and the organism is S. Typhimurium. The mapping matches the "
                "mean turn magnitude, not the shape of the turn-angle distribution."
            ),
            (
                "A zero-mean Gaussian turn cannot reproduce the measured turn-angle shape, "
                "which is broad and skewed toward the forward hemisphere. Only the mean "
                "magnitude is matched."
            ),
            (
                "Calibration still sets the persistence time to the measured mean, so the "
                "two reorientation rates remain fitted quantities with no independent "
                "physical meaning."
            ),
            (
                "This table is a decision aid. It is not used by any manuscript panel unless "
                "a builder is pointed at it explicitly."
            ),
        ],
    }
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    RECORD.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return calibration


def global_turn_angle_table_path(*, force: bool = False) -> Path:
    """Return the variant table, deriving it first if it is missing."""
    if force or not GLOBAL_TABLE.exists():
        write_global_calibration()
    return GLOBAL_TABLE


def main() -> None:
    calibration = write_global_calibration()
    columns = [
        "phenotype",
        "medium",
        "delivered_turn_angle_sd_rad",
        "turn_angle_sd_rad",
        "measured_tau_s",
        "turning_scale_factor",
        "rotational_diffusion_rad2_s",
        "reorientation_rate_s",
        "calibrated_model_tau_s",
    ]
    diagnostics = turn_angle_diagnostics()
    print(
        f"global sigma = {GLOBAL_TURN_ANGLE_SD_RAD:.6f} rad "
        f"({math.degrees(GLOBAL_TURN_ANGLE_SD_RAD):.2f} deg), "
        f"from a {TAUTE_MEAN_TURN_ANGLE_DEG:.0f} deg mean turn "
        f"(Taute et al. 2015, n = {TAUTE_TURN_COUNT})"
    )
    print(
        f"realised mean |turn| after heading wrap: "
        f"{diagnostics['wrapped_mean_abs_turn_deg']:.2f} deg "
        f"({diagnostics['fraction_wrapped']:.3%} of draws wrap)\n"
    )
    with pd.option_context("display.width", 220, "display.precision", 4):
        print(calibration[columns].to_string(index=False))
    residual = float(np.abs(calibration.calibrated_model_tau_s - calibration.measured_tau_s).max())
    print(f"\ntau closure residual: {residual:.3e} s")
    print(f"variant table: {GLOBAL_TABLE.relative_to(PROJECT)}")


if __name__ == "__main__":
    main()
