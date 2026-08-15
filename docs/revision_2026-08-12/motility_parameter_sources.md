# Sources for the active-particle motility parameters

Date: 2026-08-13, updated 2026-08-14. Scope: the parameter table of the active-particle
simulation in `models/motility_simulation/upstream/data/motility_summary_parameters.csv`
and its adopted calibrated form in
`data/processed/motility_adopted_parameters/motility_summary_parameters_adopted.csv`,
derived at build time by
`analyses/motility_adopted_parameters/derive_adopted_parameters.py`.

Purpose: give each parameter a traceable source, or say plainly that it has none.
The first version of the simulator was written by a language model. The parameters
below therefore had no provenance. This document records what the literature says
and where it says nothing.

Rule applied throughout: no value is listed unless it was read from the source text.
Where a value could not be verified, the entry says "not verified".

**Change of 13 August 2026: `turn_angle_sd_rad` is now sourced.** This review
found six per-strain turn widths with no source, one of which invented a
behavioural difference for PproB. The manuscript replaced all six with one
global value, 1.2468 rad, anchored to the 57 deg mean turn angle of Taute et al.
2015. Section 3 records both the old state and the new one. The adopted table
closes on the same measured `tau`, so `rotational_diffusion_rad2_s` and
`reorientation_rate_s` took lower fitted values; the ranges below are the
adopted ones. See
[`turn_angle_model_comparison.md`](turn_angle_model_comparison.md).

**Change of 14 August 2026: the two stall parameters were rebuilt.** The
delivered table put the flagella dependence in `stall_mean_duration_s` and gave
`stall_probability` three per-strain values that are not monotone in flagella
number. Neither had a source. The only published measurement says the opposite:
Grognot et al. 2023 measured a significant flagella effect on the stall
*frequency*, 1.7 +/- 0.2 in 0.25 % agar, and found the effect on stall *duration*
significant only at 0.16 % agar, not at 0.25 %. The adopted table therefore
scales `stall_probability` with the mean hook number as `N^-0.704` and makes
`stall_mean_duration_s` one global value, 0.9489 s. Sections 6 and 7 record both
states. See
[`stall_parameter_comparison.md`](stall_parameter_comparison.md).

**Change of 14 August 2026: four global noise constants are now declared.** The model
scales its random motion by four constants that appeared in no table:
`run_translational_scale` 0.12, `stall_translational_scale` 0.20, `stall_slide_fraction`
0.28 and `stall_rotational_diffusion_scale` 1.8. None has a source. They also order
translational noise the wrong way round: a running cell diffuses about eight times less than
a stopped one. Section 8 measures the size of that defect against a physically ordered
alternative and states why we declare the constants rather than change them. The stalled-cell
scale was a bare number inside the loop; it now carries a config key.

The simulator is two-dimensional. Its heading update during a run is
`theta += sqrt(2 * D_r * dt) * N(0,1)`, so the model convention is
`<(delta theta)^2> = 2 * D_r * dt`. This is the same convention Drescher et al. use,
so the comparison below is like for like.

Persistence relation used by the calibration:
`tau = 1 / (D_r + lambda * (1 - exp(-sigma^2 / 2)))`.

---

## Summary table

| parameter | delivered value | published value | organism | source | verdict |
|---|---|---|---|---|---|
| `rotational_diffusion_rad2_s` | 1.32 – 9.54 (adopted: 4.23 – 8.56) | 0.057 rad^2/s, swimming cells far from surfaces | *E. coli* | Drescher K, Dunkel J, Cisneros LH, Ganguly S, Goldstein RE (2011) PNAS 108:10940–10945. [10.1073/pnas.1019079108](https://doi.org/10.1073/pnas.1019079108), PMID 21690349 | **differs from literature** — 23x to 167x larger as delivered, 74x to 150x larger after calibration. See section 1. |
| `rotational_diffusion_rad2_s` (as a tumble-phase term) | as above | 1.6 – 4.4 rad^2/s, *active* rotational diffusion **during tumbles**; 0.16 rad^2/s for a passive 1 µm sphere in water | *E. coli* | Saragosti J, Silberzan P, Buguin A (2012) PLoS ONE 7:e35412. [10.1371/journal.pone.0035412](https://doi.org/10.1371/journal.pone.0035412), PMID 22530021 | **differs from literature** — the delivered magnitude matches the tumble-phase value, but the simulator applies the term during runs. See section 1. |
| `reorientation_rate_s` | 1.78 – 12.72 (adopted: 5.09 – 13.15) | 1/0.64 s = 1.56 s^-1 (mean run 0.64 s, n = 2551 cells, 14188 s of track) | *E. coli* AW405 | Taute KM, Gude S, Tans SJ, Shimizu TS (2015) Nat Commun 6:8776. [10.1038/ncomms9776](https://doi.org/10.1038/ncomms9776), PMID 26522289 | **differs from literature** — 1.1x to 8.2x larger as delivered, 3.3x to 8.4x after calibration. See section 2. |
| `reorientation_rate_s` (Salmonella check) | as above | mean run duration ≈ 1 s, so ≈ 1 s^-1 | *S.* Typhimurium SJW1103 | Nakai T, Ando T, Goto T (2021) Biophys J 120:2623–2630. [10.1016/j.bpj.2021.04.033](https://doi.org/10.1016/j.bpj.2021.04.033), PMID 33964275 | **differs from literature** — same direction, larger factor. |
| `turn_angle_sd_rad` | delivered 0.301 – 0.804 rad (17.3° – 46.0°); **adopted 1.2468 rad (71.4°) in every row** | population mean turn angle 57° (3D, n = 8058 turns); earlier report 68° | *E. coli* AW405 | Taute et al. 2015 (above); the 68° figure is attributed there to Berg HC, Brown DA (1972) Nature 239:500–504, [10.1038/239500a0](https://doi.org/10.1038/239500a0), PMID 4563019 | **sourced** — the adopted value is set so `sigma * sqrt(2/pi)` equals the published 57°. The six delivered values had no source and were 1.6x to 4x too small. See section 3. |
| `turn_angle_sd_rad` (Salmonella check) | as above | turn-angle distribution "almost uniform (random direction)" for cells swimming down the gradient | *S.* Typhimurium SJW1103 | Nakai et al. 2021 (above) | **differs from literature** — a uniform turn has a mean magnitude of 90°; the adopted Gaussian realises 56.5° after the heading wrap. Closer than the delivered 14°–37°, still narrower than uniform. |
| `reorientation_duration_s` | delivered 0.05 s (all rows); **retired 14 August 2026 — no longer a model parameter** | 0.19 s (mean tumble, n = 2551 cells) | *E. coli* AW405 | Taute et al. 2015 (above) | **retired** — the model now reorients instantaneously, which is what the persistence relation the turning parameters are fitted through describes. The delivered 0.05 s equalled the upstream time step exactly, which is evidence it was never a measured duration. See section 4. |
| `passive_diffusion_um2_s` | 0.35 µm^2/s (all rows) | 0.36 µm^2/s by Stokes–Einstein at 20 °C for an equivalent sphere of radius 0.592 µm | *S.* Typhimurium (cell dimensions) | Calculation below; cell dimensions 1–2 µm long, 0.6–0.8 µm wide from Nakai et al. 2021 (above) | **matches literature** — within 3 % of the Stokes–Einstein value at 20 °C. See section 5. |
| `stall_probability` | delivered 0.000 (liquid); 0.087, 0.146, 0.277 (agarose); **adopted 0.000 (liquid); PproA 0.2099, WT 0.1766, PproB 0.1235 (agarose)** | lateral flagella lower the chance of stalling by 1.7 ± 0.2 (mean ± SD) in 0.25 % agar | *V. alginolyticus* | Grognot M, Nam JW, Elson LE, Taute KM (2023) Proc Natl Acad Sci USA 120:e2301873120, [10.1073/pnas.2301873120](https://doi.org/10.1073/pnas.2301873120), PMID 37579142 | **ratio sourced, absolute value nominal** — the adopted values scale as `N^-0.704` so the extreme-strain ratio equals the published 1.7. The delivered three were not monotone in flagella number and had no source. See section 6. |
| `stall_mean_duration_s` | delivered 0.05 s (liquid); 0.298, 0.735, 1.813 s (agarose); **adopted 0.05 s (liquid); 0.9489 s in all three agarose rows** | trapping durations 0.4 – 40 s, power-law distributed (*E. coli*, jammed hydrogel, pores 1–13 µm); mean dwell times 2.07 s and 3.63 s in 0.25 % and 0.30 % agar (*P. putida*) | *E. coli*; *P. putida* | Bhattacharjee T, Datta SS (2019) Nat Commun 10:2075, [10.1038/s41467-019-10115-1](https://doi.org/10.1038/s41467-019-10115-1), PMID 31061418. Datta A, Beier S, Pfeifer V, Großmann R, Beta C (2025) Sci Rep 15:20320, [10.1038/s41598-025-02741-1](https://doi.org/10.1038/s41598-025-02741-1), PMID 40579453 | **no source found — nominal value**, constrained only qualitatively. One global value is what the evidence supports: Grognot et al. 2023 found the flagella effect on stall duration significant only at 0.16 % agar, not at the 0.25 % that matches our condition. See section 7. |
| `run_speed_um_s` | 15.42 – 31.97 µm/s | — | *S.* Typhimurium (our strains) | our paired experimental-unit measurements | **derived from our data** |
| `motile_fraction` | 0.420 – 0.860 | — | *S.* Typhimurium (our strains) | our paired experimental-unit measurements | **derived from our data** |
| `rotational_diffusion_rad2_s` and `reorientation_rate_s` (as used in the figures) | adopted values above | — | *S.* Typhimurium (our strains) | `analyses/motility_turn_angle_comparison/calibrate_global_turn_angle.py` | **derived from our data** — both rates keep their delivered ratio and are scaled by one factor per row so the model `tau` equals our measured `tau`. Scale factors 0.61 to 3.84. |

Notes on the table.

* The delivered ranges exclude nothing; `WT_slow` repeats the `WT` turning values.
* The adopted table drops `WT_slow` and is the one table every manuscript panel reads,
  through `adopted_parameter_table_path()` (`analyses/figure_05_revision/build.py`,
  `analyses/figure_05_revision/timestep_convergence.py`,
  `analyses/supplementary_04/build_s4.py`,
  `analyses/motility_parameter_calibration/make_supplementary_table.py`).
* `turn_angle_sd_rad` is substituted before the closure runs. `passive_diffusion_um2_s`
  passes through the calibration unchanged. `reorientation_duration_s` is dropped from the
  adopted table, because the corrected dynamics have no such parameter.
* `stall_probability` and `stall_mean_duration_s` also pass through the closure unchanged,
  and are then replaced in the three agarose rows by the adopted values. The liquid rows
  keep `stall_probability` 0, so their `stall_mean_duration_s` never fires.
* The scale factors fall from 0.80–6.16 to 0.61–3.84 because a wider turn does more work
  per reorientation, so the same measured `tau` needs lower rates.

---

## 1. `rotational_diffusion_rad2_s` — the name does not describe the quantity

**Verdict: the delivered numbers cannot be the rotational diffusion of a swimming cell body.**

Drescher et al. measured `D_r = 0.057 rad^2/s` for *E. coli* swimming far from surfaces.
They obtained it from the two-dimensional relation `<|delta phi|^2> = 2 * D_r * delta t`,
using tracks of cells that swam in the focal plane for more than 1.5 s, 50 µm from either
surface. Their cells swam at `V_0 = 22 ± 5 µm/s`.

The delivered values are 1.32 to 9.54 rad^2/s. That is 23x to 167x larger. After
calibration they are 4.23 to 8.56 rad^2/s, which is 74x to 150x larger. No physical
change of cell size or temperature closes a factor of 100. Stokes–Einstein–Debye for a
sphere of radius 1 µm in water gives 0.16 rad^2/s, which Saragosti et al. state
explicitly; for a sphere of radius 0.592 µm it gives 0.77 rad^2/s. Both are far below
the delivered numbers, and a swimming cell carries a flagellar bundle that adds rotational
drag, so the true swimming value is lower still, as Drescher et al. measured.

Where the delivered magnitude does fit: Saragosti et al. modelled *E. coli* tumbles as an
*active* rotational diffusion process and measured `D_r` between 1.6 and 4.4 rad^2/s,
depending on strain, medium and gradient. They note this is "two orders of magnitude larger
than passive diffusion coefficients of colloids of comparable size". The delivered range
sits on top of that active tumble-phase range.

But the simulator applies the term inside the `run` state, not the `reorient` state
(`simulation.py`, the `state_run` branch). So the parameter is used as a run-phase heading
noise while carrying a magnitude that belongs to the tumble phase.

**Conclusion.** The delivered `rotational_diffusion_rad2_s` is a lumped effective
reorientation rate, not physical rotational diffusion. The methods section must not call it
"rotational diffusion of the cell body". Call it what the model does: a continuous
heading-randomisation rate that, together with `reorientation_rate_s`, sets the persistence
time. After calibration it is a fitted quantity with no independent physical meaning; only
the sum `D_r + lambda * (1 - exp(-sigma^2/2))` is pinned, by our measured `tau`.

**Effect of using the published value instead.** Setting `D_r = 0.057 rad^2/s` would remove
almost all run-phase heading noise. Persistence would then be set by `reorientation_rate_s`
and `turn_angle_sd_rad` alone. To keep our measured `tau`, `reorientation_rate_s` would have
to rise by roughly the same amount that `D_r` falls. Trajectories would become straighter
between tumbles and more sharply kinked at tumbles. Net displacement statistics, which the
calibration fixes through `tau`, would change little.

## 2. `reorientation_rate_s` — too high

Taute et al. tracked 2551 motile *E. coli* AW405 in 3D and found approximately exponential
run durations with a characteristic time of 0.64 s, giving a tumble rate of 1.56 s^-1.
Nakai et al. report a mean run duration of about 1 s for *S.* Typhimurium SJW1103 in
motility buffer at 30 °C, giving about 1 s^-1.

The delivered values are 1.78 to 12.72 s^-1. Four rows are close to the published figures:
all three liquid rows (`PproA` 1.95, `WT` 2.03, `PproB` 1.89 s^-1) and `PproB` in agarose
(1.78 s^-1). Two rows are not: `PproA` and `WT` in agarose, at 12.68 and 12.72 s^-1. That
split has no stated basis. After calibration every row lies between 5.09 and 13.15 s^-1,
that is 3x to 8x the published value.

This is expected and is not an error: the calibration deliberately forces the model
persistence time onto our measured `tau`, which is 0.064 to 0.143 s. A persistence time of
0.1 s requires a total reorientation rate near 10 s^-1 whatever the parameter is called.
Our measured `tau` comes from two-dimensional tracks over short observation windows and is
not the same quantity as a 3D run duration. The methods section should say this, so the
reader does not read 10 s^-1 as a tumble frequency.

## 3. `turn_angle_sd_rad` — the delivered turns were too small; the adopted value is sourced

**Status: resolved on 13 August 2026.** The six delivered values are replaced by one
global value anchored to Taute et al. 2015. The rest of this section records why.

The model adds `N(0, sigma)` to the heading at the end of a reorientation. The mean turn
magnitude is therefore `sigma * sqrt(2/pi)`:

| delivered sigma (rad) | sigma (deg) | mean turn magnitude (deg) |
|---|---|---|
| 0.301 | 17.3 | 13.8 |
| 0.328 | 18.8 | 15.0 |
| 0.633 | 36.3 | 28.9 |
| 0.646 | 37.0 | 29.5 |
| 0.746 | 42.7 | 34.1 |
| 0.804 | 46.0 | 36.7 |

Taute et al. measured a population mean turn angle of 57° from 8058 turns in 3D, and cite
68° as the earlier figure from Berg & Brown 1972. Nakai et al. found that *S.* Typhimurium
turn angles are close to uniform for cells swimming down a chemoattractant gradient.

So the delivered turns are 1.6x to 4x too small in mean magnitude. Worse, no measurement
of ours distinguishes PproB, yet PproB carries less than half the width of the other two
strains. That split is invented, and it sits inside a figure about flagella number and
directional persistence.

**The adopted value.** Inverting the same relation on the published 57° gives

    sigma = radians(57) / sqrt(2/pi) = 1.2468 rad = 71.4°

One value for all six rows. A heading is periodic, so 1.2 % of draws fold back past
±pi and the realised mean turn magnitude is 56.5°, not 57.0°.
`turn_angle_diagnostics()` in
`analyses/motility_turn_angle_comparison/calibrate_global_turn_angle.py` measures this
rather than assuming it.

Two limits remain, and the methods state both. Taute et al. tracked in three dimensions
and in *E. coli*; the simulator is two-dimensional and the strains are *S.* Typhimurium.
A zero-mean symmetric Gaussian also cannot reproduce the measured shape, which is broad
and skewed toward the forward hemisphere. Only the mean magnitude is matched.

**What the substitution did.** `sigma` enters `tau` only through `1 - exp(-sigma^2/2)`,
which rises from 0.044–0.276 to 0.540. Each turn therefore does more work, and the
calibration lands on lower rates: `rotational_diffusion_rad2_s` falls to 4.23–8.56 and
`reorientation_rate_s` to 5.09–13.15. Both tables close on the same measured `tau`. The
simulated net displacement rose by 0.8 % to 7.0 % and every strain ratio held within the
seed noise. `turn_angle_model_comparison.md` carries the paired comparison.

## 4. `reorientation_duration_s` — retired, not refitted

**Status since 14 August 2026: this is no longer a parameter of the model.** It is absent
from the adopted table and from `MotilityParameters`. What follows records why, because the
retired value had already reached a reported number.

Delivered: 0.05 s in every row. Taute et al. measured approximately exponential tumble
durations with a characteristic time of 0.19 s. Saragosti et al. quote
`<tau_tumble> = 0.14 s` from Berg & Brown 1972. Nakai et al. give about 0.1 s as the
*E. coli* figure and observe many *Salmonella* tumbles of about 0.1 s. The delivered value
was therefore 2x to 4x shorter than any published figure, and it was a single constant
across all six phenotype-by-medium rows, which no measurement supports.

**Why it was retired rather than corrected.** The turning parameters are fitted through

    tau = 1 / (D_r + lambda * (1 - exp(-sigma^2 / 2)))

which carries no duration term. That relation describes a walker which turns instantaneously
and swims the whole time. The simulation instead parked the cell in a non-advancing
`reorient` state for `reorientation_duration_s`, so the parameters were fitted with one model
and simulated with another. The delivered 0.05 s equalled the upstream time step, 0.05 s,
exactly — evidence that the value was a step-sized placeholder and never a measured duration.

The cost was quantitative, not cosmetic. A cell swam only 75 % to 79 % of the time in liquid
and 49 % to 56 % in agarose. The effective diffusivity of a run-and-tumble walker scales as
the square of that ballistic fraction, so the model returned far less spreading than the
calibration targets. The measured shortfall was large: the model delivered 60 % to 61 % of
the measured `D_eff` in liquid and 37 % to 39 % in agarose.

Removing the dwell removes most of the shortfall. The corrected model delivers 87 % to 90 %
in liquid and 69 % to 76 % in agarose. Motile cells are now ballistic 100 % of the time in
liquid and 86 % to 90 % in agarose, and the `reorient` state is never occupied. All ratios
here compare the simulated value with the lag-corrected measured value.
`analyses/motility_effective_diffusivity_check/` measures this per strain and per medium;
the record is
`build/diagnostics/effective_diffusivity_check/effective_diffusivity_comparison.csv`.

**Why the published 0.19 s was not substituted instead.** During a reorientation the cell
does not advance; it only diffuses. The fraction of time spent not swimming is
`d / (1/lambda + d)`. At the calibrated tumble rates (5.09 to 13.15 s^-1, so mean run
intervals of 0.076 to 0.197 s), `d = 0.19 s` would put cells in a non-swimming state 49 % to
71 % of the time and remove most directed motion; the Berg & Brown figure of 0.14 s gives
42 % to 65 %. A duration does not enter `tau`, so the calibration cannot absorb it. A model
with a real tumble duration needs the persistence relation itself refitted with a duration
term, together with the tumble rate. That is a modelling change, not a parameter change, and
we did not make it. What we did instead is simulate the model the parameters were fitted to.

## 5. `passive_diffusion_um2_s` — consistent with Stokes–Einstein

Delivered: 0.35 µm^2/s in every row. Prefer the calculation to a citation.

Stokes–Einstein: `D = k_B * T / (6 * pi * eta * a)`.

Assumptions:
* Cell shape: a capsule 2.0 µm long and 0.8 µm across. This is the upper end of the
  *S.* Typhimurium SJW1103 dimensions reported by Nakai et al. (1–2 µm long,
  0.6–0.8 µm wide).
* Volume of that capsule: 0.871 µm^3. Equivalent-sphere radius `a = 0.592 µm`.
* Temperature `T = 293.15 K` (20 °C); water viscosity `eta = 1.0016 mPa s`.
* `k_B = 1.380649e-23 J/K`.

Result: `D = 0.362 µm^2/s`.

At 30 °C (`eta = 0.7972 mPa s`) the same cell gives `D = 0.470 µm^2/s`.

The delivered 0.35 µm^2/s is within 3 % of the 20 °C value. It is a defensible number.
State the assumed radius, temperature and viscosity in the methods, and state that the
value is a Stokes–Einstein estimate, not a measurement. If the imaging was done at 30 °C,
0.47 µm^2/s is the consistent value. This parameter sets the motion of non-motile cells and
the small noise terms added during runs, reorientations and stalls; a 34 % change in it
moves those terms by 16 % in displacement and does not affect motile-cell statistics much.

## 6. `stall_probability` — the absolute value has no source, the ratio does

No primary source defines a per-collision probability that a swimming cell stalls on an
obstacle. The quantity is specific to this model: it is evaluated once per time step
whenever a proposed step overlaps a disk, and it decides between a stall and a tangential
slide (`simulation.py`, the obstacle branch). Its absolute value is not an observable of
any published experiment.

The delivered values were 0.000 in liquid, which is forced by there being no obstacles, and
0.087, 0.146 and 0.277 in agarose. Ordered by mean hook number — PproA 2.085, WT 2.666,
PproB 4.432 — those are 0.146, 0.277, 0.087. They are not monotone. WT is the stickiest
strain by a factor 1.9 over PproA and 3.2 over PproB, and no mechanism makes the
intermediate strain the stickiest. The three numbers had no source and no pattern.

**What the literature does constrain: the ratio between strains.** Grognot et al. 2023
tracked *V. alginolyticus* with a polar flagellum only against polar plus lateral flagella
in soft agar, 24,248 and 22,101 motile trajectories:

> "on average, lateral flagella decrease the chance of stalling by a factor 1.7 ± 0.2
> (mean ± SD) in 0.25% agar"

They controlled the speed confound by comparing the mean free path at matched swim-phase
speed, so the 1.7 is a per-encounter quantity. That is what `stall_probability` is in this
model.

**The adopted values.** The probability falls with the mean hook number per cell,

    p_s = p_mean * N_s^-a / mean_s(N_s^-a),   a = ln(1.7) / ln(N_PproB / N_PproA) = 0.704

which gives PproA 0.2099, WT 0.1766, PproB 0.1235. The normalisation keeps the mean over
the three strains at the delivered mean, 0.16998, so the adoption redistributes the effect
rather than enlarging it. `N` is read from `hook_count_per_cell.csv`, 29,789 cells.

**Limits, stated first.** Grognot et al. varied a second flagellar system in a marine
*Vibrio*, not the flagella count in *Salmonella*. Mapping 1.7 onto our hook numbers is an
assumption made here. It fixes the ratio between the extreme strains; the power-law form is
a choice. The absolute value stays nominal.

**One artefact the methods must name.** In this model the contact rate rises with swimming
speed, so a *global* probability would make the fast, many-flagella strain stall more often
per second of swimming than the slow one — the opposite of the published direction. The
adopted scaling halves that artefact but does not remove it. Stall occupancy and stall rate
are diagnostics at a stated time step, not converged model outputs.

**Recommendation.** Declare the source class "Literature-scaled" in the methods: the ratio
between strains is set by a published measurement, the absolute value is not.

## 7. `stall_mean_duration_s` — no direct source; two qualitative constraints

No published measurement defines "mean stall duration on an obstacle" as this model uses it.
Two studies constrain the order of magnitude.

Bhattacharjee & Datta tracked individual *E. coli* W3110 in transparent jammed hydrogel
packings with pore sizes from 1 to 13 µm at 30 °C. Cells hop and trap rather than run and
tumble. Trapping durations ranged from about 0.4 s to about 40 s and were power-law
distributed, with the exponent falling weakly from about 2 to about 1 as confinement rose.
Mean hop lengths were 2.14 to 3.24 µm. Their unconfined reference values were a mean run
speed of 28 µm/s and a mean run duration of about 2 s.

Datta et al. tracked *P. putida* in 0.25 % and 0.30 % agar. Mean run times in the gel were
0.35 s and 0.23 s; mean dwell (turn or trap) times were 2.07 s and 3.63 s, with a power-law
dwell-time distribution.

Both point the same way: trapping in a gel or packing is long compared with a tumble, is
broadly distributed, and has a mean of order seconds. The delivered agarose values
(0.298, 0.735, 1.813 s) sit at or below the low end of both. The adopted global value,
0.9489 s, is their arithmetic mean and also sits below both published means. The liquid
value of 0.05 s is inert because `stall_probability` is zero there.

Neither study is a direct source. Bhattacharjee & Datta used a jammed hydrogel-particle
packing, not agarose, and a different organism. Datta et al. used agar but a polar-flagellated
soil bacterium with a different swimming repertoire. Neither reports an exponentially
distributed stall time, which is what the model draws.

**Why one global value and not three.** The delivered table gave each strain its own
duration and so put the whole flagella dependence in this parameter. The only study that
resolves flagellar architecture against stall duration does not support that:

> "While we observed increased stall durations in the P compared to the PL phenotype above
> 0.12% agar, the difference was statistically significant only at 0.16% and not at 0.25%
> agar"

Grognot et al. 2023, as above. 0.25 % agar is the concentration that matches both anchors
of this section. At that concentration the duration effect is not significant, while the
frequency effect is. A per-strain duration therefore claims more than the evidence carries.
One global value is the honest statement of what we know.

**Why the absolute value stays at the delivered mean and not at Datta's 2.07 s.** The
measured agarose `tau` is derived as `2 * D_eff / v^2` from the measured agarose diffusivity
and speed, so it already contains the mesh. The obstacles and the stalls remove a further
17 % to 22 % of the effective diffusivity on top of it. A 2.2-fold longer stall would deepen
that double count. The choice is deliberate and unsourced, and the methods record it as
nominal. See [`stall_parameter_comparison.md`](stall_parameter_comparison.md), section 1.

**Recommendation.** Declare it a nominal value. Cite the two studies as showing that
trapping in a gel is a real phenomenon on the seconds timescale, say that the model's
exponential stall with a mean below 1 s is a simplification of a broad, power-law
distribution, and say why the value is global rather than per strain.

---

## 8. The four global noise constants — no source, and the wrong way round

Four constants scale the random part of the motion. They are global: one value for all six
strain-medium rows. Every one of them changes the physics, and not one has a source. Until
this revision none of them appeared in Supplementary Table X.

| constant | value | where it lives | what it does |
|---|---|---|---|
| `noise.run_translational_scale` | 0.12 | `config.yml` | multiplies `D_t` for a **running** cell |
| `noise.stall_translational_scale` | 0.20 | model constant `STALL_TRANSLATIONAL_SCALE` | multiplies `D_t` for a **stalled** cell |
| `noise.stall_slide_fraction` | 0.28 | `config.yml` | fraction of the tangential step kept when a cell slides past a disk |
| `noise.stall_rotational_diffusion_scale` | 1.8 | `config.yml` | multiplies `D_theta` while a cell is stalled |

`noise.reorientation_diffusion_scale` (0.40) is also in `config.yml`, but only the upstream
model reads it. The corrected model never does, so it is not a parameter of this model and
it is not in the table.

**The stalled-cell scale was invisible.** Upstream wrote `0.20` as a bare number inside the
integration loop. It reached no config file and no table. This revision gives it the config
key `noise.stall_translational_scale` and the module constant `STALL_TRANSLATIONAL_SCALE`.
The value is unchanged, so no figure changes; only its visibility does.

### The inversion

The translational noise variance per state, as a multiple of the passive diffusion
coefficient `D_t = 0.35 µm^2/s`:

| state | scale |
|---|---|
| running | 0.12 |
| stalled | 0.20 |
| non-motile | 1.00 |

A swimming cell therefore diffuses about eight times **less** than a stopped one. That is
backwards. A swimming cell should diffuse at least as much as a stopped one: swimming adds
motion, it does not suppress Brownian motion.

### How large is the error?

We measured it rather than argued about it. The test compares the shipped constants against
the minimal physically ordered alternative, in which every state diffuses at the full passive
rate (running = stalled = non-motile = 1.00). Both arms used the same 100 seeds per group, so
the comparison is paired: 26 cells per seed, `dt` = 0.0025 s, the 1776 x 1152 µm box, and the
adopted parameter table. Intervals are paired percentile bootstraps over the seed pairs,
10 000 draws.

Both scales now carry config keys, so both arms call the shipped `simulate_population`
unchanged and differ only in the config they pass. No integrator is copied, so the
measurement cannot drift from the model it describes. This is the reason the bare `0.20` was
lifted into `noise.stall_translational_scale`: a constant that cannot be varied cannot be
tested. The `current` arm reproduces the `after_corrected` rows of
`effective_diffusivity_comparison.csv` on all six groups.

The script is `analyses/motility_noise_scale_check/measure_noise_scale_sensitivity.py` and
the record is `build/diagnostics/noise_scale_check/noise_scale_comparison.csv`.

**Net displacement (µm) — the observable Figure 5D and 5E plot.**

| group | current | ordered | change | 95 % CI |
|---|---|---|---|---|
| PproA liquid | 24.088 | 24.157 | +0.29 % | [-0.24, +0.81] |
| WT liquid | 44.527 | 44.531 | +0.01 % | [-0.46, +0.47] |
| PproB liquid | 58.013 | 58.513 | +0.86 % | [+0.31, +1.42] |
| PproA agarose | 10.915 | 10.651 | -2.42 % | [-5.48, +0.72] |
| WT agarose | 27.230 | 26.269 | -3.53 % | [-7.07, +0.17] |
| PproB agarose | 35.916 | 35.837 | -0.22 % | [-3.15, +2.91] |

**Effective diffusivity (µm^2/s).** These are the raw `MSD / (4 t)` values, the estimator the
stall comparison uses. The lag correction is the same in both arms, so it cancels and the
relative changes below also hold for the lag-corrected column.

| group | current | ordered | change | 95 % CI |
|---|---|---|---|---|
| PproA liquid | 19.544 | 19.857 | +1.60 % | [+1.36, +1.83] |
| WT liquid | 44.491 | 44.817 | +0.73 % | [+0.48, +0.97] |
| PproB liquid | 67.780 | 68.142 | +0.53 % | [+0.33, +0.74] |
| PproA agarose | 6.130 | 6.043 | -1.43 % | [-4.37, +1.47] |
| WT agarose | 19.794 | 18.630 | -5.88 % | [-8.15, -3.59] |
| PproB agarose | 35.564 | 33.345 | -6.24 % | [-8.02, -4.46] |

The agarose `PproB/PproA` effective-diffusivity ratio moves from 5.80 to 5.52, a change of
-4.88 % [-8.39, -1.19].

**Liquid agrees with the analytic prediction.** In liquid `stall_probability` is zero, so a
motile cell runs the whole time and raising the run scale from 0.12 to 1.00 must add exactly
`D_t * (1.00 - 0.12)` = 0.308 µm^2/s. The measured additions are 0.313, 0.326 and
0.362 µm^2/s, and every confidence interval contains 0.308.

**Agarose does not, and the reason is real.** The analytic term predicts +0.8 % to +4.9 %;
the simulation returns -1.4 % to -6.2 %. Larger translational noise pushes cells into disks
more often. Contact events rise by 36 % to 56 %, stall entries rise with them, and the stall
occupancy of motile cells rises from 0.101–0.135 to 0.126–0.159. The lost duty cycle more
than cancels the added diffusivity. In agarose the noise scale therefore controls the
obstacle encounter rate as well as the noise, which is a second coupling and not an error.

### Verdict and what we did

The effect is **negligible for the plotted observable and material for agarose effective
diffusivity**. Net displacement moves by at most 3.5 %, and no agarose interval excludes
zero. Agarose effective diffusivity moves by -6.2 % [-8.0, -4.5], which does exclude zero.

We therefore **declare the constants and keep their values**. Changing them would alter a
calibrated model on no evidence, because the ordered alternative has no source either. Three
things follow:

1. All four constants are rows of Supplementary Table X, source class **Nominal**, each
   stating plainly that it has no source.
2. The stalled-cell scale now has a config key, so a reader can find it and vary it.
3. The methods state the agarose effective-diffusivity sensitivity as a limitation. The
   effective-diffusivity diagnostic must not be called insensitive to a choice it was not
   allowed to vary.

---

## What the methods section can and cannot claim

Can claim, with citation:
* `passive_diffusion_um2_s` is a Stokes–Einstein estimate; show the radius, temperature and
  viscosity.
* `run_speed_um_s` and `motile_fraction` come from our measurements.
* `rotational_diffusion_rad2_s` and `reorientation_rate_s` were rescaled in this repository
  so the model persistence time matches our measured `tau`.
* `turn_angle_sd_rad` is set so the mean turn magnitude equals the 57° measured by
  Taute et al. 2015. State the `sqrt(2/pi)` mapping, the 3D-to-2D limit and the
  *E. coli*-to-*Salmonella* limit alongside it.
* The *ratio* of `stall_probability` between strains is set by the 1.7 ± 0.2 stall-frequency
  ratio of Grognot et al. 2023. State the `N^-0.704` mapping, the *Vibrio*-to-*Salmonella*
  limit and the flagellar-system-to-flagella-count limit alongside it.
* `stall_mean_duration_s` is one global value because the flagella effect on stall duration
  is not significant at 0.25 % agar (Grognot et al. 2023).

Must not claim:
* That `rotational_diffusion_rad2_s` is the rotational diffusion of the cell body. It is
  20x to 200x the measured value (Drescher et al. 2011) and is used as a lumped
  reorientation rate.
* That `reorientation_rate_s` is a tumble frequency comparable to published run-and-tumble
  statistics. It is 3x to 8x the published *E. coli* and *Salmonella* values, because it is
  fitted to our short-window `tau`.
* That the model reproduces the *shape* of the measured turn-angle distribution. It matches
  the mean magnitude only; the measured shape is broad and forward-skewed.
* That `stall_mean_duration_s` has any source. It does not. `reorientation_duration_s` is
  retired and is not a parameter at all; do not reintroduce it.
* That the *absolute* `stall_probability` has a source. Only its ratio between strains has
  one. Do not call the parameter measured. It is a per-contact-event probability, which is
  the same kind of quantity Grognot et al. measured.
* That the model reproduces the measured effective diffusivity in agarose. It delivers 87 %
  to 90 % of it in liquid, but only 69 % to 76 % in agarose. The agarose gap has a known
  cause: the measured agarose `tau` is derived as `2 D_eff / v^2` from tracks recorded in
  agarose, so it already contains the mesh, and the model then adds obstacles and stalls on
  top of it. The mesh is counted twice. State this as a limitation.
* That the four global noise constants have any source. They do not. See section 8.
* That the effective diffusivity in agarose is insensitive to the noise constants. It is not:
  a physically ordered alternative moves it by up to 6.2 %. See section 8.

## References

1. Berg HC, Brown DA (1972) Chemotaxis in *Escherichia coli* analysed by three-dimensional
   tracking. Nature 239:500–504. [10.1038/239500a0](https://doi.org/10.1038/239500a0). PMID 4563019.
   Values used here are quoted from Taute et al. 2015 and Saragosti et al. 2012; the
   original text was not accessible for this review.
2. Drescher K, Dunkel J, Cisneros LH, Ganguly S, Goldstein RE (2011) Fluid dynamics and
   noise in bacterial cell-cell and cell-surface scattering. PNAS 108:10940–10945.
   [10.1073/pnas.1019079108](https://doi.org/10.1073/pnas.1019079108). PMID 21690349.
3. Saragosti J, Silberzan P, Buguin A (2012) Modeling *E. coli* tumbles by rotational
   diffusion. Implications for chemotaxis. PLoS ONE 7:e35412.
   [10.1371/journal.pone.0035412](https://doi.org/10.1371/journal.pone.0035412). PMID 22530021.
4. Taute KM, Gude S, Tans SJ, Shimizu TS (2015) High-throughput 3D tracking of bacteria on a
   standard phase contrast microscope. Nat Commun 6:8776.
   [10.1038/ncomms9776](https://doi.org/10.1038/ncomms9776). PMID 26522289.
5. Nakai T, Ando T, Goto T (2021) Biased reorientation in the chemotaxis of peritrichous
   bacteria *Salmonella enterica* serovar Typhimurium. Biophys J 120:2623–2630.
   [10.1016/j.bpj.2021.04.033](https://doi.org/10.1016/j.bpj.2021.04.033). PMID 33964275.
6. Bhattacharjee T, Datta SS (2019) Bacterial hopping and trapping in porous media.
   Nat Commun 10:2075. [10.1038/s41467-019-10115-1](https://doi.org/10.1038/s41467-019-10115-1).
   PMID 31061418.
7. Bhattacharjee T, Datta SS (2019) Confinement and activity regulate bacterial motion in
   porous media. Soft Matter 15:9920–9930.
   [10.1039/c9sm01735f](https://doi.org/10.1039/c9sm01735f). PMID 31750508.
8. Datta A, Beier S, Pfeifer V, Großmann R, Beta C (2025) Bacterial swimming in porous gels
   exhibits intermittent run motility with active turns and mechanical trapping.
   Sci Rep 15:20320. [10.1038/s41598-025-02741-1](https://doi.org/10.1038/s41598-025-02741-1).
   PMID 40579453.

Bibliographic records for references 2–8 were retrieved from PubMed.

## Not verified

* The rotational diffusion coefficient reported inside Berg & Brown 1972 itself. The paper
  is paywalled and no accessible source quoted a numerical value for it. Use Drescher et al.
  2011 for the swimming-cell figure.
* Any *Salmonella*-specific measurement of rotational diffusion, tumble duration or
  translational Brownian diffusion. None was found.
* Any measurement of a stall probability or stall duration on discrete obstacles in agarose.
  None was found.
