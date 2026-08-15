# Which turn-angle model goes in the paper

Date: 2026-08-13.

**Recommendation: use the global-angle model.** One turn width for all six rows,
`sigma = 1.247 rad`, anchored to a published mean turn angle of 57 deg.

The reason is provenance. The current per-strain values have no source, and one
of them is an invented strain difference. The global value has a citation and a
stated mapping. The reported strain differences do not depend on the choice, so
adopting the anchored value costs nothing scientifically.

**Adopted 13 August 2026.** Marc approved the recommendation. Section 7 lists
what moved; `change_log.md` records the before and after group means. The text
below is the evidence that led to the choice and was not rewritten after the
fact. Method, code and outputs are in
`analyses/motility_turn_angle_comparison/`.

**Where the adopted value now lives.** The global turn angle is one row of the
single canonical parameter table,
`data/processed/motility_adopted_parameters/motility_summary_parameters_adopted.csv`,
derived at build time by
`analyses/motility_adopted_parameters/derive_adopted_parameters.py`. Figure 5D,
Figure 5E, Supplementary Figure 4, the time-step convergence ladder and
Supplementary Table X reach that table only through
`adopted_parameter_table_path()`. The turn-angle-only table this document
produced is a diagnostic; no manuscript path reads it.

**The figures also run the corrected dynamics.** Every number measured in this
document comes from the upstream dynamics. The panels now run
`models/motility_simulation/corrected/`: reorientation is instantaneous, the
stall test fires once per contact event, and the obstacle count scales with the
box area. The comparison below still decides the turn width, because it compares
two parameter tables under one fixed set of dynamics, and the correction changes
the dynamics for both alike. Do not quote its absolute values as current ones.

---

## 1. The problem with the current values

The delivered table gives each phenotype-by-medium row its own
`turn_angle_sd_rad`:

| | liquid | agarose |
| --- | --- | --- |
| PproA | 0.633 | 0.804 |
| WT | 0.646 | 0.746 |
| PproB | 0.301 | 0.328 |

None of the six values was measured. None came from a publication. The first
version of the simulator was written by a language model.
`motility_parameter_sources.md`, section 3, records the gap, and Supplementary
Table X already labels the parameter "Nominal".

PproB carries less than half the turn width of the other two strains. Nothing in
our measurements distinguishes PproB that way. The split is invented.

It is not harmless. The persistence relation is

    tau = 1 / (D_theta + lambda * (1 - exp(-sigma^2 / 2)))

so a small `sigma` makes each turn nearly useless, and the calibration must
raise the rates to reach the measured `tau`. Under the current table, PproB
delivers only 5.1 % (liquid) and 6.5 % (agarose) of its reorientation as
discrete turns. PproA and WT deliver 15 % to 30 %. The current model therefore
makes PproB a qualitatively different swimmer: a cell that almost never tumbles
and instead wanders continuously. That difference is an artefact of an invented
number, and it sits inside a figure about flagella number and persistence.

## 2. The global value and where it comes from

The simulator draws `theta += rng.normal(0, sigma)`. For a zero-mean normal the
mean absolute turn is `sigma * sqrt(2 / pi)`.

Taute et al. 2015 report a population mean turn angle of 57 deg from 8058 turns
of *E. coli* AW405 (Nat Commun 6:8776, doi:10.1038/ncomms9776, PMID 26522289).
This is the only published mean turn angle the source review verified.

    sigma = radians(57) / sqrt(2 / pi) = 1.2468 rad = 71.4 deg

Two limits, stated so a reviewer meets them first:

- Taute et al. measured in three dimensions. The simulator is two-dimensional.
  The mapping matches the mean turn magnitude. That is the comparison
  `motility_parameter_sources.md` already makes.
- A heading is periodic. 1.2 % of draws fold back past +/-pi, so the realised
  mean turn is 56.5 deg, not 57.0 deg. The code measures this rather than
  assuming it.

A Gaussian still cannot reproduce the measured turn-angle *shape*, which is
broad and skewed forward. Only the mean magnitude is matched. The methods must
say so.

## 3. Calibration, and the correctness check

The variant repeats the published calibration with one substitution.
`turn_angle_sd_rad` becomes the global value before the closure runs.
`D_theta` and `lambda` keep their delivered ratio and are both scaled by the one
factor that makes the model `tau` equal the measured `tau`. Every other column
passes through as delivered.

Because `sigma` is larger, each turn does more work, so the calibration lands on
lower rates. Both tables close on the same measured `tau`.

| Group | sigma (rad) cur → glo | D_theta (rad^2/s) cur → glo | lambda (1/s) cur → glo | tau model cur / glo (s) | tau measured (s) |
| --- | --- | --- | --- | --- | --- |
| PproA liquid | 0.633 → 1.247 | 8.03 → 6.15 | 8.12 → 6.21 | 0.1052 / 0.1052 | 0.1052 |
| WT liquid | 0.646 → 1.247 | 6.11 → 4.30 | 9.40 → 6.62 | 0.1270 / 0.1270 | 0.1270 |
| PproB liquid | 0.301 → 1.247 | 6.62 → 4.23 | 7.97 → 5.09 | 0.1434 / 0.1434 | 0.1434 |
| PproA agarose | 0.804 → 1.247 | 11.00 → 8.56 | 16.90 → 13.15 | 0.0638 / 0.0638 | 0.0638 |
| WT agarose | 0.746 → 1.247 | 7.62 → 5.86 | 10.15 → 7.81 | 0.0992 / 0.0992 | 0.0992 |
| PproB agarose | 0.328 → 1.247 | 8.27 → 5.16 | 10.94 → 6.82 | 0.1131 / 0.1131 | 0.1131 |

**The check passes.** Under both models every row's model `tau` equals its
measured `tau`. The largest residual over all twelve rows is `9.7e-17` s. The
two models describe the same persistence. They differ only in how that
persistence is delivered.

## 4. What the trajectories do

| Group | mean abs turn (deg) | tumble share | reorient duty cycle | mean run length (µm) |
| --- | --- | --- | --- | --- |
| PproA liquid | 28.9 → 57.0 | 0.155 → 0.353 | 0.289 → 0.237 | 2.45 → 3.20 |
| WT liquid | 29.5 → 57.0 | 0.225 → 0.454 | 0.320 → 0.249 | 2.94 → 4.17 |
| PproB liquid | 13.8 → 57.0 | 0.051 → 0.394 | 0.285 → 0.203 | 4.01 → 6.28 |
| PproA agarose | 36.7 → 57.0 | 0.298 → 0.454 | 0.458 → 0.397 | 0.91 → 1.17 |
| WT agarose | 34.1 → 57.0 | 0.245 → 0.419 | 0.337 → 0.281 | 2.28 → 2.97 |
| PproB agarose | 15.0 → 57.0 | 0.065 → 0.417 | 0.354 → 0.254 | 2.62 → 4.20 |

`tumble share` is `lambda * k / (D_theta + lambda * k)` with
`k = 1 - exp(-sigma^2 / 2)`. It is the fraction of the persistence decay rate
delivered by discrete turns rather than by continuous heading wander.

Three things follow.

1. Turns become discrete. The tumble share rises from a range of 0.05 to 0.30
   into a narrow band of 0.35 to 0.45. Under the global value all six rows swim
   the same *way*, and differ only in speed, motile fraction and persistence
   time, which are the quantities we measured.
2. Runs get longer. Mean run length rises by 28 % to 60 %. Both models still
   fall far short of a real run. Taute et al. measured a mean run of 0.64 s; at
   the 22 µm/s that Drescher et al. measured for swimming *E. coli*, that is
   about 14 µm. Our longest modelled run is 6.3 µm. That gap is set by our
   measured short-window `tau` of 0.064 to 0.143 s, not by the turn angle, and
   no choice of `sigma` closes it.
3. Cells swim more of the time. Fewer turns means less time in the non-swimming
   reorientation state. The duty cycle falls by 5 to 10 percentage points.

`build/diagnostics/turn_angle_comparison/single_cell_tracks_liquid.png` shows
this directly. Each discrete turn is marked. Under the current model the PproB
track wanders smoothly with 17 barely-visible turns in 3 s. Under the global
value the same cell runs in straight segments and turns sharply 8 times. The
second looks more like a swimming cell.

## 5. Net displacement

Both models ran the manuscript seed plan: seeds 1000-1099, 26 cells per seed,
dt = 0.0025 s, 20 s tracks, 1200 simulations. The two models share the seeds, so
they share the starting positions, the motile mask, the initial headings and the
obstacle field. The comparison is paired on the initial condition. Intervals are
a bootstrap over the 100 seeds, 10000 draws, seed 20260813.

The current-model run reproduces the published Figure 5D and 5E run exactly. All
600 seed values are identical to
`data/processed/figure_05_revision/active_particle_100_seed_summary.csv`, to the
last bit. The comparison is therefore like for like with the manuscript.

| Group | current (µm) [95 % CI] | global (µm) [95 % CI] | paired difference (µm) [95 % CI] | relative |
| --- | --- | --- | --- | --- |
| PproA liquid | 18.03 [17.44, 18.61] | 18.72 [17.98, 19.49] | +0.69 [+0.03, +1.38] | +3.8 % |
| WT liquid | 29.58 [28.75, 30.44] | 31.65 [30.68, 32.59] | +2.07 [+0.97, +3.11] | +7.0 % |
| PproB liquid | 36.79 [35.88, 37.74] | 38.67 [37.72, 39.63] | +1.87 [+0.69, +3.05] | +5.1 % |
| PproA agarose | 7.75 [7.55, 7.95] | 8.07 [7.83, 8.31] | +0.32 [+0.06, +0.60] | +4.2 % |
| WT agarose | 17.88 [17.38, 18.39] | 18.03 [17.48, 18.59] | +0.15 [-0.49, +0.78] | +0.8 % |
| PproB agarose | 24.80 [24.09, 25.51] | 26.42 [25.63, 27.18] | +1.62 [+0.88, +2.34] | +6.5 % |

Net displacement rises by 0.8 % to 7.0 %. The rise is real, not noise, for five
of the six groups. It is small, and it has a cause: cells spend less time
stopped, so they cover slightly more ground.

## 6. The strain ratios are unchanged

| Ratio | current [95 % CI] | global [95 % CI] | shift [95 % CI] |
| --- | --- | --- | --- |
| WT/PproA liquid | 1.641 [1.585, 1.702] | 1.690 [1.622, 1.761] | +0.050 [-0.032, +0.130] |
| PproB/PproA liquid | 2.041 [1.968, 2.121] | 2.065 [1.988, 2.147] | +0.025 [-0.067, +0.115] |
| WT/PproA agarose | 2.308 [2.234, 2.386] | 2.235 [2.148, 2.324] | -0.073 [-0.186, +0.040] |
| PproB/PproA agarose | 3.201 [3.094, 3.312] | 3.274 [3.159, 3.394] | +0.072 [-0.075, +0.222] |

Every shift has a 95 % interval that contains zero. The ordering
PproA < WT < PproB holds in both media under both models, and the magnitudes are
the same within the seed noise.

This is the load-bearing result. **The invented per-strain turn angle was not
driving the reported strain differences.** Removing it changes no conclusion in
the paper. The choice can therefore be made on provenance alone, which is how it
should be made.

## 7. Numbers that change if the variant is adopted

Nothing changes unless the builders are pointed at the variant table. If they
are, these reported numbers move:

- **Figure 5D and 5E**, `build/statistics/Figure_5/{D,E}/*_simulation_interval.csv`.
  Group means move as in section 5: liquid 18.03 → 18.72, 29.58 → 31.65,
  36.79 → 38.67 µm; agarose 7.75 → 8.07, 17.88 → 18.03, 24.80 → 26.42 µm. The
  seed clouds and the 2.5-97.5 % intervals move with them. The panel ordering and
  the conclusion do not change.
- **Supplementary Table X**, the row `turn_angle_sd_rad`: six values
  (0.633, 0.646, 0.301, 0.804, 0.746, 0.328) become one value, 1.247. Its Source
  changes from "Nominal" to a citation.
- **Supplementary Table X**, the rows `rotational_diffusion_rad2_s` and
  `reorientation_rate_s`: every value falls, as in section 3. Both stay "Fitted".
- **Supplementary Table X**, derived `tau`: **unchanged**, by construction.
- **Supplementary Figure 4** (`analyses/supplementary_05/`): the trajectory maps
  are redrawn. Same seeds, visibly straighter runs and sharper turns.
- **Methods**: the sentence that calls the turn width a nominal value of the
  published code is replaced by the Taute anchor, the `sqrt(2/pi)` mapping, and
  the two limits in section 2.

Figures 1, 2, 3, 4, 6 and 7 are untouched.

## 8. Why not keep the current model

The only argument for keeping it is that it is already built. Against it:

- Six numbers with no source, which the paper must defend to a reviewer who has
  read Taute et al.
- One of those numbers invents a behavioural difference between PproB and the
  other strains, in a figure about flagella number and directional persistence.
  That is the weakest point in the current simulation section.
- Its mean turns of 14 to 37 deg are 1.5 to 4 times smaller than the only
  published figure.

The variant answers all three at the cost of a 0.8 % to 7.0 % shift in a
simulated quantity that the paper already labels a model output, and no change
to any ratio.

## 9. What the variant does not fix

Stated plainly, because adopting it must not be oversold.

- `reorientation_duration_s` was 0.05 s in every row against a published 0.19 s,
  and it had no source. **Resolved on 14 August 2026 by a different route: the
  parameter is removed.** It is deleted from `MotilityParameters` and its column
  sits in `RETIRED_COLUMNS`. It is not set to zero; it is not a parameter of the
  model at all, and it must not be reintroduced. The persistence relation this
  comparison works with,
  `tau = 1 / (D_theta + lambda * (1 - exp(-sigma^2 / 2)))`, carries no duration
  term, so the model reorients instantaneously and has no reorientation duration
  left to source. Everything measured in this document predates that correction.
  Its conclusion is unaffected, because the turn-width decision rests on
  comparing two parameter tables under one fixed set of dynamics, and the
  correction changes the dynamics for both alike. See
  `models/motility_simulation/corrected/README.md` and
  `tests/test_corrected_motility_dynamics.py`.
- `stall_probability` and `stall_mean_duration_s` still have no source.
  `stall_probability` is now a per-contact-event probability rather than a
  per-time-step one, which is what its Grognot anchor measures; only its ratio
  between strains is anchored.
- `rotational_diffusion_rad2_s` is still a fitted lumped rate, 100 times the
  measured rotational diffusion of a swimming cell, and must not be called
  rotational diffusion.
- The persistence time is still our measured short-window 2D `tau` of 0.064 to
  0.143 s. It is not a run duration, and neither model reproduces run-and-tumble
  on the published 0.6 s timescale.
- The turn-angle distribution is still Gaussian, not the measured forward-skewed
  shape.

The variant fixes one parameter out of five that lacked provenance. It is worth
doing because it is the one that invented a strain difference.

## 10. Reproduce

    PYTHONPATH=$PWD/src .venv/bin/python \
        analyses/motility_turn_angle_comparison/calibrate_global_turn_angle.py

    PYTHONPATH=$PWD/src MPLBACKEND=Agg .venv/bin/python \
        analyses/motility_turn_angle_comparison/compare_turn_angle_models.py

Tables and figures land in `build/diagnostics/turn_angle_comparison/`. The
variant parameter table lands in
`data/processed/motility_turn_angle_comparison/`. See
`analyses/motility_turn_angle_comparison/README.md` for how to adopt it.
