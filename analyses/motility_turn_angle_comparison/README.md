# Turn-angle model comparison

Builds a second motility parameter table in which the reorientation angle is one
global, literature-anchored value, then compares it against the previous table.

**Adopted 13 August 2026.** The global-angle table is now the canonical
parameter table. `analyses/figure_05_revision/build.py`,
`analyses/supplementary_04/build_s4.py`,
`analyses/figure_05_revision/timestep_convergence.py` and
`analyses/motility_parameter_calibration/make_supplementary_table.py` all read
it. The comparison below stays on the record as the evidence for the choice.

The written recommendation is in
`docs/revision_2026-08-12/turn_angle_model_comparison.md`.

## Why

The delivered table gives each phenotype-by-medium row its own
`turn_angle_sd_rad`:

| | liquid | agarose |
| --- | --- | --- |
| PproA | 0.633 | 0.804 |
| WT | 0.646 | 0.746 |
| PproB | 0.301 | 0.328 |

None of the six values has a source. The first version of the simulator was
written by a language model, and this parameter was never measured and never
taken from a publication. PproB carries less than half the width of the other
two strains. No measurement of ours distinguishes PproB that way, so the split
is invented, and it contaminates any attempt to relate directional persistence
to flagella number. `docs/revision_2026-08-12/motility_parameter_sources.md`,
section 3, records the gap.

## The global value

The simulator draws `theta += rng.normal(0, sigma)`. For a zero-mean normal the
mean absolute turn is `sigma * sqrt(2 / pi)`.

Taute et al. 2015 report a population mean turn angle of 57 deg from 8058 turns
of *E. coli* AW405 (Nat Commun 6:8776, doi:10.1038/ncomms9776, PMID 26522289).
This is the only published mean turn angle the source review verified.

    sigma = radians(57) / sqrt(2 / pi) = 1.2468 rad = 71.4 deg

Two limits of the anchor:

- Taute et al. measured in three dimensions; the simulator is two-dimensional.
  The mapping matches the mean turn magnitude, which is the comparison the
  source review already makes.
- A heading is periodic, so 1.2 % of draws fold back past +/-pi. The realised
  mean turn is 56.5 deg rather than 57.0 deg. `turn_angle_diagnostics()`
  measures this rather than assuming it.

The value is computed from the published angle at import time. It is not
written into any table by hand.

## Method

`calibrate_global_turn_angle.py` repeats the published calibration with one
substitution. `turn_angle_sd_rad` becomes the global value in every row before
the persistence closure runs. Everything else is unchanged:

    tau = 1 / (D_r + lambda * (1 - exp(-sigma^2 / 2)))

`rotational_diffusion_rad2_s` and `reorientation_rate_s` keep their delivered
ratio, and both are scaled by the one factor that makes the model tau equal the
measured tau. Every other column passes through as delivered.

Both tables therefore close on the same measured persistence time. The two
models differ only in how that persistence is split between continuous heading
wander and discrete turns.

`analyses/motility_parameter_calibration/calibrate.py` is imported, never
edited. Editing it would change the recorded input checksum of the Figure 5
panels and force a rebuild.

## Comparison

`compare_turn_angle_models.py` runs both tables over the same seed plan the
manuscript uses: seeds 1000-1099, 26 cells per seed, dt = 0.0025 s, 20 s per
track, six phenotype-by-medium groups. That is 1200 simulations.

The two models share the seed set, so they share the starting positions, the
motile mask, the initial headings and the obstacle field. Those draws all
precede any parameter that differs. The comparison is therefore paired on the
initial condition. It is not paired on the later random draws, because the
parameters differ from the first step onward.

Intervals come from a bootstrap over the 100 seeds, 10000 draws, seed 20260813.
One resample is applied to every group of both models at once, so the pairing
and the strain ratios survive the resampling.

## Inputs

| Path | Role |
| --- | --- |
| `models/motility_simulation/upstream/data/motility_summary_parameters.csv` | Frozen delivered table. Never modified. |
| `data/processed/figure_07_revision/paired_experimental_unit_measurements.csv` | Measured per-unit values. |
| `data/processed/motility_parameter_calibration/motility_summary_parameters_calibrated.csv` | The current model. Never modified. |
| `models/motility_simulation/upstream/data/config.yml` | Frozen simulator config. Never modified. |

## Outputs

| Path | Role |
| --- | --- |
| `data/processed/motility_turn_angle_comparison/motility_summary_parameters_global_turn_angle.csv` | The variant table, same schema as delivered. |
| `data/processed/motility_turn_angle_comparison/global_turn_angle_calibration_audit.csv` | Per-row substitution, scale factor and tau closure. |
| `build/diagnostics/turn_angle_comparison/parameter_comparison.csv` | D_theta, lambda, tau, tumble share and run length under both models. |
| `build/diagnostics/turn_angle_comparison/net_displacement_comparison.csv` | Paired net displacement with bootstrap intervals. |
| `build/diagnostics/turn_angle_comparison/ratio_comparison.csv` | PproB/PproA and WT/PproA under both models. |
| `build/diagnostics/turn_angle_comparison/seed_summary_*.csv` | One mean net displacement per seed, per model. |
| `build/diagnostics/turn_angle_comparison/trajectories_*.png` | All 26 tracks of one seed, both models side by side. |
| `build/diagnostics/turn_angle_comparison/single_cell_tracks_*.png` | One cell, 3 s, both models, with each discrete turn marked. |
| `build/diagnostics/turn_angle_comparison/net_displacement_paired.png` | Each seed as a line from the current model to the variant. |
| `analyses/motility_turn_angle_comparison/metadata/*.json` | Provenance records. |

## Run

    PYTHONPATH=$PWD/src .venv/bin/python \
        analyses/motility_turn_angle_comparison/calibrate_global_turn_angle.py

    PYTHONPATH=$PWD/src MPLBACKEND=Agg .venv/bin/python \
        analyses/motility_turn_angle_comparison/compare_turn_angle_models.py

The comparison takes about 12 min on one core. It caches each model's run and
keys the cache to the checksum of that model's parameter table, so a rerun
without a parameter change costs seconds. Pass `--force` to rerun anyway.

## Adoption, 13 August 2026

Marc approved the variant. The builders now call
`global_turn_angle_table_path()` instead of `calibrated_table_path()` in
`analyses/figure_05_revision/build.py`,
`analyses/figure_05_revision/timestep_convergence.py`,
`analyses/supplementary_04/build_s4.py` and
`analyses/motility_parameter_calibration/make_supplementary_table.py`. The
simulation caches are keyed by the parameter checksum, so they invalidated on
their own. `docs/revision_2026-08-12/change_log.md` records the before and after
group means.
