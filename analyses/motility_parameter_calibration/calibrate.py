#!/usr/bin/env python3
"""Derive active-particle motility parameters calibrated to our own measurements.

The collaborator delivered a frozen parameter table with the active-particle
simulator.  Two of its columns, ``run_speed_um_s`` and ``motile_fraction``, were
already set from our measured per-unit values.  The turning parameters were not.
Using the model's own persistence relation

    tau = 1 / (D_r + lambda * (1 - exp(-sigma^2 / 2)))

the delivered rows give a persistence time between 0.80x and 6.16x the measured
one.  This module closes that gap so the simulation illustrates the measured
behaviour instead of contradicting it.

Method, per phenotype-by-medium row:

* ``motile_fraction`` and ``run_speed_um_s`` are taken from the measurements.
  They already equal the delivered values, so the agreement is asserted as a
  self-check on the delivered table rather than used to change it.
* ``turn_angle_sd_rad`` is kept exactly as delivered.
* ``rotational_diffusion_rad2_s`` and ``reorientation_rate_s`` keep their
  delivered ratio.  Both are scaled by the single factor that makes the model
  tau equal the measured tau.  Because tau depends on the two rates only through
  their sum, scaling both by ``s`` divides tau by ``s``, so the closing factor is
  ``s = tau_delivered / tau_measured``.
* ``reorientation_duration_s``, ``passive_diffusion_um2_s``,
  ``stall_probability`` and ``stall_mean_duration_s`` are left as delivered.

``WT_slow`` is excluded, as the manuscript already excludes it.

Nothing here is hardcoded: every calibrated number is recomputed from the two
canonical inputs on each run.

Setup:
    PYTHONPATH=$PWD/src MPLBACKEND=Agg .venv/bin/python \
        analyses/motility_parameter_calibration/calibrate.py

Complexity is O(rows); the whole derivation runs in well under a second.
"""

from __future__ import annotations

import hashlib
import json
import platform
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parents[2]

DELIVERED = PROJECT / "models/motility_simulation/upstream/data/motility_summary_parameters.csv"
MEASURED = (
    PROJECT / "data/processed/figure_07_revision/paired_experimental_unit_measurements.csv"
)
PROCESSED = PROJECT / "data/processed/motility_parameter_calibration"
CALIBRATED = PROCESSED / "motility_summary_parameters_calibrated.csv"
CHECKSUMS = PROCESSED / "motility_summary_parameters_calibrated.sha256"
RECORD = Path(__file__).resolve().parent / "metadata/derivation.json"

# The manuscript panels never show WT_slow, so it never reaches calibration.
EXCLUDED_PHENOTYPES = ("WT_slow",)

# The delivered CSV carries six significant figures, so a measured value that
# was used to build it round-trips to about 1e-6, not to exact equality.
SELF_CHECK_ATOL = 1e-5
# The tau closure is pure arithmetic on floats and closes to machine precision.
TAU_CLOSURE_ATOL = 1e-12


def model_tau(
    rotational_diffusion_rad2_s: float,
    reorientation_rate_s: float,
    turn_angle_sd_rad: float,
) -> float:
    """Return the model persistence time in seconds.

    This is the simulator's own relation between the two reorientation rates and
    the turn-angle width.

    Example:
        >>> round(model_tau(1.933177, 1.953612, 0.632777), 4)
        0.4371
    """
    turn_efficiency = 1.0 - np.exp(-(turn_angle_sd_rad**2) / 2.0)
    return float(1.0 / (rotational_diffusion_rad2_s + reorientation_rate_s * turn_efficiency))


def measured_summary() -> pd.DataFrame:
    """Return the mean over paired experimental units, per phenotype and medium.

    The paired-unit table stores one column per phenotype.  A unit that did not
    image a given phenotype leaves that column empty, so the mean skips missing
    entries.
    """
    units = pd.read_csv(MEASURED)
    rows: list[dict[str, object]] = []
    for medium, part in units.groupby("medium"):
        for phenotype in ("PproA", "WT", "PproB"):
            rows.append(
                {
                    "phenotype": phenotype,
                    "medium": str(medium),
                    "measured_run_speed_um_s": float(part[f"speed_med_{phenotype}"].mean()),
                    "measured_tau_s": float(part[f"tau_{phenotype}"].mean()),
                    "measured_motile_fraction": float(part[f"swim_frac_{phenotype}"].mean()),
                    "n_units": int(part[f"tau_{phenotype}"].notna().sum()),
                }
            )
    return pd.DataFrame(rows)


def calibrate() -> pd.DataFrame:
    """Derive the calibrated parameter table from the two canonical inputs."""
    delivered = pd.read_csv(DELIVERED)
    delivered = delivered[~delivered.phenotype.isin(EXCLUDED_PHENOTYPES)].copy()
    measured = measured_summary()
    merged = delivered.merge(measured, on=["phenotype", "medium"], how="left", validate="1:1")
    if merged[["measured_tau_s", "measured_run_speed_um_s"]].isna().any().any():
        raise ValueError("A delivered row has no matching measurement.")

    merged["delivered_model_tau_s"] = [
        model_tau(row.rotational_diffusion_rad2_s, row.reorientation_rate_s, row.turn_angle_sd_rad)
        for row in merged.itertuples()
    ]

    # Self-check, not a change: the delivered table really was built on these two
    # measured quantities, so they must already agree to CSV round-trip accuracy.
    for column, measured_column in (
        ("run_speed_um_s", "measured_run_speed_um_s"),
        ("motile_fraction", "measured_motile_fraction"),
    ):
        deviation = float(np.abs(merged[column] - merged[measured_column]).max())
        if deviation > SELF_CHECK_ATOL:
            raise AssertionError(
                f"Delivered {column} does not match the measurement it was built from "
                f"(max deviation {deviation:.3e} > {SELF_CHECK_ATOL:.0e}). The delivered "
                "table may no longer correspond to these measurements."
            )

    # tau depends on the two rates only through their sum, so one factor closes it.
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


def write_calibration() -> pd.DataFrame:
    """Derive, write and checksum the calibrated table plus its derivation record."""
    calibration = calibrate()
    PROCESSED.mkdir(parents=True, exist_ok=True)
    table = parameter_table(calibration)
    table.to_csv(CALIBRATED, index=False)
    digest = hashlib.sha256(CALIBRATED.read_bytes()).hexdigest()
    CHECKSUMS.write_text(f"{digest}  {CALIBRATED.name}\n", encoding="utf-8")

    audit_columns = [
        "phenotype",
        "medium",
        "delivered_model_tau_s",
        "measured_tau_s",
        "turning_scale_factor",
        "rotational_diffusion_rad2_s",
        "reorientation_rate_s",
        "calibrated_model_tau_s",
        "n_units",
    ]
    audit = calibration[audit_columns]
    audit_path = PROCESSED / "calibration_audit.csv"
    audit.to_csv(audit_path, index=False)

    residual = float(np.abs(calibration.calibrated_model_tau_s - calibration.measured_tau_s).max())
    record = {
        "schema_version": "1.0.0",
        "record_type": "derived_parameter_calibration",
        "record_id": "motility_parameter_calibration",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "command": [
            ".venv/bin/python3.12",
            "analyses/motility_parameter_calibration/calibrate.py",
        ],
        "inputs": [_artifact(Path(__file__).resolve()), _artifact(DELIVERED), _artifact(MEASURED)],
        "outputs": [_artifact(CALIBRATED), _artifact(CHECKSUMS), _artifact(audit_path)],
        "software": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "parameters": {
            "persistence_relation": "tau = 1 / (D_r + lambda * (1 - exp(-sigma^2 / 2)))",
            "measured_statistic": "mean over paired experimental units, per medium",
            "measured_columns": [
                "speed_med_<phenotype>",
                "tau_<phenotype>",
                "swim_frac_<phenotype>",
            ],
            "calibrated_columns": ["rotational_diffusion_rad2_s", "reorientation_rate_s"],
            "columns_taken_from_measurement": ["run_speed_um_s", "motile_fraction"],
            "columns_kept_as_delivered": [
                "turn_angle_sd_rad",
                "reorientation_duration_s",
                "passive_diffusion_um2_s",
                "stall_probability",
                "stall_mean_duration_s",
            ],
            "excluded_phenotypes": list(EXCLUDED_PHENOTYPES),
            "self_check_atol": SELF_CHECK_ATOL,
            "tau_closure_atol": TAU_CLOSURE_ATOL,
            "tau_closure_residual_s": residual,
            "turning_scale_factor_range": [
                float(calibration.turning_scale_factor.min()),
                float(calibration.turning_scale_factor.max()),
            ],
        },
        "random_seeds": {},
        "findings": [
            (
                "The delivered table's run_speed_um_s and motile_fraction were already "
                "calibrated to these same paired-unit measurements; they agree to CSV "
                "round-trip accuracy and are unchanged by this step."
            ),
            (
                "The turning parameters were not calibrated. The delivered rows give a "
                "model persistence time between "
                f"{calibration.turning_scale_factor.min():.2f}x and "
                f"{calibration.turning_scale_factor.max():.2f}x the measured one, worst for "
                "PproB in agarose. That asymmetry is why this calibration exists."
            ),
        ],
        "limitations": [
            (
                "The turning parameters were calibrated in this repository. They were not "
                "supplied by the collaborator."
            ),
            (
                "Calibration sets the persistence time to the measured mean. It does not fit "
                "the two reorientation rates separately, because the measurement constrains "
                "only their combination through tau."
            ),
            (
                "Run speed, motile fraction and persistence time are now model inputs, so the "
                "simulation cannot be read as predicting them."
            ),
        ],
    }
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    RECORD.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return calibration


def calibrated_table_path(*, force: bool = False) -> Path:
    """Return the calibrated table, deriving it first if it is missing or stale."""
    if force or not CALIBRATED.exists():
        write_calibration()
    return CALIBRATED


def main() -> None:
    calibration = write_calibration()
    columns = [
        "phenotype",
        "medium",
        "delivered_model_tau_s",
        "measured_tau_s",
        "rotational_diffusion_rad2_s",
        "reorientation_rate_s",
    ]
    with pd.option_context("display.width", 200, "display.precision", 4):
        print(calibration[columns].to_string(index=False))
    residual = float(np.abs(calibration.calibrated_model_tau_s - calibration.measured_tau_s).max())
    print(f"\ntau closure residual: {residual:.3e} s")
    print(f"calibrated table: {CALIBRATED.relative_to(PROJECT)}")


if __name__ == "__main__":
    main()
