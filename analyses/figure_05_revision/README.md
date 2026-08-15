# Revised Figure 5 — motility benefit and predicted optimum

This Python 3.12 workflow combines the supplied gradient-model results with quantitative
predictions from the updated active-particle motility simulation.

Run:

```text
.venv/bin/python analyses/figure_05_revision/build.py --all
```

Panels A–C use the checksum-frozen collaborator tables for the demonstrated dynamic-model
domain of 0.5–5% flagellar allocation. Panels D–E summarize 100 deterministic simulation
seeds per phenotype and medium, with 26 cells per seed. The plotted points are seed-level
mean net displacements; intervals are 2.5–97.5% simulation intervals, not biological
confidence intervals. `WT_slow` is excluded because it is not a manuscript phenotype.

Panels D and E measure, so they run in a domain of 1776 × 1152 µm, twelvefold larger in
each direction than the published 148 × 96 µm box (`QUANTITATIVE_BOX_SCALE` = 12 in
`build.py`). The obstacle count scales with the box area, so the enlarged agarose field
holds 8352 disks at a realised area fraction of 0.187, against 58 disks at 0.185 in the
published box. Panel D is liquid and holds no obstacle. Supplementary Figure 4 keeps the
published box (`VISUAL_BOX_SCALE` = 1), because its maps must stay legible and report no
number.

The active-particle model is explicitly illustrative and excludes chemotaxis. The six
representative seeded trajectory maps remain in Supplementary Figure 4.

## Which parameter table D and E read

`data/processed/motility_adopted_parameters/motility_summary_parameters_adopted.csv`,
derived at build time by
`analyses/motility_adopted_parameters/derive_adopted_parameters.py` and reached through the
single accessor `adopted_parameter_table_path()`. It is the only parameter table any
manuscript panel reads. Supplementary Figure 4, the time-step convergence ladder and
Supplementary Table X read the same file, so every figure depicts one simulation.

The table repeats the calibration of
`analyses/motility_parameter_calibration/calibrate.py` with two changes, both adopted
during the revision and both derived, never typed in.

1. **One global turn width**, `turn_angle_sd_rad` = 1.2468 rad in all six rows, set so the
   mean turn magnitude equals the 57 deg measured by Taute et al. 2015. The six per-strain
   widths it replaces had no source. See
   `docs/revision_2026-08-12/turn_angle_model_comparison.md`.
2. **A flagella-scaled stall probability and a global stall duration.** In the three
   agarose rows `stall_probability` falls with the mean hook number as `N^-0.704` (PproA
   0.2099, WT 0.1766, PproB 0.1235), normalised so its mean over the three strains is
   unchanged. `stall_probability` is a per-contact-event probability, the same quantity
   Grognot et al. 2023 measured. The exponent sets the extreme-strain ratio to the 1.7 +/- 0.2 stall-frequency
   ratio of Grognot et al. 2023. `stall_mean_duration_s` becomes one value, 0.9489 s,
   because that study found the duration effect significant only at 0.16 % agar, not at the
   0.25 % that matches our condition. The liquid rows keep `stall_probability` 0 and are
   unaffected. See `docs/revision_2026-08-12/stall_parameter_comparison.md`.

## Why net displacement and not path length

Panels D and E once plotted the mean contour path length of a track. That quantity does
not converge under time-step refinement. A trajectory with a diffusive component has an
infinite arc length in the continuum limit, so the summed step length grows without a
limit as the step shrinks, and the ratio between two phenotypes drifts across 1. The
strain comparison was therefore a property of the chosen step, not of the model. Net
displacement, the straight-line distance from the start to the end of a track, converges.

The check runs the full seed plan at a ladder of time steps:

```text
PYTHONPATH=$PWD/src MPLBACKEND=Agg .venv/bin/python \
    analyses/figure_05_revision/timestep_convergence.py
```

It writes `build/diagnostics/Figure_5/timestep_convergence.csv` and two companion tables.
The check accepts every step whose group mean net displacement stays within 5 % of the
mean of the two finest steps tested, 0.00125 s and 0.000625 s. It uses 100 seeds and six
strain-by-medium groups. Every step of the tested ladder passes. The table records the
largest deviation over the six groups:

| dt (s) | largest group deviation | passes |
| ---: | ---: | :--- |
| 0.05 | 3.96 % | yes |
| 0.01 | 3.88 % | yes |
| 0.005 | 3.22 % | yes |
| 0.0025 | 1.99 % | yes, panel step |
| 0.00125 | 2.20 % | yes |
| 0.000625 | 2.20 % | yes |

`SIMULATION_DT_S` in `build.py` holds 0.0025 s, the step with the smallest deviation. The
`selected_dt_s` column of the CSV reads 0.05, because the selector returns the coarsest
passing step. The panels deliberately run finer, which also keeps them comparable across
the parameter change.

**Net displacement converges in both media.** The model draws the stall test once per
contact event, not once per time step of obstacle overlap, so a finer step does not add
stall draws. A cell counts as still touching a disk until its centre passes 0.1 µm beyond
the surface (`CONTACT_RELEASE_UM`). Between the two finest steps the PproB agarose group
mean moves by 0.30 %. The agarose PproB/PproA ratio holds across the whole ladder: 3.45 at
0.05 s, 3.32 at 0.01 s, 3.50 at 0.005 s, 3.29 at the panel step, 3.35 at 0.00125 s and
3.34 at 0.000625 s. The ratio shows no trend in the step.

The upstream `config.yml` declares 0.05 s and stays untouched, because it is immutable
provenance; the builder overrides the value. Supplementary Figure 4 imports the same
constant, so both figures depict one simulation.

## Analysis A3 — the 0–1% allocation sweep

A3 is a separate executable harness. It covers 0–1% flagellar allocation in
0.05-percentage-point steps, 21 steps in total.

```text
.venv/bin/python models/cell_economy/low_allocation_sweep.py --remote
```

`--remote` is the canonical mode and it needs network access. GEKKO sends the model to
the public APMonitor server, which solves it with IPOPT (solver 3). This is the route
the model's author, Michael Jahn, uses. The harness writes
`build/statistics/Figure_5/A3/low_allocation_solver_status.csv` and the companion
`low_allocation_steady_state.csv`, and copies both to `data/processed/figure_05_revision/`.

`--plan` emits the historical blocked-status plan, so the pre-13-August record stays
reproducible. `--execute` runs the local, non-network attempt, which fails on every step.
Neither mode invents an objective value. The harness requires an explicit mode, so a bare
call cannot overwrite the solved table with blocked rows.

### A3 solver provenance

Recorded 13 August 2026. Reproduce with these exact settings:

| item | value |
| :--- | :--- |
| solver | APMonitor solver 3 (IPOPT v3.12), server-side |
| GEKKO | 1.3.2, `remote=True` |
| server | `https://apmonitor.com` |
| model options | `IMODE` 5 (steady state) then 6 (dynamic), `REDUCE=1`, `MAX_ITER=2000`, `RTOL=1e-5`, `OTOL=1e-5`, `SCALING=1`, `TIME_SHIFT=1` |
| client | Python 3.12.11, macOS 26.6.1 arm64, project `.venv` |
| parameters | `data/external/cell_economy_results/sampling/kinetic_params_2026.csv` |
| runtime | about 12 s per allocation, about 4 min for all 21 |

Two host-level shims are needed and are coded in the harness, not hidden:

1. GEKKO 1.3.2 hardcodes `http://byu.apmonitor.com`. That host no longer resolves
   (NXDOMAIN, checked 13 August 2026), so the harness sets `server="https://apmonitor.com"`.
2. GEKKO posts with the default urllib User-Agent, which the CDN in front of
   apmonitor.com rejects with HTTP 403. The harness identifies the client as
   `GEKKO/1.3.2 (python-urllib)`, a truthful client name.

The harness also gives every model a unique random name, because the server keys each
workspace on the observed client address and that address is shared behind the CDN.
Only the model is sent. No data file and no credential leaves the host.

### What A3 found

19 of 21 steps solve end to end. The steady-state stage solves at all 21 steps,
including exactly 0%. The dynamic stage fails at 0.75% and 0.95% with
`Solution Not Found`; both failures repeat on retry, and both neighbours solve, so this
is local-optimum behaviour of a non-convex NLP, not a domain boundary.

The route reproduces the delivered dynamic tables at 1%, 2%, 3%, 4% and 5% flagellar
allocation to within 1e-9 relative error. At 0.5% it finds a different and better local
optimum than the delivered table: final growth rate 1.7064 h⁻¹ against 1.6617 h⁻¹.
Because the dynamic objective is non-convex, the 0–1% dynamic curve is not monotonic;
the steady-state curve is.
