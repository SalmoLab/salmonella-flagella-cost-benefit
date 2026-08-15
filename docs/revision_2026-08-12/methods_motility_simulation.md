# Draft methods paragraph — active-particle motility simulation

Status: draft for Marc, rewritten 14 August 2026 for the corrected dynamics.
Parameter sources are recorded in
[`motility_parameter_sources.md`](motility_parameter_sources.md).

---

## Draft

**Active-particle simulation of swimming behaviour.** We illustrated the measured
motility phenotypes with a two-dimensional active-particle model
(https://github.com/MPUSP/salmonella-motility-simulation, commit `96ca0e74`,
MIT licence). We corrected three defects in the published dynamics before we used
it; the corrected model is in `models/motility_simulation/corrected/` and the
published code is kept unedited beside it as provenance. Each cell occupies one of
three states: run, stall and permanently non-motile. A running cell moves at a
fixed speed while its heading performs a random walk. It reorients at a fixed
rate, turning by a random angle without interrupting its motion. In the
agarose-like condition the field also contains non-overlapping circular obstacles,
and a cell that meets an obstacle can stall for a random time before it escapes.

**Correction 1: reorientation is instantaneous.** The published loop parked a
reorienting cell in a fourth, non-advancing state for a fixed duration. That is not
the model the parameters are fitted to. The persistence relation used by the
calibration,

    tau = 1 / (D_theta + lambda * (1 - exp(-sigma^2 / 2)))

carries no duration term. It describes a walker that turns instantaneously and
swims the whole time. Fitting through one model and simulating another cost a
large part of the spreading. We therefore apply the heading kick at the transition
and let the cell keep swimming. The reorientation duration is then not a parameter
of the model at all, so we removed it rather than set it to zero, and it does not
appear in Supplementary Table X. Its published value, 0.05 s, equalled the
published time step exactly, which is evidence that it was never a measured
duration. We did not substitute the measured *E. coli* tumble duration of 0.19 s
(Taute et al., 2015): a duration does not enter the persistence relation, so the
calibration cannot absorb it, and at our fitted rates it would put cells in a
non-swimming state 49 % to 71 % of the time. A model with a real tumble duration
needs the persistence relation refitted with a duration term. That is a modelling
change, not a parameter change, and we did not make it.

**Correction 2: the stall test fires once per contact event.** The published loop
drew against the stall probability at every time step in which a proposed step
overlapped an obstacle. A sliding or stalled cell was therefore re-drawn on every
step, so the stall occupancy grew as the step shrank and no obstacle observable
converged. We draw once, on the step where a cell first overlaps a disk it was not
already touching. A cell counts as still touching that disk until its centre passes
0.1 um beyond the surface, which stops a cell parked on the surface from leaving
and re-entering contact on almost every step. The stall probability then means the
chance that one encounter ends in a stall. That is the same per-contact quantity
Grognot et al. (2023) measured, so the parameter now means what its literature
anchor means.

**Correction 3: the obstacle count scales with the box area.** The published field
of 58 disks is tuned to the published 148 x 96 um box. Enlarging the box without
scaling the count would dilute the mesh and raise every agarose observable. We
scale the count with the box area and record the realised obstacle area fraction
for every run as the check that the mesh density held.

Two parameters come directly from our measurements: the run speed and the motile
fraction, both taken per strain and per medium from the paired experimental units
in Figure 7. Two further parameters — the heading-diffusion coefficient and the
reorientation rate — set the model's directional persistence. The delivered values
did not reproduce our measured persistence time, so we scaled both by the single
factor that makes the model persistence time equal the measured one, keeping their
delivered ratio. In the relation above tau depends on the two rates only through
their sum, so one factor closes the gap exactly. We report these two parameters as
fitted quantities, not as measured ones. The fitted heading-diffusion coefficient
is 4.2 to 8.6 rad^2 s^-1. This is 70 to 150 times the rotational diffusion measured
for a swimming *Escherichia coli* cell body, 0.057 rad^2 s^-1 (Drescher et al.,
2011, PNAS 108:10940, doi:10.1073/pnas.1019079108). The parameter is therefore an
effective directional-decorrelation rate that absorbs reorientation mechanisms the
model does not resolve. It is not the rotational diffusion of the cell body, and we
do not interpret it as such.

The reorientation angle spread comes from the literature. We set one value for all
six strain-by-medium rows, sigma = 1.247 rad (71.4 degrees), so that the mean turn
magnitude sigma * sqrt(2 / pi) equals the population mean turn angle of 57 degrees
measured over 8058 turns of *E. coli* AW405 (Taute et al., 2015, Nat Commun 6:8776,
doi:10.1038/ncomms9776). Two limits apply. Taute et al. tracked in three dimensions
and in *E. coli*; our model is two-dimensional and our strains are
*S.* Typhimurium, so the mapping matches the mean turn magnitude and nothing else.
A zero-mean Gaussian turn also cannot reproduce the measured turn-angle shape,
which is broad and skewed toward the forward hemisphere. A heading is periodic, so
1.2 % of draws fold back past +/-pi and the realised mean turn magnitude is
56.5 degrees rather than 57.0 degrees. The persistence calibration ran with this
value already in place, so both rates and the turn width close on the same measured
persistence time.

The passive translational diffusion coefficient, 0.35 um^2 s^-1, is a nominal value
of the published code. It agrees within 3 % with the Stokes-Einstein value for a
2.0 x 0.8 um cell at 20 °C. We state it in Supplementary Table X.

The two stall parameters act only in the agarose-like condition. The stall
probability is zero in the liquid condition, so the stall duration never fires
there. The stall probability is the chance that one contact with an obstacle ends
in a pause rather than a tangential slide. No published measurement gives its
absolute value, so we report it as nominal in size. Its ratio between strains is
taken from the literature. Grognot et al. (2023, PNAS 120:e2301873120,
doi:10.1073/pnas.2301873120) report that lateral flagella lower the chance of
stalling by a factor 1.7 +/- 0.2 in 0.25 % agar, and they control the speed
confound by comparing the mean free path at matched swim-phase speed, so the factor
is a per-contact quantity. Our stall probability is now the same per-contact
quantity. We let it fall with the mean flagella number per cell as N^-0.704,
normalised so its mean over the three strains equals the mean of the delivered
values, and we set the exponent so the ratio between the least and the most
flagellated strain equals 1.7. This gives 0.210, 0.177 and 0.123 for PproA, WT and
PproB. Two limits apply. Grognot et al. varied a second flagellar system in *Vibrio
alginolyticus*, not the flagella count in *Salmonella*, so mapping the factor onto
our flagella numbers is an assumption. The mapping fixes the ratio between the
extreme strains; the power-law form is our choice.

The mean stall duration is one nominal value, 0.949 s, in all three strains. We did
not give it a flagella dependence, because the evidence does not support one:
Grognot et al. found the difference in stall duration significant only at 0.16 %
agar and not at the 0.25 % that matches our anchors. Reported trapping times in
hydrogels and soft agar span 0.4 to 40 s (Bhattacharjee and Datta, 2019) and average
2.1 to 3.6 s (Datta et al., 2025), so our value lies below the published means, and
those distributions are power-law while the model draws an exponential. We report
the absolute duration as nominal.

Four further constants scale the random part of the motion, and none of them has a
source: the translational noise of a running cell and of a stalled cell, at 0.12 and
0.20 of the passive diffusion coefficient, the fraction of a tangential step kept
during a slide, 0.28, and the rotational diffusion of a stalled cell, at 1.8 times
the running value. We list all four in Supplementary Table X as nominal values. They
also order the translational noise the wrong way round, because a non-motile cell
diffuses at the full passive rate while a running cell diffuses at 0.12 of it. We
measured the size of that defect rather than assume it. Against a physically ordered
alternative, in which every state diffuses at the full passive rate, the net
displacement we report changes by at most 3.5 % and no agarose interval excludes
zero, while the effective diffusivity in agarose changes by up to 6.2 %
(95 % CI -8.0 % to -4.5 %). We therefore keep the published values and declare them,
and we state the agarose sensitivity as a limitation below.

**Domain.** The quantitative panels, Figure 5D and 5E, run in a box of
1776 x 1152 um, enlarged twelvefold in each linear direction from the published
domain, with 8352 obstacle disks in the agarose-like condition. The published
148 x 96 um box has reflecting walls, and a wall turns a cell back, so it shortens a
fast strain more than a slow one and compresses the strain ratios. We measured that
compression directly: the published box lowers the PproB-to-PproA net-displacement
ratio by 12.9 % (95 % CI 8.4 % to 17.2 %) in the agarose-like medium and by 17.1 %
(14.2 % to 20.0 %) in liquid, and the WT-to-PproA ratio by 10.9 % and 9.7 %. A
ladder of box sizes puts the ratios on a plateau: every ratio moves by less than
0.6 % between an eightfold and a twelvefold box. The realised obstacle area fraction
is 0.185 in the published box and 0.187 in the enlarged one, so the mesh keeps its
density. Supplementary Figure 4 keeps the published 148 x 96 um box with its 58
disks, because a small field is what makes individual tracks legible. It shows a
spatial pattern and reports no number.

**Integration.** We integrated the model with a time step of 0.0025 s, over 100
seeds per strain and medium and 26 cells per seed. A convergence test accepts every
step whose group mean net displacement stays within 5 % of the mean of the two
finest steps tested, 0.00125 s and 0.000625 s. Under the corrected dynamics every
step we tested passes, from 0.000625 s to 0.05 s: the largest deviation over the six
groups is 2.0 % at the step we used and 4.0 % at the coarsest. The step dependence
that the published stall rule created is gone, because the stall draw now happens
once per contact event. The agarose PproB group mean moves by 0.3 % between the two
finest steps, and the simulated PproB-to-PproA ratio in agarose stays between 3.29
and 3.50 across the whole ladder with no trend in the step. We do not report contour
path length, which does not converge at all, because a trajectory with a diffusive
component has an infinite arc length in the continuum limit.

**What the simulation shows, and what it does not.** The simulation illustrates the
measured phenotypes. It does not predict them. Run speed and motile fraction are
inputs, and directional persistence is fitted to our measurement. The model output
we report is the net displacement.

The corrected dynamics reproduce most of the measured spreading. The model delivers
87 % to 90 % of the measured effective diffusivity in liquid and 69 % to 76 % in the
agarose-like medium, against 60 % to 61 % and 37 % to 39 % before the corrections.
These ratios compare the simulated value with the lag-corrected measured value.
Compared with the diffusivity the calibration itself implies, v^2 tau / 2, the
corrected liquid runs reach 98 % to 100 %. In liquid the simulation therefore now
matches the calibration it was fitted through. Motile cells swim 100 % of the time
in liquid and 86 % to 90 % of the time in agarose.

Two limits follow, and we state both. First, the agarose condition counts the mesh
twice. We derive the measured agarose persistence time as tau = 2 D_eff / v^2 from
the measured agarose diffusivity and speed, so it already contains the mesh. The
model then adds obstacles and stalls on top of that calibration, and those remove a
further 17 % to 22 % of the effective diffusivity. This double count is why agarose
stays at 69 % to 76 % while liquid reaches 87 % to 90 %. The agarose simulation is an
illustration of the measurement, not an independent prediction of spreading in a
gel. Second, the agarose effective diffusivity is sensitive to the undeclared noise
constants described above, by up to 6.2 %. We report the agarose numbers with both
limits stated.

The measured median speed is the model's run-phase speed input. A simulated cell
now advances whenever it runs and turns without stopping, so its whole-track speed
is below the run speed only where obstacles and stalls slow it.

---

## Notes for Marc, not for the manuscript

**Why this wording.** The initial version of the simulation was written with a large
language model. The turning parameters therefore had no source: they were neither
measured nor taken from the literature. Three facts showed this. The values
clustered by medium, not by strain. The synthetic `WT_slow` rows carried turning
values byte-identical to the WT rows in both media. Our measurement tables contain
no column that could have supplied them.

**The turn angle is now sourced, as of 13 August 2026.** The six sourceless
per-strain widths are replaced by one cited value. The worst of the six gave PproB
less than half the turn width of the other strains, which invented a behavioural
difference inside a figure about flagella number and persistence. The substitution
moved the simulated net displacement by 0.8 % to 7.0 % and left every strain ratio
unchanged within the seed noise, so no conclusion depends on it. See
`turn_angle_model_comparison.md`.

**Three dynamics defects are fixed, as of 14 August 2026.** Reorientation is
instantaneous, the stall test fires once per contact event, and the obstacle count
scales with the box area. The first two changed the numbers: the effective
diffusivity rose from 60 % to 87–90 % of the measured value in liquid and from 37 %
to 69–76 % in agarose, and the time-step dependence of the agarose observables
disappeared. Do not describe the model as having a reorientation duration. That
parameter is removed, not zeroed.

**The four noise constants are declared but not changed.** They have no source and
they invert the translational noise ordering. We measured the effect before deciding:
it is negligible for net displacement and material for the agarose effective
diffusivity. Changing them would alter a calibrated model on no evidence, because the
ordered alternative has no source either. See section 8 of
`motility_parameter_sources.md`.

**Open question for Michael.** He does not know where the two turning parameters came
from either. The paragraph does not need his answer, because it reports them as
fitted. Ask anyway, in case an older data source exists that we have not seen.

**Supplementary Table X** lists the eight per-strain parameters and the four global
noise constants, with a source column carrying the five states.
