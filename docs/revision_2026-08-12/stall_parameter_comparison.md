# What to do with the two stall parameters

Date: 2026-08-13.

> **ADOPTED, 14 August 2026.** Marc approved variant G. It is now in the one
> canonical parameter table that every manuscript panel reads,
> `data/processed/motility_adopted_parameters/motility_summary_parameters_adopted.csv`,
> derived at build time by
> `analyses/motility_adopted_parameters/derive_adopted_parameters.py`. Figure 5D,
> Figure 5E, Supplementary Figure 4, the time-step convergence ladder and
> Supplementary Table X reach that table only through
> `adopted_parameter_table_path()`. No manuscript path reads any other parameter
> file.
>
> **The figures also run the corrected dynamics.** The panels no longer run the
> dynamics this document measured. They run
> `models/motility_simulation/corrected/`: reorientation is instantaneous, the
> stall test fires once per contact event, and the obstacle count scales with the
> box area. The rebuilt numbers are in [`change_log.md`](change_log.md).
>
> This document keeps the full comparison that led to the decision; sections 3 to
> 5 below describe the grid as it stood before the adoption, so the "current
> model" in them is variant A, not the adopted table.

> **DYNAMICS CORRECTED, 14 August 2026 — read this before reusing any number
> below.** Every simulation in this document ran under the upstream dynamics,
> which have since been corrected in three ways
> (`models/motility_simulation/corrected/README.md`). Two of them change what the
> numbers below mean:
>
> * `stall_probability` was drawn at **every time step** of obstacle overlap. It
>   is now drawn **once per contact event**. The parameter therefore now means a
>   per-encounter probability, which is what Grognot et al. measured. The
>   adoption of variant G is unaffected: it rests on the **ratio** between
>   strains, and the correction rescales all three strains alike. The absolute
>   probability had no source before and still has none.
> * Reorientation was a non-advancing dwell and is now instantaneous, so the
>   duty-cycle diagnosis in section 1 is resolved rather than open.
>
> The variant grid was not re-run under the corrected dynamics. The decision it
> supports is a decision about the shape of the flagella dependence, which the
> correction does not touch. Absolute values quoted below — retained
> `D_eff` fractions, net-displacement costs, stall occupancy — are properties of
> the retired dynamics. Do not quote them as current. Current values live in
> `build/diagnostics/effective_diffusivity_check/` and in `change_log.md`.

**Recommendation: variant G.** Make `stall_mean_duration_s` one global value and
let `stall_probability` fall with flagella number at the strength Grognot et al.
2023 measured, `p ∝ N^-0.70`.

This inverts the shape of the current table. Today the *duration* carries the
flagella-number effect and the *probability* is an unexplained per-strain
number. The only published measurement of either quantity says the opposite: the
flagella effect is on the **chance of stalling**, and it is significant, while
the effect on stall duration is not significant at the matching agar
concentration.

**Adopting G weakens the agarose simulation result.** PproB loses 8.0 % of its
net displacement and the PproB/PproA ratio falls from 3.27 to 2.98. The strain
ordering survives and stays resolved. The measured agarose result in Figure 7 is
untouched, because none of this changes a measurement. Marc should make this
call with that trade in front of him.

Method, code and outputs: `analyses/motility_stall_parameter_comparison/` and
`build/diagnostics/stall_parameter_comparison/`.

---

## 1. The double-counting finding — read this first

**Verdict: yes, the agarose model represents the mesh more than once. The second
representation removes 17 % to 22 % of the effective diffusivity that the
measured persistence time already contains.**

The 17 % to 22 % is the current figure. It is measured under the corrected
dynamics against the model's own implied `v^2 tau / 2`, in
`build/diagnostics/effective_diffusivity_check/effective_diffusivity_comparison.csv`.
The variant grid in section 3 ran under the upstream dynamics and put the same
double count at 17 % to 36 %. The finding does not change; only its size does.

### Why the suspicion was right in principle

The measured agarose `tau` comes from cells tracked in agarose. It is also not
an independent measurement of persistence.
`analyses/figure_07_revision/build_figure_07_revision.py` derives it as

    tau = 2 * D_eff / v^2

from the measured agarose diffusivity and the measured agarose speed. An
idealised run-and-tumble walker carrying the measured speed and the measured
`tau` therefore reproduces the measured agarose `D_eff` **by construction**.
(This simulator falls short of that ideal for a separate reason, given below.)
The 58 obstacles and the stalls are then added on top of a number that already
contains the mesh.

### What the measurement is

Mean over 36 paired experimental units, agarose. `D` is
`diff_med_<phenotype>`; `v^2 tau / 2` is shown as the closure check.

| | PproA | WT | PproB |
| --- | --- | --- | --- |
| measured speed (µm/s) | 15.42 | 23.19 | 28.65 |
| measured `tau` (s) | 0.0638 | 0.0992 | 0.1131 |
| measured `D_eff` (µm²/s) | 8.31 | 28.86 | 54.47 |
| `v^2 tau / 2` (µm²/s) | 7.59 | 26.67 | 46.41 |

### The ladder

Same 100 seeds, 26 cells, 20 s, `dt = 0.0025 s`, agarose parameters throughout.
`D_eff` is estimated from the mean squared displacement of motile cells at a 2 s
lag, inside the same 148 x 96 µm box with the same reflecting boundary.

Mean net displacement per seed (µm):

| condition | PproA | WT | PproB |
| --- | --- | --- | --- |
| Brownian walker at the measured `D_eff` | 11.16 | 27.11 | 33.40 |
| model, measured `tau` only | 9.22 | 22.31 | 28.70 |
| + 58 obstacles | 8.68 | 21.79 | 27.35 |
| + stalls (**current model**) | 8.07 | 18.03 | 26.42 |

Effective diffusivity (µm²/s):

| condition | PproA | WT | PproB |
| --- | --- | --- | --- |
| **measured `D_eff`** | **8.31** | **28.86** | **54.47** |
| Brownian walker at the measured `D_eff` | 7.85 | 26.34 | 47.20 |
| model, measured `tau` only | 4.09 | 16.13 | 28.29 |
| + 58 obstacles | 3.72 | 15.05 | 25.38 |
| + stalls (**current model**) | 2.96 | 10.36 | 23.37 |

Three things fall out.

**The estimator is sound.** The Brownian walker recovers 87 % to 94 % of the
measured `D_eff`. The 6 % to 13 % shortfall is the reflecting box, not a
modelling error, and it applies equally to every rung.

**The double counting is real, and this grid puts it at 17 % to 36 % of `D_eff`.**
These are upstream-dynamics numbers; the corrected model puts the same double
count at 17 % to 22 %. Against the
measured-`tau`-only model, the obstacles alone cost 7 % to 10 % of `D_eff` and
2 % to 6 % of net displacement; the stalls cost a further 8 % to 31 % of `D_eff`.
Together they remove

| | PproA | WT | PproB |
| --- | --- | --- | --- |
| `D_eff` retained | 0.72 | 0.64 | 0.83 |
| net displacement retained | 0.875 | 0.808 | 0.921 |
| paired bootstrap CI on displacement | 0.847–0.905 | 0.783–0.836 | 0.889–0.953 |

**A separate and larger problem, which is not double counting.** Even with no
obstacles and no stalls, the model delivers only 49 % to 56 % of the measured
`D_eff`. The liquid model does the same: 56 % to 58 % of the measured liquid
`D_eff`. The shortfall is therefore medium-independent, so it is not the mesh
being counted twice. It is the reorientation duty cycle. At the calibrated
tumble rates a motile cell sits in the non-swimming `reorient` state 20 % to
40 % of the time, so its effective speed is well below `run_speed_um_s`, while
the calibration closes only `tau`. `motility_parameter_sources.md`, section 4,
records the `reorientation_duration_s` behind this.

**Fixed on 14 August 2026.** The parameter is removed from the model and
reorientation is instantaneous, so the `reorient` state no longer exists. Its
occupancy now reads 0.000 in every row. Under the lag-corrected convention the
corrected model delivers 87 % to 90 % of the measured `D_eff` in liquid and 69 %
to 76 % in agarose. Only the agarose gap remains, and it is the double count
above. Do not quote the 49 % to 58 % figures in this paragraph as current.

### What this changes about the stall parameters

It does not say they must not exist. It says three things.

1. They have no free budget. Anything they remove is removed from a `tau` that
   already contains the mesh. So they must stay small, and they must not be
   tuned upward to make agarose "look harder".
2. **They are not what produces the strain difference in agarose.** Strain
   ratios of net displacement along the ladder:

   | | WT/PproA | PproB/PproA |
   | --- | --- | --- |
   | Brownian walker at the measured `D_eff` | 2.43 | 2.99 |
   | model, measured `tau` only | 2.42 | 3.11 |
   | + obstacles | 2.51 | 3.15 |
   | + stalls (current model) | 2.23 | 3.27 |

   The separation is already there before any obstacle or stall, and it is the
   separation the measurement implies. The measured speed, `tau` and motile
   fraction do all the work. The current stall parameters move `PproB/PproA`
   **away** from the measurement-implied 2.99–3.11, up to 3.27.
3. Any variant that pushes `PproB/PproA` further above 3.11 is inflating a
   result the measurement does not support.

---

## 2. The literature, as checked

Read from the sources, not from memory. Retrieved through PubMed.

### Grognot et al. 2023 — the anchor survives, and it points at the probability

*Vibrio alginolyticus*, polar flagellum only (P) against polar plus lateral (PL).
PNAS 120:e2301873120, [doi 10.1073/pnas.2301873120](https://doi.org/10.1073/pnas.2301873120),
PMID 37579142. Verified from the full text:

> "on average, lateral flagella decrease the chance of stalling by a factor
> 1.7 ± 0.2 (mean ± SD) in 0.25% agar"

> "While we observed increased stall durations in the P compared to the PL
> phenotype above 0.12% agar, the difference was statistically significant only
> at 0.16% and not at 0.25% agar"

> "Thus, both the duration and the temporal frequency of stalls are decreased in
> the presence of lateral flagella."

`flagella_number_literature.md` quoted only the first sentence. The second and
third are added here, because they decide the question.

**Reading.** Richer flagellar architecture lowers both the stall frequency and
the stall duration. Only the frequency effect is significant at 0.25 % agar, and
only the frequency effect has a number: 1.7 ± 0.2. The paper's own summary of
the mechanism is "preventing trapping in pores", not faster escape from a pore.

**The speed confound was controlled.** The authors asked whether the lower stall
frequency of PL only reflects the longer time a slower cell needs to reach a
trap, and answered it by comparing the mean free path at matched swim-phase
speed. PL kept a longer or equal mean free path. The 1.7 is therefore a
per-encounter quantity, which is exactly what `stall_probability` is in this
model.

**Mapping onto our strains.** Setting the ratio between the least and the most
flagellated strain to 1.7 gives

    a = ln(1.7) / ln(4.432 / 2.085) = 0.704

The two requested duration scalings bracket that strength: `1/sqrt(N)` spans
1.46-fold across our strains, `1/N` spans 2.13-fold, and 1.7 sits between them.
Neither is excluded by the anchor, and neither is supported by it either,
because the anchor is about the probability.

**Limits, stated first.** Grognot et al. varied a second flagellar system in a
marine *Vibrio*, not the flagella count in *Salmonella*. Mapping 1.7 onto our
hook numbers is an assumption made here, not a measurement. It fixes only the
ratio between the extreme strains; the exponent form is a choice.

### Datta et al. 2025 — an absolute duration, no flagella dependence

*P. putida* in 0.25 % and 0.30 % agar. Sci Rep 15:20320,
[doi 10.1038/s41598-025-02741-1](https://doi.org/10.1038/s41598-025-02741-1),
PMID 40579453. Mean dwell times 2.07 s and 3.63 s; power-law dwell-time
distribution; mean run times 0.35 s and 0.23 s.

Caveat on verification: the PubMed Central rendering strips inline numerals, so
the 2.07 s could not be re-read from it. The value is carried from
`motility_parameter_sources.md`, section 7, which records it as read from the
source. Anyone rebuilding variant F should re-check it against the published
PDF.

Two further points from that paper bear on this model. Run lengths in the gel
were identical across wild type and both stator mutants, so the geometry, not
the swimming pattern, sets the run length. And the dwell time is power-law
distributed, whereas the model draws an exponential. An anchored mean therefore
fixes the mean and nothing else.

### Bhattacharjee and Datta 2019 — an order of magnitude only

*E. coli* in a jammed hydrogel packing. Nat Commun 10:2075,
[doi 10.1038/s41467-019-10115-1](https://doi.org/10.1038/s41467-019-10115-1),
PMID 31061418. Trapping durations 0.4 s to 40 s, power-law distributed. The
current values, 0.30 s to 1.81 s, sit at or below the low end.

### No source defines a stall probability

`stall_probability` is a per-contact-event quantity of the corrected model,
decided once per encounter with a disk. The upstream model that produced the
grid below decided it once per time step of continued overlap. Under neither
form is it an observable of any published experiment. Grognot's 1.7 constrains
the **ratio** between strains. Nothing constrains the absolute value. Variant F
therefore anchors only the duration, and says so.

---

## 3. The grid

Seven variants, agarose only, 100 seeds (1000–1099), 26 cells, 20 s,
`dt = 0.0025 s`, everything else at the adopted global-turn-angle values.

**Normalisation.** Every scaled column is renormalised so its arithmetic mean
over the three strains equals the mean of the three current values:

    x_s = x_mean * N_s^-a / mean_s(N_s^-a)

with `x_mean` = 0.16998 for the probability and 0.94892 s for the duration.
A variant therefore changes how the effect is **distributed** between strains,
not how large it is. Variant F breaks that rule on purpose, because its duration
comes from a publication rather than from the current table. `N` is the mean hook
count per cell, read from `hook_count_per_cell.csv` (PproA 2.085, WT 2.666,
PproB 4.432; 29,789 cells).

### Parameters

| variant | | PproA | WT | PproB |
| --- | --- | --- | --- | --- |
| A baseline | `p` | 0.1456 | 0.2774 | 0.0870 |
| | `t` (s) | 1.813 | 0.735 | 0.298 |
| B global, global | `p` | 0.1700 | 0.1700 | 0.1700 |
| | `t` (s) | 0.949 | 0.949 | 0.949 |
| C global `p`, `t ~ 1/N` | `p` | 0.1700 | 0.1700 | 0.1700 |
| | `t` (s) | 1.264 | 0.988 | 0.595 |
| D global `p`, `t ~ 1/sqrt(N)` | `p` | 0.1700 | 0.1700 | 0.1700 |
| | `t` (s) | 1.108 | 0.980 | 0.760 |
| E `p ~ 1/N`, `t ~ 1/N` | `p` | 0.2264 | 0.1771 | 0.1065 |
| | `t` (s) | 1.264 | 0.988 | 0.595 |
| F global `p`, literature `t` | `p` | 0.1700 | 0.1700 | 0.1700 |
| | `t` (s) | 2.070 | 2.070 | 2.070 |
| **G `p ~ N^-0.70`, global `t`** | `p` | 0.2099 | 0.1766 | 0.1235 |
| | `t` (s) | 0.949 | 0.949 | 0.949 |

**Variant G is an addition to the requested grid.** A to F all keep the
probability global or tie it to the duration. Checking the anchor showed that the
only quantitative published effect is on the probability, so none of A to F
tested what the literature supports. G does.

### Results

Mean net displacement in µm, with the 2.5th to 97.5th percentile across the 100
seeds, and the paired difference from the baseline with its bootstrap interval.

| variant | PproA | WT | PproB | PproB change vs A |
| --- | --- | --- | --- | --- |
| A baseline | 8.07 (5.86–10.90) | 18.03 (13.44–24.10) | 26.42 (19.30–34.46) | — |
| B | 8.18 (5.93–10.39) | 18.81 (13.81–23.64) | 23.24 (17.08–31.27) | −3.18 (−4.01, −2.35), −12.1 % |
| C | 7.99 (6.06–10.29) | 18.57 (13.69–24.47) | 24.37 (17.50–32.22) | −2.05 (−2.90, −1.17), −7.8 % |
| D | 8.09 (6.06–10.37) | 18.67 (13.12–24.15) | 24.09 (17.91–31.05) | −2.33 (−3.09, −1.58), −8.8 % |
| E | 7.85 (6.03–10.65) | 18.65 (13.70–23.95) | 25.68 (18.36–32.07) | −0.74 (−1.58, +0.10), −2.8 % |
| F | 7.88 (5.60–10.13) | 16.73 (12.17–21.39) | 21.05 (16.08–28.32) | −5.37 (−6.15, −4.59), −20.3 % |
| **G** | 8.17 (5.98–10.69) | 18.17 (13.70–23.70) | 24.31 (17.89–31.24) | −2.11 (−2.90, −1.32), −8.0 % |

PproA moves by at most 2.7 % in any variant and no interval excludes zero. WT
moves by at most 4.3 % except in F. The choice is a choice about PproB.

Strain ratios, with the bootstrap interval on the ratio and on the paired shift
from the baseline.

| variant | WT/PproA | shift vs A | PproB/PproA | shift vs A |
| --- | --- | --- | --- | --- |
| A baseline | 2.235 (2.149–2.324) | — | 3.274 (3.159–3.394) | — |
| B | 2.300 (2.220–2.382) | +0.066 (−0.047, +0.177) | 2.842 (2.742–2.943) | **−0.432 (−0.576, −0.289)** |
| C | 2.325 (2.235–2.418) | +0.091 (−0.026, +0.206) | 3.051 (2.941–3.167) | **−0.223 (−0.363, −0.078)** |
| D | 2.307 (2.221–2.394) | +0.072 (−0.045, +0.190) | 2.977 (2.881–3.079) | **−0.297 (−0.446, −0.151)** |
| E | 2.377 (2.292–2.466) | **+0.142 (+0.043, +0.240)** | 3.272 (3.155–3.391) | −0.002 (−0.143, +0.136) |
| F | 2.125 (2.037–2.215) | −0.110 (−0.233, +0.012) | 2.672 (2.573–2.774) | **−0.602 (−0.747, −0.454)** |
| **G** | 2.225 (2.157–2.299) | −0.010 (−0.103, +0.087) | 2.977 (2.879–3.078) | **−0.297 (−0.426, −0.172)** |

Bold shifts exclude zero. The measurement-implied band from section 1 is
**2.99 to 3.11** for PproB/PproA and **2.42 to 2.43** for WT/PproA. C, D and G
land inside or at the edge of the PproB band; A and E sit above it; B and F sit
below it.

**The strain ordering PproA < WT < PproB holds in every variant**, and in every
variant both steps are resolved: the bootstrap interval on WT − PproA and on
PproB − WT excludes zero. No variant in this grid destroys the ordering.

### Stall diagnostics — do not report these as model outputs

The grid ran under the upstream dynamics, which evaluate both columns per time
step of obstacle overlap, so **neither converges with the time step**: halving
`dt` roughly doubles the number of stall draws per contact. They are diagnostics
at `dt = 0.0025 s` and are not comparable with any published fraction of time
spent stalling. The corrected model draws once per contact event, so this
particular defect is gone from the figures; the numbers in the table below still
carry it.

| variant | occupancy A / WT / B | entries per swimming second, A / WT / B |
| --- | --- | --- |
| A baseline | 0.227 / 0.274 / 0.074 | 0.185 / 0.530 / 0.266 |
| B | 0.168 / 0.250 / 0.289 | 0.226 / 0.374 / 0.449 |
| C | 0.196 / 0.258 / 0.209 | 0.209 / 0.371 / 0.450 |
| D | 0.186 / 0.261 / 0.253 | 0.214 / 0.377 / 0.457 |
| E | 0.226 / 0.256 / 0.153 | 0.256 / 0.369 / 0.317 |
| F | 0.261 / 0.390 / 0.437 | 0.194 / 0.349 / 0.424 |
| **G** | 0.179 / 0.260 / 0.242 | 0.245 / 0.388 / 0.349 |

One point here matters for the recommendation and is easy to miss.

**A global probability does not give a global stall rate.** In the model the
contact rate rises with swimming speed, so under variant B the stall rate per
second of swimming *rises* with flagella number, 0.226 to 0.449, a factor 2.0 in
the direction opposite to the published one. Making the probability global is
therefore not the neutral choice it looks like: it builds in a speed-driven
flagella dependence of the wrong sign. Variant G halves that artefact, to a
factor 1.42.

---

## 4. Marc's question: may the stall probability differ between strains?

**Yes, and the evidence for a per-strain probability is stronger than the
evidence for a per-strain duration. But the current three numbers are not that
evidence and should not stay.**

The reasoning, in four steps.

**One. The quantity is measurable and has been measured.** Grognot et al.
measured the rate at which swimming bacteria stall in 0.25 % agar and found it
significantly lower for the richer flagellar architecture, by 1.7 ± 0.2. They
controlled the speed confound with the mean free path, so the effect is
per-encounter. `stall_probability` is a per-encounter capture chance. The
quantities line up.

**Two. There is a mechanism, and it is not the one the current table encodes.**
More flagella means a wider, more redundant bundle and more torque available to
push past a constriction, so a cell is less likely to be caught in the first
place. Grognot's own summary is "preventing trapping in pores". The escape
mechanism Marc has in mind — more flagella free a trapped cell sooner — is also
in their data, but it is the weaker effect and it is not significant at the agar
concentration that matches their 1.7.

**Three. The current values are not this effect.** 0.146, 0.277, 0.087 for
hook numbers 2.09, 2.67, 4.43 is not monotone. WT is the stickiest strain by a
factor of 1.9 over PproA and 3.2 over PproB, and no mechanism makes the
intermediate strain the stickiest. These are three unsourced numbers with no
pattern, and a reviewer who plots them against flagella number will see that in
one second.

**Four. A global probability is not the safe default it looks like.** Because
the model's contact rate scales with speed, a global probability makes the fast,
many-flagella strain stall *more often per second* than the slow one — the
opposite of the published direction. If the probability is made global, the
methods must say that the resulting stall rate still differs between strains and
does so for a geometric reason, not a biological one.

**So:** a per-strain probability is defensible if and only if it is monotone in
flagella number and its strength is tied to Grognot's 1.7. That is variant G.
The current per-strain probabilities are not defensible in any reading.

---

## 5. Recommendation

**Adopt variant G.**

    stall_probability      PproA 0.2099   WT 0.1766   PproB 0.1235   (p ∝ N^-0.704)
    stall_mean_duration_s  0.9489 in all three agarose rows

The case, on provenance first.

* The probability is the only one of the two parameters with a published,
  quantitative, flagella-resolved measurement behind it. G uses it and states the
  mapping. The current values contradict it.
* The duration's flagella dependence is not significant at the matching agar
  concentration, so a per-strain duration is not supported. One global value is
  the honest statement of what we know.
* The absolute duration stays at the current mean rather than Datta's 2.07 s.
  This is a deliberate choice, and it is unsourced: section 1 shows the measured
  `tau` already contains the mesh, so a 2.2-fold longer stall would deepen a
  double count that is already 17 % to 22 % of `D_eff`. Variant F does exactly
  that: it costs PproB 20.3 % of its displacement against the baseline, 12
  percentage points more than G. The methods must record the absolute value as
  nominal.
* G does not maximise the strain difference. It reduces `PproB/PproA` from 3.27
  to 2.98 and moves it onto the value the measurement implies (2.99 to 3.11).
  That is the model becoming more honest, not less informative.

**What adopting G would cost, stated plainly.** The simulated PproB advantage in
agarose gets smaller. PproB loses 8.0 % of its net displacement (−2.11 µm, CI
−2.90 to −1.32) and `PproB/PproA` falls by 0.30 (CI −0.43 to −0.17). `WT/PproA`
does not move (−0.010, CI −0.103 to +0.087). The ordering PproA < WT < PproB
holds and both steps stay resolved. Nothing measured changes: Figure 7 and every
agarose measurement are untouched, because this is a simulation input.

**If Marc prefers the strongest possible provenance on the duration**, variant F
is the alternative: it is the only variant whose duration comes from a
publication. It costs PproB 20.3 % of its displacement, pushes `PproB/PproA` to
2.67, below the measurement-implied band, and raises stall occupancy to 26–44 %,
which makes the double counting worse. I do not recommend it, and the reason is
section 1, not the size of the strain difference.

**If Marc prefers to change as little as possible**, variant E reproduces the
baseline `PproB/PproA` almost exactly (3.272 against 3.274) while removing the
non-monotone probabilities. But E keeps both parameters flagella-dependent, so it
claims more than the literature supports, and it leaves `PproB/PproA` above the
measurement-implied band. It is the least defensible of the reasonable options.

## 6. What the methods must say if G is adopted

* `stall_probability` scales as `N^-0.704`, normalised so the mean over the three
  strains is unchanged. The exponent is set so the ratio between the least and
  the most flagellated strain equals the 1.7 ± 0.2 stall-frequency ratio measured
  by Grognot et al. 2023 in 0.25 % agar. Name the organism, *Vibrio
  alginolyticus*, and the contrast, a second flagellar system rather than a
  flagella count. Name the mapping as an assumption.
* `stall_mean_duration_s` is one nominal value, 0.949 s, with no source. Cite
  Bhattacharjee and Datta 2019 and Datta et al. 2025 as showing that gel trapping
  happens on the seconds timescale and is power-law distributed, and state that
  the model's exponential stall with a mean below 1 s is a simplification and
  sits below the published means.
* The simulation is not an independent prediction of agarose spreading. Speed,
  motile fraction and persistence time are calibrated inputs, and the measured
  persistence time already contains the mesh. Under the corrected dynamics the
  obstacles and stalls add a further 17 % to 22 % reduction of the effective
  diffusivity on top of it.
* The model reproduces the measured liquid `D_eff` closely and the measured
  agarose `D_eff` only in part. Under the lag-corrected convention it delivers
  87 % to 90 % in liquid and 69 % to 76 % in agarose. Name the convention.
  The old explanation is retired: cells no longer spend 20 % to 40 % of their
  time in a non-swimming reorientation state, because that state no longer
  exists. Its occupancy is 0.000 in every row. The remaining agarose gap is the
  double count of the mesh described above. Source:
  `build/diagnostics/effective_diffusivity_check/effective_diffusivity_comparison.csv`.
* Do not report stall occupancy as a model result. The occupancy numbers in the
  grid of section 3 are properties of the retired dynamics and do not converge
  with the time step. The corrected model gives 0.101 to 0.135 in agarose, but
  its convergence was not tested. Treat it as a diagnostic.

## 7. Limitations

* Neither parameter becomes *sourced* by this exercise. The probability gains a
  sourced ratio between strains; its absolute value stays nominal. The duration
  stays nominal in both value and form.
* The agarose concentration of our own experiments is not recorded in the
  revision documents. Both anchors are for 0.25 % agar. If our gel differs, the
  anchors move.
* The grid pairs on the seed index. Variants B to G share the starting positions,
  the motile mask and the obstacle field with the baseline, because those draws
  precede the first stall decision. They do not share later draws.
* The intervals quantify stochastic seed variation, not biological sampling
  uncertainty.
* Nothing in `build/diagnostics/stall_parameter_comparison/` is a manuscript
  panel. No figure, panel, config, theme or palette was changed.
