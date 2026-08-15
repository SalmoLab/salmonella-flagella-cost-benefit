# Motility parameter calibration

Derives the active-particle motility parameters from our own measurements.

**This directory no longer produces the table the figures read.** Every
manuscript panel reads
`data/processed/motility_adopted_parameters/motility_summary_parameters_adopted.csv`,
built by `analyses/motility_adopted_parameters/derive_adopted_parameters.py` and
reached through `adopted_parameter_table_path()`. That module composes two
adopted decisions on top of this calibration: `turn_angle_sd_rad` becomes one
global, literature-anchored value before the persistence closure runs, and the
three agarose rows then take a flagella-scaled `stall_probability` and one
global `stall_mean_duration_s`. See
`docs/revision_2026-08-12/turn_angle_model_comparison.md` and
`docs/revision_2026-08-12/stall_parameter_comparison.md`.

The table described below therefore stays the reference point of the comparison.
It is not the table the panels use.

## Why

The collaborator delivered a frozen parameter table with the simulator. Two of
its columns were already calibrated to our measured per-unit values:
`run_speed_um_s` and `motile_fraction`. The turning parameters were not. Using
the model's own persistence relation

    tau = 1 / (D_r + lambda * (1 - exp(-sigma^2 / 2)))

the delivered rows give a persistence time between 0.80x and 6.16x the measured
one, worst for PproB in agarose. That row is why the simulated agarose PproB
cells spread much further than the data show.

The simulation illustrates the experimental findings. It does not predict them.
Calibration is therefore legitimate, and the panels say so.

## Inputs

| Path | Role |
| --- | --- |
| `models/motility_simulation/upstream/data/motility_summary_parameters.csv` | Frozen delivered table. Never modified. |
| `data/processed/figure_07_revision/paired_experimental_unit_measurements.csv` | Measured per-unit values. |

The measured statistic is the mean over paired experimental units, per medium,
of `speed_med_<phenotype>`, `tau_<phenotype>` and `swim_frac_<phenotype>`.

## Method

Per phenotype-by-medium row, excluding `WT_slow`:

- `motile_fraction` and `run_speed_um_s` come from the measurements. They
  already equal the delivered values, so the code asserts the agreement as a
  self-check on the delivered table. The tolerance is `1e-5`, because the
  delivered CSV carries six significant figures and does not round-trip exactly.
- `turn_angle_sd_rad` is kept as delivered. The adopted table replaces it with
  one global value; see the note at the top of this file.
- `rotational_diffusion_rad2_s` and `reorientation_rate_s` keep their delivered
  ratio. Both are scaled by the one factor that makes the model tau equal the
  measured tau. tau depends on the two rates only through their sum, so scaling
  both by `s` divides tau by `s`, and the closing factor is
  `s = tau_delivered / tau_measured`.
- `passive_diffusion_um2_s`, `stall_probability` and `stall_mean_duration_s` are
  kept as delivered.
- `reorientation_duration_s` is dropped. The corrected dynamics reorient
  instantaneously, so the model has no such parameter and the adopted table
  carries no such column.

After calibration the code asserts that every row's model tau equals its
measured tau to `1e-12`. The observed residual is about `3e-17` s.

Nothing is hardcoded. Every calibrated number is recomputed from the two
canonical inputs on each run.

## Outputs

| Path | Role |
| --- | --- |
| `data/processed/motility_parameter_calibration/motility_summary_parameters_calibrated.csv` | Calibrated table, same schema as delivered. |
| `data/processed/motility_parameter_calibration/motility_summary_parameters_calibrated.sha256` | Checksum of the table. |
| `data/processed/motility_parameter_calibration/calibration_audit.csv` | Per-row delivered tau, measured tau, scale factor and closure. |
| `analyses/motility_parameter_calibration/metadata/derivation.json` | Provenance record, including the finding that only the turning parameters were uncalibrated. |

## Run

    PYTHONPATH=$PWD/src MPLBACKEND=Agg .venv/bin/python \
        analyses/motility_parameter_calibration/calibrate.py

The Figure 5 and Supplementary Figure 4 builders call
`adopted_parameter_table_path()`, which derives the adopted table if it is
missing. Both builders key their simulation cache to the checksum of the
parameter table, so a recalibration invalidates a stale run instead of being
reused.

`make_supplementary_table.py` reads the same adopted table, so Supplementary
Table X cannot drift from the numbers the figures use.

The delivered-parameter run stays reproducible as a diagnostic under
`build/diagnostics/Figure_5/`. It is not a manuscript panel.
