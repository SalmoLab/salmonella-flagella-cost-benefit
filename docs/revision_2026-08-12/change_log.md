# Coauthor-comment change log

The quoted headings below preserve the actionable comment text from the frozen
12 August revision brief. The implementation outcome is stated immediately
below each heading.

## “Remove significance stars from all figures.”

Accepted. Stars and star-code keys are prohibited. Genuine comparisons use an
effect size, confidence interval and exact P value in registered statistics.
Jahn's dissent—that stars would be acceptable if their thresholds were defined—
is retained here.

## “Use bars only where a single model-predicted value is compared with a single measured mean.”

Accepted, and applied more strictly than the comment asked. The
experiment-versus-model penalty panel, Figure 3E, draws no bar at all. It plots
one point per experiment day in the colour and shape of its strain, a black
diamond with 95% confidence whiskers for the experiment mean, and a filled
square for the single model value at 5% flagellar mass fraction. No panel draws
a bar for a mean. Two other bar geometries remain, and neither is a summary bar:
Figure 4C, 4D and 4E stack bars to show a composition, and Figure 7D draws a
horizontal bar from the reference ratio of 1 to the estimate, so bar length
reads as effect size on the log axis. Replicate panels expose their independent
observations. Dufour's preference for complete geometric consistency is recorded
as dissent.

## “Panel D must be drawn in the same visual style as panels C and H.”

Accepted. The three count-per-cell panels use the shared count-distribution
geometry and ordered condition colors.

## “Define the central dark-grey lines … or remove them.”

Accepted in part. The violins of Figure 2C and Figure 3C are drawn with
`inner=None`, so the box and the quartile lines seaborn draws inside a violin
are gone. One vertical line remains inside each violin: the 95% confidence
whisker of the black summary diamond, which is drawn over the violin at the
group centre. It is kept because it is the inferential mark of the panel, the
interval of the independent-replicate means, and the panel key names it
"Mean ± 95% CI". The undefined lines were removed; the defined one was kept and
named.

## “Panel A: define the lines connecting the dots, or remove them.”

Accepted by removal because experimental days are independent, not a time or
matched-dose trajectory.

## “Add the single-cell wild-type measurement if the data exist.”

Not implemented because TH9677/WT(S171) is absent from the mother-machine data.
Ppro1 is the explicitly labelled within-replicate reference. No other strain is
substituted for WT(S171).

## “Clarify the heterogeneity at 0.5 ng/mL AnTc.”

Not testable: no corresponding single-cell Ptet dataset exists. Plate-reader
wells and hook-count microscopy cannot establish single-cell bimodality.

## “Current panel F … does not track current panel E — reconcile or explain.”

Explained as an unresolved assay/context discrepancy. Population and
mother-machine experiments use different contexts, and the single-cell series
has only two independent repeats.

## “Protein labels are unreadable.”

Accepted. Labels require a predeclared 15% contribution threshold within the
displayed sector subtotal, FliC is always retained, and labels use external
repelled placement with leader lines. Kept and dropped labels are source data.

## “Sectors Tra and AaB also seem to change.”

Confirmed by replicate-aware analysis. The analysis report replaces the claim
that other sectors vary only minimally with the measured sector-specific result.

## “Overlay model predictions on the experimental data.”

Accepted. Both raw and change-from-reference overlays are generated. The latter
is the main panel because it exposes agreement and disagreement in trends without
conflating model zero with experimental ΔflhDC.

## “Define the lines and the grey shaded area.”

Accepted. The gradient panel explicitly defines travelled-distance trajectories,
endpoints and the fixed glucose profile. Glucose is labelled in mM.

## “The non-flagellated / non-motile reference case is not plottable.”

**Now plotted, on 14 August 2026.** The case became plottable when the solver
route did. GEKKO with `remote=True` sends the model to the public APMonitor
server, which solves it with IPOPT. On that route the zero-allocation case
solves: growth rate 1.0634 1/h at 8 h, `alpha_Fla` exactly 0, distance
unchanged at 8500 µm because the cell never reaches the substrate. The same
route reproduces the delivered 1–5% tables to 1e-9 relative error, so it is the
collaborator's solver and not a substitute.

Figure 5B now draws that trajectory as a dashed grey reference beside the
0.5–5% family. Every motile allocation reaches 1.66–1.77 1/h by 8 h, a gain of
56% to 66% over the non-motile cell, and 8.3-fold to 35.5-fold its compounded
biomass. The numbers are in
`data/source_data/figure_05_revision/B/non_motile_gain.csv`.

**The interval between 0% and 1% is recorded, not drawn.** A first sweep left
two of 21 steps unsolved and produced non-monotonic growth rates. A warm-start
continuation with a multi-start then solved all 21 steps: each allocation was
attempted from the cold guess, from the accepted neighbour above and from the
accepted neighbour below, and the best solver objective was kept. The failures
disappeared. The scatter did not. Three growth-rate reversals remain, and each
comes with a distance reversal in which the cell with more flagella ends
farther from the source. Across the three initial guesses the solved endpoint
of one allocation spreads by up to 27.6%. That is local-optimum scatter in a
non-convex problem, not biology, so no interior curve is claimed and nothing is
smoothed or interpolated across the gap.

The 0% point is the exception, and its status is different in kind. With
`alpha_Fla` fixed at 0 the cell cannot swim, the substrate stays at its initial
0.0911 mM, and the dynamic problem collapses onto a fixed-substrate steady
state. The independent steady-state solve at 0% gives 1.0627 1/h against the
dynamic plateau of 1.0634 1/h, a gap of 0.069%. The baseline therefore does not
depend on which local optimum the solver found.

Records: `build/statistics/Figure_5/A3/low_allocation_continuation_status.csv`,
`low_allocation_continuation_attempts.csv`, and the accepted trajectories under
`data/processed/figure_05_revision/A3_trajectories/`. The harness is
`models/cell_economy/low_allocation_sweep.py --continuation`.

## “Add the missing scale bar to the example images.”

Blocked. A scale bar is not inferred from cell size. It requires calibrated raw
images or exact pixel calibration plus the intended physical length.

## “Replace the pairwise enrichment maps … Test both and show them.”

Accepted, and both designs were built as finished panels at the final
55 x 54 mm size and compared side by side. The paired-unit design is canonical
as Figure 7A-C: it plots the inferential unit, shows the within-experiment
pairing, and states the effect size with its confidence interval. The contours
are retained as Supplementary Figure 5, at full width where they are legible,
because they show the joint speed/diffusivity distribution that the paired
panels cannot.

The contours are supplementary for a scientific reason as well as a visual one.
They pool 7,213-13,874 trajectories, while every test uses the paired experiment
as its unit, so contour separation invites an effect-size reading that the
statistics do not support. The Supplementary Figure 5 caption states that
pooling, and each panel carries the paired-experiment count and a centroid
marker with its 95% confidence whiskers, so the inferential mark is visible
inside the pooled layer.

## “Remove the broken y-axis. Add a horizontal reference line at D_eff = 1.”

Accepted. The revised panels use a continuous log10 effective-diffusivity axis
and a reference at zero.

## “Diffusion is the product of speed and directional persistence.”

Accepted with the exact relation used by the code: `D_eff = v²τ/2`. The revised
figure treats τ as a derived persistence-equivalent timescale, not independent
evidence, and includes an explicit paired-unit decomposition.

## “Flagella numbers can affect chemotaxis.”

Analyzed and reported only, as authorized. The four available chemotaxis proteins
are compared with structural apparatus proteins, but no functional chemotaxis
conclusion is drawn and no new figure claim is added.

## Decisions taken without a coauthor comment

### The old Supplementary Figure 3 was withdrawn

The July Supplementary Figure 3 duplicated the lower half of the current
Figure 4F: it read the same input file and drew the same association. It was
withdrawn on 12 August 2026 and the later supplementary figures moved up one
number to close the gap. Until now the decision was recorded only as a note in
`config/panels.csv` and a comment in
`analyses/collaborator_science/build_panels.py`. The withdrawn effective-
diffusivity row of the current Supplementary Figure 3 was dropped for the same
reason: it repeated Figure 7A-C from the same input file with a different
within-unit summary.

### Supplementary Figure 3 now follows Figure 7A-C

The 14 August version pooled both media on one strain tick and printed the
medium comparison as three lines of text in the panel corner:

```
paired-unit ratio PproA/WT, 95 % CI
agarose 0.71 (0.67, 0.76), 18 units
liquid  0.67 (0.59, 0.75), 16 units
```

The comparison a reader wants — how liquid differs from agarose — was therefore
text, not a graphic. Two media on one tick also made the joining lines cross,
and the dashed liquid violin printed over the filled agarose violin.

The panels now follow Figure 7A-C. One panel still holds one metric and one
strain pair. Inside the panel the two media stand side by side as two groups of
paired violins, separated by a gap, exactly as Figure 7A-C separates them. Each
group carries its own header: the medium and its fill convention, the paired
estimate, the 95 % interval and the unit count.

**The figure fell from 190 mm to 166 mm.** What the estimate divides is now
stated in the legend and in the new `contrast` column of every effect table,
which is how Figure 7A-C already handles the same question: "What the D ratio
divides is stated in the figure legend." Printing that wording under every panel
cost 8 mm of panel height nine times over. The panel box went from 55 x 56 mm to
55 x 48 mm and the plotted area kept 29.6 mm, the row height of Figure 7A-C.
BLOCKING-5 of the compliance check listed Supplementary Figure 3 as over the
maximum height for a caption under 300 words, about 185 mm. It no longer is.

Five further changes come with the restyle.

- **The three panels of a metric row share one y range.** Figure 7A-C pins one
  range across its three panels for the same reason: three different scales in
  one row would be read as one. The cost is panel H, whose data occupy the upper
  half of the shared persistence axis.
- **A ratio metric is drawn as log10 on a linear axis**, and the ticks print the
  original unit. A matplotlib log axis estimates the violin density in the
  original unit and then stretches it, which misdraws the distribution. This is
  the geometry Figure 7A-C uses.
- **Every group carries the summary diamond of Figures 4, 5 and 6.** The diamond
  sits at the group mean of the plotted quantity. The second strain's diamond
  carries the paired 95 % interval, anchored at the first strain's mean. Because
  the plotted quantity is log10 for a ratio metric and the raw value for the
  bounded fraction, that anchored estimate lands on the second strain's own mean
  exactly; the builder asserts the residual is below 1e-12.
- **The strain colours now come from `get_strain_style`**, the same three entries
  Figure 7A-C reads. The three colours are unchanged: WT `#7F7F7F`, PproA
  `#FC9272`, PproB `#DE2D26`.

No number changed. The paired estimator, the bootstrap seed and the 10 000
iterations are untouched, and every estimate, bound and count in
`data/source_data/supplementary_04/*_paired_effect.csv` is the value the earlier
table carried. The table gained one column, `contrast`, which names what the
estimate divides or subtracts. The same table is now also written to
`build/statistics/Supplementary_Figure_3/<panel>/S3_<panel>_paired_effect_statistics.csv`
and registered as `partial_statistics`, so every number the withdrawn corner
block printed is machine-readable where a reader of Figure 7 looks for it.

The panel-letter guard changed with the layout. `PANEL_LETTER_CLEARANCE_MM`
stays at 2.8 mm, above the 2.0456 mm the assembler's letter reaches into the
panel, and the builder now measures the rendered extent of every text it draws
and fails the build if one of them reaches into the letter band. The test that
pinned the old corner block reads the same band instead of one named text, and a
second test holds every number of the statistics table on the panel.

On-page type is 6.5 pt at an assembly scale of 1.0, above the 6 pt floor.

### A separator now divides the stacked sector segments

The eight-sector palette is not safe for red-green colour blindness where two
segments touch. Under the Machado, Oliveira and Fernandes (2009) deuteranomaly
simulation at severity 100, the CAM02-UCS distance between three sector pairs
collapses:

- Lpb `#1B9E77` against Fla `#E7298A`: 61.7 in normal vision, 3.7 under
  deuteranomaly.
- Rib `#A6761D` against Etc `#66A61E`: 25.9 in normal vision, 6.3 under
  deuteranomaly.
- Etc `#66A61E` against Tra `#DF9359`: 33.9 in normal vision, 9.7 under
  deuteranomaly.

A distance of 3.7 is below the discrimination threshold. Lpb and Fla are
neighbours in the sector stack, and flagellar allocation is the central variable
of the manuscript. A deuteranope could not see where one segment ended and the
next began.

The palette did not change. Michael Jahn asked to keep the fixed eight-sector
palette, and the same sector colours appear in the collaborator's own figures.
Figure 4C, 4D and 4E now draw a thin white line between stacked segments
instead. The background is at least CAM02-UCS 24.4 from every one of the eight
sectors under the same simulation, so one separator repairs all three pairs at
once and no colour moves.

`SEGMENT_SEPARATOR_COLOR` and `SEGMENT_SEPARATOR_WIDTH` in
`src/flagella_repro/theme.py` hold the one definition. The width is 0.3 pt,
which is 0.106 mm on the page because every panel renders at its assembly box.
That is above the 0.1 mm minimum stroke that print production holds, and below
the width at which the line reads as a data element. Two earlier sites
disagreed: Figure 4C drew 0.18 pt in the palette background colour, and the
superseded collaborator builder drew 0.3 pt in literal white. Both now read the
shared constants.

Three segments do not survive the separator. The flagellar sector of the three
lowest strains in Figure 4D is 0.075% of protein mass for Ppro1-flhDC, 0.095%
for ΔflhDC and 0.125% for PproA-flhDC. Those segments are 0.12, 0.15 and 0.20 pt
tall. Each is thinner than the 0.3 pt separator, so the separator overdraws it.
None of the three was legible before: 0.2 pt is 0.07 mm, below what print
resolves, and they were visible only when the PDF was magnified on screen. The
measured values stay in Source Data, and Figure 4E draws nothing at all for the
flagella-free model point, so the two panels agree on what a near-zero flagellar
sector looks like.

Every other segment stays visible. The flagellar sector of WT is 0.57 pt and
survives as a thin line. The thinnest sector that is drawn at every strain is
Tra at about 1.5 pt, which keeps about 1.2 pt of colour.

### The turn angle of the motility simulation is now one cited value

Adopted 13 August 2026. The active-particle simulation gave every
phenotype-by-medium row its own reorientation angle spread `turn_angle_sd_rad`:
0.633, 0.646, 0.301 rad in liquid and 0.804, 0.746, 0.328 rad in agarose. None
of the six was measured and none came from a publication. The first version of
the simulator was written by a language model. Worse, PproB carried less than
half the turn width of the other two strains, and no measurement of ours
distinguishes PproB that way. That invented split sat inside a figure about
flagella number and directional persistence.

All six are replaced by one value, σ = 1.2468 rad (71.4°), for every row. It is
set so the mean turn magnitude `σ * sqrt(2/π)` equals the population mean turn
angle of 57° that Taute et al. measured over 8058 turns of *E. coli* AW405
(2015, Nat Commun 6:8776, doi:10.1038/ncomms9776, PMID 26522289). The value is
computed from the published angle at build time; it is not written into any
table by hand.

The reason is provenance, not fit. Six numbers with no source become one number
with a citation. Nothing else changes in how the model is calibrated: the
persistence relation is untouched, and `rotational_diffusion_rad2_s` and
`reorientation_rate_s` still keep their delivered ratio and are still scaled by
the one factor that makes the model persistence time equal the measured one.
Because a wider turn does more work per reorientation, that factor is smaller,
so both rates fall: `rotational_diffusion_rad2_s` from 6.11–11.00 to
4.23–8.56 rad² s⁻¹ and `reorientation_rate_s` from 7.97–16.90 to
5.09–13.15 s⁻¹. Both tables close on the same measured persistence time, so the
derived τ is unchanged.

The simulated group mean net displacement of Figure 5D and 5E, in µm:

| Group | before | after | change |
| --- | --- | --- | --- |
| PproA liquid | 18.03 | 18.72 | +0.69 (+3.8 %) |
| WT liquid | 29.58 | 31.65 | +2.07 (+7.0 %) |
| PproB liquid | 36.79 | 38.67 | +1.87 (+5.1 %) |
| PproA agarose | 7.75 | 8.07 | +0.32 (+4.2 %) |
| WT agarose | 17.88 | 18.03 | +0.15 (+0.8 %) |
| PproB agarose | 24.80 | 26.42 | +1.62 (+6.5 %) |

Cells spend less time in the reorient state, so they cover slightly more ground.
The rise is 0.8 % to 7.0 %.

**No strain ratio moves.** A paired comparison over the same 100 seeds, with a
bootstrap over seeds, puts zero inside the 95 % interval of every ratio shift:
WT/PproA liquid +0.050 [−0.032, +0.130], PproB/PproA liquid +0.025
[−0.067, +0.115], WT/PproA agarose −0.073 [−0.186, +0.040], PproB/PproA agarose
+0.072 [−0.075, +0.222]. The ordering PproA < WT < PproB holds in both media
under both tables. The invented per-strain turn angle was not driving the
reported strain differences, so the choice could be made on provenance alone.

What was rebuilt: Figure 5D and 5E, Supplementary Figure 4A–F, and
Supplementary Table X, where the `turn_angle_sd_rad` row changes from six values
with source class "Nominal" to one value with source class "Literature" and the
Taute citation. Figures 1, 2, 3, 4, 6 and 7 and Supplementary Figures 1, 2, 3
and 5 are untouched.

What the change does not fix, stated so it is not oversold: `stall_probability`
and `stall_mean_duration_s` still have no source; `rotational_diffusion_rad2_s`
is still a fitted lumped rate and must not be called rotational diffusion; and a
Gaussian turn still cannot reproduce the measured forward-skewed turn-angle
shape. Only the mean magnitude is matched. `reorientation_duration_s` also still
lacked a source on 13 August. The dynamics correction of 14 August retired it:
the parameter is removed from `MotilityParameters`, not set to zero. See "The
motility dynamics were corrected in three ways" below.
The evidence for the decision is in
[`turn_angle_model_comparison.md`](turn_angle_model_comparison.md).

### The time-step convergence check was repeated on the adopted table

The check that fixes the integration step reads the parameter table, so it was
rerun. `analyses/figure_05_revision/timestep_convergence.py` now reads the
adopted table too. The rerun changes what the check reports, and the reported
wording had to change with it.

The rule is unchanged: accept every step whose group mean net displacement stays
within 5 % of the mean of the two finest steps tested, 0.00125 s and 0.000625 s.
Under the previous table the largest accepted step was 0.0025 s, because 0.005 s
missed the tolerance in one group of six, liquid WT, by 0.2 percentage points.
Under the adopted table every group passes at 0.005 s, at a worst deviation of
4.7 %, so 0.005 s is now the largest accepted step. The reason is mechanical: the
adopted table lowers both reorientation rates, so the per-step turn probability
falls and a coarser step resolves the same trajectory.

**The panels keep dt = 0.0025 s.** It passes at a worst group deviation of 3.3 %,
a finer step is the conservative choice, and keeping it makes the panels
comparable across the parameter change. The sentence that called 0.0025 s "the
largest step tested that holds every group within 5 %" was true under the
previous table and is not true under this one. It is replaced everywhere by the
accepted-step wording above: in the Figure 5 legend, the methods draft,
`analyses/figure_05_revision/README.md`, and the panel provenance of Figure 5D,
5E and Supplementary Figure 4A–F.

Contour path length still does not converge. For WT in the agarose-like medium
the simulated mean path length rises from 163 µm at dt = 0.05 s to 573 µm at
dt = 0.000625 s and is still rising, so net displacement remains the reported
observable.

### The two stall parameters now follow the only published measurement

Adopted on 14 August 2026. `stall_probability` and `stall_mean_duration_s` are
the last two parameters of the motility simulation that had no source. The
delivered table put the flagella dependence in the **duration** (PproA 1.813 s,
WT 0.735 s, PproB 0.298 s) and gave the **probability** three per-strain values
that are not monotone in flagella number (PproA 0.146, WT 0.277, PproB 0.087).
No mechanism makes the intermediate strain the stickiest, and neither set had a
source.

The literature says the opposite of what the delivered table encoded. Grognot et
al. 2023 (PNAS 120:e2301873120, PMID 37579142) measured a flagella effect on the
stall **frequency** and quantified it, 1.7 ± 0.2 in 0.25 % agar, with the speed
confound controlled through the mean free path. They found the effect on stall
**duration** significant only at 0.16 % agar and **not** at the 0.25 % that
matches our condition.

The adopted table therefore lets the probability fall with the mean hook number
per cell as `p ∝ N^-0.704`, normalised so its mean over the three strains is
unchanged (PproA 0.2099, WT 0.1766, PproB 0.1235), and makes the duration one
global value, 0.9489 s. The exponent is set so the ratio between the least and
the most flagellated strain equals the published 1.7. Liquid rows keep
`stall_probability` 0 and are unaffected. Evidence and the full seven-variant
comparison: [`stall_parameter_comparison.md`](stall_parameter_comparison.md).

**One table now, not two.** The turn-angle decision and the stall decision are
combined in a single canonical file,
`data/processed/motility_adopted_parameters/motility_summary_parameters_adopted.csv`,
derived at build time by
`analyses/motility_adopted_parameters/derive_adopted_parameters.py` and reached
through one accessor, `adopted_parameter_table_path()`. Figure 5D, Figure 5E,
Supplementary Figure 4, the time-step convergence ladder and Supplementary
Table X all call it. No manuscript path reads the turn-angle-only table any
more.

**What moved.** Liquid is untouched: the stall probability is zero there, so
Figure 5D is byte-identical in its numbers. Agarose:

| group | before | after | change |
| --- | --- | --- | --- |
| PproA agarose | 8.07 (5.86–10.90) | 8.17 (5.98–10.69) | +0.10 (−0.14, +0.33), +1.2 % |
| WT agarose | 18.03 (13.44–24.10) | 18.17 (13.70–23.70) | +0.14 (−0.44, +0.69), +0.8 % |
| PproB agarose | 26.42 (19.30–34.46) | 24.31 (17.89–31.24) | −2.11 (−2.92, −1.31), −8.0 % |

Values are the mean of 100 seed means in µm, with the 2.5th–97.5th seed
percentiles; the change carries a paired bootstrap interval over the seeds.

| ratio | before | after | shift |
| --- | --- | --- | --- |
| WT/PproA agarose | 2.235 (2.150–2.324) | 2.225 (2.158–2.297) | −0.009 (−0.107, +0.085) |
| PproB/PproA agarose | 3.274 (3.160–3.391) | 2.977 (2.879–3.078) | **−0.297 (−0.426, −0.174)** |
| WT/PproA liquid | 1.690 (1.622–1.762) | 1.690 (1.622–1.762) | 0.000 |
| PproB/PproA liquid | 2.065 (1.989–2.147) | 2.065 (1.989–2.147) | 0.000 |

**This weakens the simulated agarose result, and that is the honest direction.**
PproB loses 8.0 % of its simulated net displacement and `PproB/PproA` falls by
0.30. The measurement-implied band for that ratio is 2.99 to 3.11, so the
adopted value moves onto the measurement instead of above it. The ordering
PproA < WT < PproB holds and both steps stay resolved. Nothing measured changes:
Figure 7 and every agarose measurement are untouched, because this is a
simulation input.

**What the change does not fix.** The absolute stall probability still has no
source; only its ratio between strains does. The absolute stall duration still
has no source.

Two further statements stood here on 14 August and are now false. The dynamics
correction of the same day replaces both. `reorientation_duration_s` is not
0.05 s: the parameter is removed from the model. The model does not reproduce
only 49 % to 58 % of the measured effective diffusivity: under the lag-corrected
convention it now reaches 87 % to 90 % of the measured value in liquid and 69 %
to 76 % in agarose. The remaining agarose gap is a double count of the mesh, not
a reorientation duty cycle. See "The motility dynamics were corrected in three
ways" below.

### The time-step ladder was rerun and now accepts a finer step

The convergence check reads the parameter table, so it was rerun on the adopted
table with the same rule: accept every step whose group mean net displacement
stays within 5 % of the mean of the two finest steps tested, 0.00125 s and
0.000625 s.

**The largest accepted step is now 0.00125 s.** Under the turn-angle-only table
it was 0.005 s. The panels keep dt = 0.0025 s. At that step five of the six
strain-by-medium groups stay within 3.0 % of the refined reference and the
sixth, PproB in agarose, deviates by 5.0 %, so it just misses the tolerance.

The cause is the stall rule, and it must be stated. The model tests
`stall_probability` at every time step in which a proposed step overlaps an
obstacle, so a finer step makes more stall draws per contact. The adopted table
raises the PproB stall probability from 0.087 to 0.1235, which makes agarose net
displacement more step-dependent than before. Between the two finest steps the
PproB agarose group mean still moves by 6.4 %, and the agarose `PproB/PproA`
ratio moves with the step: 3.14 at 0.005 s, 2.98 at the panel step, 2.93 at
0.00125 s and 2.77 at 0.000625 s. Liquid net displacement is converged. The
agarose ratios are therefore reported as values at a stated step, and the legend,
the methods, `analyses/figure_05_revision/README.md`, Supplementary Table X and
the panel provenance of Figure 5D, 5E and Supplementary Figure 4A–F all say so.
A step-independent statement would need a per-contact reformulation of the stall
rule, which was not made.

**Superseded on 14 August 2026.** The per-contact reformulation was made. This
ladder describes the retired dynamics. The current ladder is in "Every time step
now passes the 5 % rule" below.

### The motility dynamics were corrected in three ways

Adopted 14 August 2026. The corrected model is in
`models/motility_simulation/corrected/`. Figure 5D, Figure 5E and Supplementary
Figure 4 now run it. It reads the same canonical table,
`data/processed/motility_adopted_parameters/motility_summary_parameters_adopted.csv`,
through the one accessor `adopted_parameter_table_path()`.

**One. Reorientation is instantaneous.** `reorientation_duration_s` is removed
from `MotilityParameters`. It is not set to zero; the attribute is gone and the
column sits in `RETIRED_COLUMNS`. The reason is the persistence relation that
the turning parameters are fitted through,

    tau = 1 / (D_theta + lambda * (1 - exp(-sigma^2 / 2)))

That relation carries no duration term, so a non-advancing dwell was never part
of the calibration. `tests/test_corrected_motility_dynamics.py` asserts the
removal.

**Two. The stall test fires once per contact event.** The upstream model drew
`stall_probability` at every time step of continued overlap, so a finer step
made more draws per contact. The corrected model draws once per encounter. A
cell counts as still touching a disk until its centre is more than
`CONTACT_RELEASE_UM` = 0.1 µm beyond the surface. The parameter therefore now
means a per-encounter probability, which is the quantity Grognot et al. 2023
measured.

**Three. The obstacle count scales with the box area.** An enlarged domain keeps
the published mesh density. Figure 5D and 5E now run at box scale 12, a
1776 x 1152 µm domain, with 8352 disks in agarose and none in liquid.
Supplementary Figure 4 keeps box scale 1, the published 148 x 96 µm domain with
58 disks, because it draws single trajectories.

**The mesh survives the enlargement.** A controlled ladder at one obstacle seed
gives an obstacle area fraction of 0.1851 at scale 1, 0.1856 at scale 2, 0.1871
at scale 4, 0.1873 at scale 8 and 0.1874 at scale 12. The large box is
marginally denser, by 1.2 % in area fraction. Over the 100 obstacle seeds of
Figure 5E the mean is 0.18743, range 0.1859 to 0.1888.

**What the corrections buy.** Ratios of simulated to measured effective
diffusivity, lag-corrected throughout, 100 seeds:

| medium | before | after |
| --- | --- | --- |
| liquid | 0.599–0.608 | 0.872–0.899 |
| agarose | 0.372–0.385 | 0.692–0.762 |

Against the model's own implied `v²τ/2` the liquid model now reaches 98 % to
100 %, up from 65 % to 69 %. That is the check that the dynamics match the
calibration. The reorient state is gone: its occupancy reads 0.000 in every row,
against up to 0.329 before. A motile cell in liquid now swims 100 % of the time,
up from 74.7 % to 79.3 %. Agarose stall occupancy falls from 0.179–0.259 to
0.101–0.135. Source:
`build/diagnostics/effective_diffusivity_check/effective_diffusivity_comparison.csv`.

**Agarose still falls short, and the cause is a double count.** The measured
agarose τ is derived as `2 D_eff / v²` from tracks recorded in agarose, so it
already contains the mesh. The model then adds obstacles and stalls on top of
that calibration. They remove a further 17 % to 22 % of the effective
diffusivity. In liquid there is no double count. State the agarose gap as a
limitation.

### Every time step now passes the 5 % rule

The step dependence is gone, because the stall draw is now once per contact
event. The rule is unchanged: a step passes if every group mean net displacement
stays within 5 % of the mean of the two finest steps tested, 0.000625 s and
0.00125 s, over 100 seeds and six groups. The largest deviation over the six
groups, per step:

| step (s) | largest deviation |
| --- | --- |
| 0.000625 | 2.20 % |
| 0.00125 | 2.20 % |
| **0.0025** | **1.99 %** |
| 0.005 | 3.22 % |
| 0.01 | 3.88 % |
| 0.05 | 3.96 % |

The panels integrate at 0.0025 s, the bold row. Between the two finest steps the
agarose PproB group mean now moves 0.30 %; it moved 6.4 % before. The agarose
`PproB/PproA` ratio across the whole ladder reads 3.34, 3.35, 3.29, 3.50, 3.32
and 3.45, with no trend in the step. The `selected_dt_s` column reads 0.05
because the selector returns the coarsest passing step; the panels deliberately
run finer. Source: `build/diagnostics/Figure_5/timestep_convergence.csv`.

### The four global noise constants are declared, and the cost of keeping them is measured

Four constants scale the random part of the motion. Each is global: one value
for all six strain-by-medium rows. None has a source, and none appeared in
Supplementary Table X before this revision.

| constant | value | where it lives |
| --- | --- | --- |
| `noise.run_translational_scale` | 0.12 | `config.yml` |
| `noise.stall_translational_scale` | 0.20 | `config.yml`, and `STALL_TRANSLATIONAL_SCALE` |
| `noise.stall_slide_fraction` | 0.28 | `config.yml` |
| `noise.stall_rotational_diffusion_scale` | 1.8 | `config.yml` |

`noise.reorientation_diffusion_scale`, 0.40, is also in `config.yml`, but only
the upstream model reads it. It is not a parameter of the corrected model, so it
is not in the table.

**The stalled-cell scale was invisible.** Upstream wrote 0.20 as a bare literal
inside the integration loop. It reached no config file and no table. It now
carries the config key `noise.stall_translational_scale` and the module constant
`STALL_TRANSLATIONAL_SCALE`. The value does not change, so no figure changes.
Only its visibility changes.

**The constants order the translational noise backwards.** As a multiple of the
passive diffusion coefficient `D_t` = 0.35 µm² s⁻¹, a running cell gets 0.12, a
stalled cell 0.20 and a non-motile cell 1.00. A swimming cell therefore diffuses
about eight times less than a stopped one. That is the wrong way round.

**We measured the defect rather than argued about it.** The test compares the
shipped constants against the minimal physically ordered alternative, in which
every state diffuses at the full passive rate. Both arms ran the same 100 seeds
per group, so the comparison is paired. Intervals are paired percentile
bootstraps over the seed pairs.

- Net displacement changes by at most 3.5 %, in WT agarose, 95 % CI
  [−7.1, +0.2] %. No agarose interval excludes zero.
- Agarose effective diffusivity changes by −6.2 %, in PproB, 95 % CI
  [−8.0, −4.5] %. That interval does exclude zero.
- The agarose `PproB/PproA` effective-diffusivity ratio changes by −4.9 %,
  95 % CI [−8.4, −1.2] %.
- The mechanism is a second coupling, not an error. Larger translational noise
  drives cells into obstacles more often. Contact events rise by 36 % to 56 %,
  and stall occupancy rises with them.

**Decision: declare the constants and keep their values.** Changing them would
alter a calibrated model on no evidence, because the ordered alternative has no
source either. All four are now rows of Supplementary Table X with source class
Nominal. The methods state the agarose effective-diffusivity sensitivity as a
limitation. The full measurement is in
[`motility_parameter_sources.md`](motility_parameter_sources.md), section 8.

### The box compression is re-derived

The published 148 x 96 µm box compresses the simulated strain ratios. The
earlier figure of "about 12 %" had no script behind it. A controlled scale
ladder replaces it with four measured values:

| ratio | compression | 95 % CI |
| --- | --- | --- |
| agarose PproB/PproA | 12.9 % | [8.4, 17.2] |
| agarose WT/PproA | 10.9 % | [6.0, 15.6] |
| liquid PproB/PproA | 17.1 % | [14.2, 20.0] |
| liquid WT/PproA | 9.7 % | [6.8, 12.5] |

Intervals are paired percentile bootstraps over the seeds, 10 000 draws, seed
20260814. Scale 8 and scale 12 agree within 0.6 %, the largest `plateau_shift`
being 0.0060, so scale 12 sits on the plateau. Source:
`build/diagnostics/domain_boundary_check/domain_box_compression.csv`.
