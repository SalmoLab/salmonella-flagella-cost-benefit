# Proposed descriptive figure legends

These are figure-only replacement legends. They define graphical elements and
sampling units without interpreting results. Exact cell and trajectory counts
are also provided in the Source Data workbook.

## Figure 1 | Tunable control of flagellar number per cell

**A,** Ptet-flhDC control design; editable source pending. **B,** Representative
Ptet hook and filament microscopy; calibrated raw images pending. **C, D,** Hook
and filament counts per cell, respectively, across the ordered AnTc series. Each
panel is a discrete count-frequency plot; it shows no kernel density and no box.
Counts are integers, so each observed count is one mark whose half-width follows
the square root of its cell frequency. A count carried by 12 cells or fewer is
drawn as individual cell dots instead. A mark whose fill is near white carries a
thin outline in a darker shade of that same fill, so the lightest conditions stay
visible. Grey dots are the independent replicate means, and the dark bar is the
mean of those replicate means. Each condition prints its mean ± SD across
replicates and its cell count. C and D show the titration and draw no test. The
registered statistics table compares each AnTc level to WT by a two-sided Welch
t-test on the three replicate means. After Benjamini-Hochberg correction across
the six levels of the panel no level differs from WT: the smallest q is 0.088 in
C and 0.22 in D. **E,** Hook versus filament counts for matched
cells. One bubble is one observed count pair, and bubble area follows the square
root of the number of cells; the key gives 10, 100 and 1000 cells per bubble. No
line is fitted, no interval is drawn and no test is run. Each bubble pools every AnTc level of
the series, so the bubbles carry one neutral ink rather than a condition color.
**F,** Ppro promoter-series design; editable source pending. **G,**
Representative Ppro microscopy; calibrated raw images pending. **H,** Hook counts
per cell across the ordered Ppro series, drawn with the discrete-count geometry
of C and D. Each strain is compared to TH9677 by a two-sided Welch t-test on the
three replicate means: P = 0.012 for Ppro1-flhDC, 0.013 for PproA-flhDC, 0.0075
for PproB-flhDC and 0.00034 for PproD-flhDC. Benjamini-Hochberg correction across
the four comparisons of the panel gives q = 0.0014 to 0.013. In C, D and H, color identifies the inducer concentration or the
promoter strength, as decoded in A and F and in the panel keys. A key swatch that
names a graphical concept, such as cell-count frequency, uses a neutral grey and
never a strain color.

## Figure 2 | Growth cost across tunable flagellar-number series

**A,** Population growth across the Ptet/AnTc series. **B,** Population growth
across the Ppro series. Each growth curve is divided by the mean of the same-day
TH9677 WT reference. The reference is divided the same way, curve by curve, so it
scatters around 1.0 like every other condition. The light marks are the single
growth curves and stay descriptive: 10 curves per condition per day in A, and 3
curves per condition per day in B. The solid marks are the six independent
experiment days, and the day is the sampling unit of every test. The summary is
the mean of those day values with its 95% bootstrap confidence interval. Each
condition is compared to the reference by a two-sided paired t-test on the day
values, with Benjamini-Hochberg correction inside the panel. In A, P = 0.0053,
0.0075, 0.45, 0.0011, 0.00019 and 0.0043 for 0, 0.25, 0.5, 1, 2 and 4 ng/mL AnTc,
and correction across the six comparisons gives q = 0.0011 to 0.45. In B,
P = 1.4 × 10^-5 for Ppro1-flhDC, 3.6 × 10^-5 for PproA-flhDC, 0.0015 for
PproB-flhDC and 5.3 × 10^-5 for PproD-flhDC, and correction across the four
comparisons gives q = 5.5 × 10^-5 to 0.0015. The scatter of the reference is
within-day variation only. The normalization removes between-day variation by
design, and that removal is its purpose: the reference grows at 1.087 1/h in the
experiment series of A and at 1.624 1/h in the series of B, a difference of
0.537 1/h between batches. The three decimals are carried so the printed
difference matches the printed rates. Absolute growth rates are retained in Source Data. **C,**
Single-cell growth across Ppro strains, with each cell divided by the mean of
Ppro1-flhDC from its own mother-machine experiment. Ppro1 is divided the same way,
cell by cell, so it also scatters. The violin describes 126934 cell values and
carries no inference. The two points are the two independent experiments per
strain and carry the statistics; the summary is their mean with a 95% confidence
interval. Each strain is compared to Ppro1-flhDC by a two-sided paired t-test on
those two experiment means: P = 0.021 for PproA-flhDC, 0.17 for PproB-flhDC and
0.071 for PproD-flhDC. Benjamini-Hochberg correction across the three comparisons
gives q = 0.063 to 0.17, so no strain differs from the reference once the panel is
corrected. Two experiments per strain is the whole inferential sample of C.
Ppro1 is the within-experiment reference because TH9677/WT (S171) was
not measured in this dataset. Colors identify the ordered inducer or promoter
series. A key swatch that names a graphical concept, such as the cell
distribution, uses a neutral grey and never a strain color.

## Figure 3 | Dissecting the growth cost of flagellation

**A,** Flagellar assembly-mutant design; editable source not supplied. **B,**
Population growth of the assembly-mutant series. Each value is normalized to the
same-day WT. The light marks are single growth curves and stay descriptive; the
solid marks are the six independent experiment days; the summary is the mean of
those day values with its 95% confidence interval. Each mutant is compared to the
same-day WT by a two-sided paired t-test on those six day values: P = 4.2 × 10^-5
for ΔflhDC, 2.9 × 10^-6 for ΔflgE, 0.077 for ΔflgKL, 0.027 for motB (D33N) and
0.086 for ΔflgM flhAΔc. Benjamini-Hochberg correction across the five comparisons
gives q = 1.4 × 10^-5 to 0.086. **C,** Single-cell growth for
the same mutants, with each cell normalized to the WT mean of its replicate. The
violin describes 110983 cell values and carries no inference; the two points are
the independent replicates, and the summary is their mean with a 95% confidence
interval. Each mutant is compared to the replicate WT by a two-sided paired
t-test on those two replicate means: P = 0.049 for ΔflhDC, 0.11 for ΔflgE, 0.11
for ΔflgKL, 0.41 for motB (D33N) and 0.020 for ΔflgM flhAΔc. Benjamini-Hochberg
correction across the five comparisons gives q = 0.10 to 0.41, so no mutant
differs from WT once the panel is corrected.
Each mutant keeps one color and one marker shape in B and C. **D,**
Cell-economy-model growth over flagellar protein mass fraction. Both curves are
deterministic model output, so both carry the summary ink. The solid line is
rotating flagella and the dashed line is non-rotating flagella; the model states
no uncertainty. **E,** Measured growth penalty against the flagella-free
reference. One point is one experiment day and keeps the color and shape of its
strain in B and C: grey circles are WT (fliC-ON) under Rotating, and pink
diamonds are motB (D33N) under Non-rotating. The black diamond is the mean of the
day values with its 95% confidence interval. The black square is the single
model value at 5% flagellar mass fraction. The panel draws no bar. In D and E, color never encodes
rotation. Color names the strain or marks a derived value, rotation is the line
style in D and the category position in E, and every derived mark uses one
summary ink. A key swatch that names a graphical concept, such as experiment
days, uses a neutral grey and never a strain color. In E each condition is
compared to the same-day ΔflhDC reference by a two-sided paired t-test on the six
day values: P = 2.2 × 10^-5 for rotating flagella and 0.00050 for non-rotating
flagella, with Benjamini-Hochberg q = 4.4 × 10^-5 and 0.00050 across the two
comparisons. D is deterministic model output and carries no test.

## Figure 4 | Proteome allocation under increasing flagellar investment

**A,** Editable cell-economy-model schematic; arrows and labels identify model
sectors, material fluxes and constraints. **B,** Sector changes relative to the
separately labelled experimental ΔflhDC and model-zero references. Small circles
are the four biological proteomics replicates per strain and diamonds are the
condition means. No dispersion bar is drawn. The line is deterministic
cell-economy-model output and carries the neutral summary ink, not the sector
color; it has no uncertainty band. The line is solid over the measured range and
dashed above 3.34% flagellar allocation, which no strain reaches, so the
extrapolated part is explicit. The flagellar sector has no sub-axes here:
flagellar allocation is the x variable, so that sub-axes plotted the variable
against itself, and the model imposes the flagellar sector to equal the imposed
allocation. The Oth line is flat because the model fixes that sector at 0.35. It
is a constraint of the model, not a successful prediction. The panel draws no
regression: the drawn line is the model. Across the six measured condition means
the ribosomal sector falls with flagellar allocation with a slope of -1.49
(95% CI -1.81 to -1.17; ordinary least squares, P = 0.00021, Benjamini-Hochberg
q = 0.0015 across the seven non-flagellar sectors). That one regression is
printed because the ribosome-flagellum trade-off is the claim this figure rests
on; the six other sector regressions are in the registered statistics table.
**C,** Protein
contributions within each sector, as means over the four biological replicates.
An external label names a protein when it carries at least 0.06% of total
protein mass in one condition and, in addition, either reaches 15% of the
displayed sector subtotal or ranks among the three most abundant proteins of its
sector. FliC is named independently of both rules. Each leader line points at the
strain where its segment is thickest as drawn. The complete named and dropped
list, with one reason per protein, is Source Data. **D,** Measured mean sector
fractions per strain; stacked colors use the fixed sector palette. **E,** Modeled
sector fractions over flagellar allocation, in the same palette. In C, D and E a
thin white line separates the stacked segments. **F,** Growth
rate versus ribosomal and flagellar allocation. Small circles are the six
independent growth-experiment days per strain, so the six days of one strain
share the single proteomics-derived allocation of that strain. Diamonds are the
strain means. The line is cell-economy-model output and not a fit to these
points; no confidence band is drawn, and the line is dashed where the model runs
past the measured flagellar range. A, C, D, E and F draw no test.

Sector membership follows the delivered KEGG mapping, with the exceptions
recorded in `analyses/figure_04_revision/config/protein_sector_overrides.csv`.
Sigma-70 (RpoD) and the ribose-import binding protein RbsB carry a flagellar or
chemotaxis KEGG map for a reason that is not flagellar, and both are flat across
the promoter series, so both are counted outside the flagellar sector. Figure 4
and Supplementary Figure 2 read that one table.

## Figure 5 | Motility benefit and the predicted optimum

**A,** Simulated travelled distance over time at fixed flagellar allocations.
Colored lines denote distance, circles denote final endpoints, and the grey area
on the secondary axis is the fixed glucose profile established for 3 h (mM).
**B,** Deterministic growth trajectories. Colored lines are flagellar
allocations from 0.5% to 5%, and color identifies allocation. The dashed grey
line is the non-motile reference at 0% allocation. That cell builds no
flagellum, stays 8500 µm from the source and holds 1.063 1/h on the 0.091 mM
glucose it starts in. Every motile allocation reaches 1.66–1.77 1/h by 8 h,
which is a gain of 56% to 66% over the non-motile cell. Compounded over the
8 h, the same allocations reach 8.3-fold to 35.5-fold the non-motile biomass.
The 0% trajectory was solved here with IPOPT on the public APMonitor server
(GEKKO `remote=True`); the 0.5–5% trajectories are the supplied solver tables,
which that route reproduces to 1e-9 relative error. The sweep between 0% and 1%
is recorded but not drawn. A warm-start continuation with a multi-start solved
all 21 steps of that interval, yet the solutions do not follow one consistent
branch, so no interior curve is claimed. The model is coarse-grained: it
recovers the trend of a benefit that rises steeply from zero and then flattens,
and it does not fix the allocation of the optimum to the precision the tick
labels suggest. **C,** Normalized final biomass versus ordered flagellar
allocation; points are fixed model outputs and the line connects the ordered
allocation values. A, B and C are deterministic model output and carry no test.
**D, E,** Active-particle simulated net displacements
in liquid and agarose-like media. Net displacement is the straight-line distance
from the start to the end of a simulated track, and it is the only plotted
observable. Each point is the mean of 26 simulated cells for one of 100 fixed
random seeds per phenotype; the center is the seed median and the interval spans
the 2.5th–97.5th seed percentiles. These intervals describe simulation
variability, not biological confidence intervals, and D and E report no P value
because a simulation seed is not an experimental unit. Both panels run in a domain of
1776 × 1152 µm, twelvefold larger in each direction than the published
148 × 96 µm box. Both panels integrate at dt = 0.0025 s. The agarose-like panel
**E** holds 8352 obstacle disks, a realised obstacle area fraction of 0.187. The
liquid panel **D** holds no obstacle.

The simulation illustrates the experimental findings; it does not predict them.
Run speed, motile fraction and persistence time are model inputs calibrated to
the measured paired-unit means, so panels D and E do not predict the measured
speed or effective-diffusivity ordering. The collaborator's delivered table had
already set run speed and motile fraction from these same measurements. The
turning parameters had not been calibrated; they were calibrated in this
repository and were not supplied by the collaborator. The reorientation angle
spread is one value for all six strain-by-medium rows, σ = 1.247 rad, set so the
mean turn magnitude equals the 57° measured over 8058 turns of *E. coli* (Taute
et al., 2015). The anchor matches the mean turn magnitude only: it is a
three-dimensional *E. coli* measurement applied to a two-dimensional
*Salmonella* model, and a Gaussian turn cannot reproduce the measured
forward-skewed shape. In the agarose-like medium the per-contact stall
probability falls with the mean flagella number as N^−0.704 (PproA 0.210, WT
0.177, PproB 0.123), normalized so its mean over the three strains is unchanged.
The exponent sets the ratio between the least and the most flagellated strain to
the 1.7 ± 0.2 stall-frequency ratio measured in 0.25% agar by Grognot et al.
(2023). That study varied a second flagellar system in *Vibrio alginolyticus*
rather than the flagella count, so the mapping onto our flagella numbers is an
assumption and only the ratio is anchored; the absolute value is nominal. The
mean stall duration is one nominal value, 0.949 s, for all three strains,
because the same study found the flagella effect on stall duration significant
only at 0.16% agar and not at 0.25%. Net displacement, obstacle trapping, the
stall duty cycle and the spatial search pattern remain model outputs that no
measurement supplies. The simulation reaches 87–90% of the measured effective
diffusivity in liquid and 69–76% in the agarose-like medium. Both ratios are
lag-corrected, and each rests on 100 seeds. Reorientation is instantaneous, so
no cell spends time in a non-swimming reorientation state. The agarose shortfall
is the larger one because the measured persistence time already contains the
mesh. The model then adds obstacles and stalls on top of that calibration, so
agarose counts the mesh twice. Liquid carries no double count, and there the
model reaches 98–100% of its own implied v²τ/2. The run that uses the delivered
turning parameters is kept as a diagnostic under `build/diagnostics/`.

Panels D and E report net displacement because contour path length was tested
and rejected. Contour path length does not converge under time-step refinement.
A trajectory with a diffusive component has an infinite arc length in the
continuum limit, so the summed step length grows without a limit as the step
shrinks. Between dt = 0.05 s and dt = 0.000625 s the simulated mean path length
of WT in the agarose-like medium rises from 325 µm to 595 µm and is still
rising. The PproA/WT path-length ratio drifts with it from 0.54 to 1.10 and
crosses 1, so the strain comparison was a property of the chosen step and not of
the model. Net displacement converges in both media. A 100-seed test accepts
every step whose group mean net displacement stays within 5% of the mean of the
two finest steps tested, 0.00125 s and 0.000625 s. Every step of the tested
ladder passes. The largest deviation over the six strain-by-medium groups, by
step: 3.96% at 0.05 s, 3.88% at 0.01 s, 3.22% at 0.005 s, 1.99% at 0.0025 s,
2.20% at 0.00125 s and 2.20% at 0.000625 s. Panels D and E and Supplementary
Figure 4 integrate at dt = 0.0025 s, the step with the smallest deviation. The
step dependence is gone because the model draws the stall test once per contact
event and not once per time step of overlap. Between the two finest steps the
PproB agarose-like group mean moves by 0.30%. Over the same six steps the
agarose-like PproB/PproA net-displacement ratio holds at 3.45, 3.31, 3.50, 3.29,
3.35 and 3.34, with no trend in the step.
The upstream configuration file declares 0.05 s and was not edited; the builder
overrides the step. `build/diagnostics/Figure_5/timestep_convergence.csv` holds
the check.

## Figure 6 | Soft-agar motility and structured-medium competition

**A, B,** Soft-agar motility of the Ptet-flhDC series (**A**) and the
Ppro-flhDC series (**B**). Both panels use the same unit of analysis, the
independent experiment: an experimental day in A and a replicate in B. The small
pale marks are the individual measurements, the filled marks are the independent
units, and the black diamond is the mean with its 95% confidence interval across
units. A draws all three layers; B draws no pale layer, because there each
replicate carries a single measurement. **A,** Every value is normalized to
the same-day WT mean, so each of the 93 soft-agar wells is drawn around the day
it belongs to. WT was measured on two experimental days and every AnTc condition
on four, so the WT interval rests on two units and the others on four. Because
WT is the normalizer, both WT day means are 100% by construction and the WT
confidence interval has zero width; the WT wells nevertheless span 94.3% to
109.3%, which is the well-to-well spread of the reference. A draws no test; the
registered table holds the mean of each condition with its 95% confidence
interval, and the WT interval rests on two units. **B,** Each of the
six independent replicates per strain carries a single measurement, so the
measurement and the independent unit are the same number and one mark shows
both. Each strain is compared to WT by a two-sided paired t-test on those six
replicate pairs: P = 3.8 × 10^-8 for Ppro1, 4.5 × 10^-5 for PproA, 1.5 × 10^-6
for PproB and 1.9 × 10^-6 for PproD. The registered table holds no correction for
this panel, so these four P values are uncorrected. **C,** Hook counts per cell for cells sampled from the center, middle and
outer positions of one soft-agar plate (n = 257 cells per position), drawn with
the discrete-count geometry of C, D and H in Figure 1 and E–G in Figure 7. Hook
count is an integer, so each observed count is one mark whose half-width follows
the square root of its cell frequency; a count carried by 12 cells or fewer is
drawn as individual cell dots instead. The black bar is the mean of all cells at
that position, and each position prints its mean ± SD and its cell count. All
257 cells per position come from a single plate, so the panel carries no
replicate layer, is descriptive and shows no test. The original calibrated halo
image remains pending. **D,** Structured-medium competition workflow
reconstructed from the editable design source. The concentric rings of the
soft-agar spot are neutral greys that mark expansion distance only; the
schematic makes no claim about which strain occupies which ring, because strain
identity per region is measured in E. Uncalibrated image regions remain explicit
placeholders. **E,** Hook-count composition of the two competing strains across
the four sampled regions R1–R4. Each point is the mean fraction of all cells in
that region carrying the given hook count, so one strain's values sum to that
strain's share of the region. Error bars are ±1 SD across imaging fields, with
18, 13, 13 and 12 fields for R1 to R4. The fields are imaging positions within a
single competition experiment and are not biological replicates, so the panel is
descriptive and shows no test. The four region images are placeholders: a
calibrated microscopy field is required for every region, and no scale bar is
shown because the scale is not inferred. Reporter pseudocolors are decoded
separately from phenotype colors.

## Figure 7 | Single-cell swimming behavior and hook-number differences

**A–C,** Paired swimming summary for WT/PproA, WT/PproB and PproA/PproB,
respectively, grouped by medium. Each panel is two rows: unit mean speed above,
unit mean log10 effective diffusivity (log10 D_eff) below. One marker is one
paired experimental unit, that is one direct co-imaged session. A marker is the
mean over that unit's trajectories of a natural logarithm, printed as speed in
µm/s on the upper row and as log10 D_eff on the lower row. A thin line joins the
two phenotypes measured in that session, so the reader sees the within-session
contrast. The violin is the kernel density of the unit means. Medium is the
filled circle for agarose and the open square for liquid, which is the
convention of panel D and of Supplementary Figure S3. The header above the
upper row names the medium and its paired-unit count. The header above the lower
row gives the D ratio and, in brackets, its 95% confidence interval. D ratio is
PproA/WT in A, PproB/WT in B and PproB/PproA in C. The dashed line denotes
D_eff = 1. Paired-unit counts (agarose/liquid) are 18/16, 18/18 and 18/16. The
pooled-trajectory probability contours are Supplementary Figure S5.
**D,** Paired-unit decomposition of `D_eff = v²τ/2`. The three rows are speed²
(measured), the derived timescale τ = 2D/v², and, below a thin rule, the D_eff
product. Each bar runs from the reference at 1 to the estimate, so on the log
axis the two component bar lengths add to the product bar length. Bars are
filled for agarose and open for liquid; the key at the top left of the strip
gives that convention. The number beside a bar is its point estimate. Estimates
are equal-weight mean log ratios. Intervals are 95% percentile intervals from
10,000 fixed-seed paired-unit bootstrap resamples, and the dashed line at ratio
1 is no change. All three subplots share one symmetric log axis from 1/6.5 to
6.5, so the reference line holds one position and equal bar lengths mean equal
effects. Each subplot prints its paired-unit count per medium. The component
rows carry no hue, because row position and row label already separate them.
τ is a derived persistence-equivalent timescale, not an independent
measurement. A to D print no P value. Each reports a paired-unit estimate with
its 95% bootstrap interval, and that interval is the inference the panel
carries. **E–G,** Hook counts per cell for the three
phenotype pairs, drawn with the discrete-count geometry of C, D and H in Figure
1. Hook count is an integer, so each observed count is one mark whose half-width
follows the square root of its cell frequency. A count carried by 12 cells or
fewer is drawn as individual cell dots instead. Grey points are the six
independent day-replicate means per phenotype, and the black bar is the mean of
those replicate means. Each phenotype prints its mean ± SD across days and its
cell count. Where the hook axis clips, the key names the number of cells above
it. E to G are descriptive and show no test.

## Supplementary Figure S1 | Single-cell growth analysis windows

Cell-level normalized growth for mother and non-mother lineages across the Ppro
series. **A,** Pooled stable window 200–800 min, 126934 cell values. **B,** Pooled
stable window 180–480 min, 65967 cell values. Both panels use the three layers of
Figure 2C. The violin describes the cell distribution and carries no inference.
The two points are the two independent mother-machine experiments for that strain
and lineage class. The bar is the mean of those two experiment means. This figure
reports no test. Colors identify Ppro strains, and the promoter order runs Ppro1
to PproD as in every other figure. Cell counts per strain, lineage class and
experiment are provided in Source Data.

## Supplementary Figure S2 | Flagellar-protein allocation

Protein-level mass fractions for the 60 proteins of the flagellar sector. One
cell is one protein and one point is the mean of the four biological proteomics
replicates of one strain, across the six promoter-series conditions. Colors
identify strains. Every cell shares one y axis, so the panel compares proteins
directly. The figure is descriptive and reports no test. The chemoreceptor is
Tsr, from the delivered gene name `tsr`; `Tst` in the earlier legend was a typo.

Sigma-70 (RpoD) and the ribose-import binding protein RbsB are not shown. The
delivery assigns both to the flagellar sector through a single KEGG map, neither
is a flagellar protein, and both are flat across the promoter series. This panel
and Figure 4 read the same override table,
`analyses/figure_04_revision/config/protein_sector_overrides.csv`, which records
one reason per protein. The complete plotted matrix is Source Data.

## Supplementary Figure S3 | Paired-unit motility summaries

Paired experimental-unit summaries for median speed, swimming fraction and the
derived persistence-equivalent timescale across the three phenotype pairs and
two media. The panels use the geometry of Figure 7A-C. **A-C,** median speed.
**D-F,** swimming fraction. **G-I,** persistence-equivalent timescale. Each
column is one phenotype pair: WT against PproA, WT against PproB, PproA against
PproB. Inside a panel the two media stand side by side as two groups, agarose on
the left and liquid on the right.

One marker is one direct co-imaged experimental unit. A thin line joins the two
strains measured in the same unit, so the reader sees the within-unit contrast
that the bootstrap resamples. Colour identifies the strain, in the three colours
Figure 7A-C uses. Medium is carried by marker shape and fill: a filled circle is
agarose and an open square is liquid. The violin is the kernel density of the
plotted unit values on the plotted scale.

The black diamond is the group mean of the plotted quantity. The whisker on the
second strain's diamond is the paired-unit 95% confidence interval, anchored at
the first strain's mean; the first strain is the reference the contrast divides
by, so its diamond carries no whisker of its own. The header above each group
states the medium, the paired-unit estimate, that interval and the number of
paired units.

**The estimate is always the second strain against the first**, in the order the
x axis names them. On the median-speed and persistence rows it is the ratio
second/first: PproA/WT in A and G, PproB/WT in B and H, PproB/PproA in C and I.
On the swimming-fraction row it is the difference second − first: PproA − WT in
D, PproB − WT in E, PproB − PproA in F. The same wording is the `contrast`
column of every effect table. Every interval is a percentile bootstrap over
paired experimental units, 10 000 draws, and is an estimate, not a test.

The three panels of a row share one y range, so the three phenotype pairs are
read on one scale. Median speed and the persistence-equivalent timescale are
drawn as log10 on a linear axis and the ticks print the original unit; a log
axis would estimate the violin density in the original unit and then stretch it.
The effective-diffusivity row was withdrawn because it repeated Figure 7A-C from
the same input file with a different within-unit summary. Exact unit counts and
all values are Source Data, and the paired estimates with their intervals are in
`build/statistics/Supplementary_Figure_3/`.

## Supplementary Figure S4 | Representative active-particle trajectories

Representative fixed-seed trajectories for PproA, WT and PproB in liquid and
agarose-like simulations. Colors identify phenotype. A filled circle marks a
cell that ended in a run, a filled square marks a stalled cell, and an unfilled
circle marks a non-motile cell. Grey disks are the agarose-like obstacles. The
scale bar in each panel is 20 µm. Maps illustrate simulated trajectories and are
not biological replicates or independent validation.

The simulation illustrates the experimental findings; it does not predict them.
Run speed, motile fraction and persistence time are model inputs calibrated to
the measured paired-unit means, so these maps do not predict the measured speed
or effective-diffusivity ordering. The collaborator's delivered table had
already set run speed and motile fraction from these same measurements. The
turning parameters had not been calibrated; they were calibrated in this
repository and were not supplied by the collaborator. The reorientation angle
spread is one value for all six strain-by-medium rows, σ = 1.247 rad, set so the
mean turn magnitude equals the 57° measured over 8058 turns of *E. coli* (Taute
et al., 2015); the anchor matches the mean turn magnitude only. In the
agarose-like medium the stall probability is a per-contact-event probability,
drawn once when a cell first meets an obstacle it was not already touching; it
falls with the mean flagella number as N^−0.704, at the strength Grognot et al.
(2023) measured for the stall frequency in 0.25% agar, and the mean stall
duration is one nominal value, 0.949 s, for all three strains. Reorientation is
instantaneous, because the persistence relation the turning parameters are fitted
through carries no duration term, so no track shows a stationary reorientation
pause. The spatial search pattern, obstacle trapping and the stall duty cycle
remain model outputs that no measurement supplies.

These maps keep the published 148 × 96 µm domain with reflecting walls, and each
agarose-like map keeps its 58 obstacle disks. A small field is what makes
individual tracks legible. These maps show a spatial pattern and report no
number. Figure 5D and 5E measure, so they run in a domain enlarged twelvefold in
each direction, 1776 × 1152 µm with 8352 obstacle disks, where the walls no
longer compress the strain ratios. The obstacle count scales with the box area,
so both domains hold the same mesh density. The reflecting walls of these maps
shorten the faster strains more than the slower ones, so the maps must not be
read as a quantitative comparison of spread.

These maps integrate at dt = 0.0025 s, the same step as Figure 5D and 5E, so
both figures depict one simulation. A convergence check covers that step: every
step of the tested ladder passes the 5% rule, and 0.0025 s carries the smallest
deviation. See the Figure 5 legend. The upstream configuration file declares
0.05 s and was not edited; the builder overrides the step. Contour path length is plotted nowhere,
because it does not converge under time-step refinement. Figure 5D and 5E report
net displacement instead. These maps show a spatial pattern and not a scalar, so
that rejection does not change what they draw.

Simulation parameters and seeds per panel, all at 26 cells, 20 s of simulated
time and a 0.0025 s integration step:

**A,** PproA, liquid: motile fraction 0.63, run speed 19.9 µm/s, reorientation
rate 6.21 1/s, stall probability 0.00; seed 24. **B,** WT, liquid: 0.80,
27.6 µm/s, 6.62 1/s, 0.00; seed 106. **C,** PproB, liquid: 0.86, 32.0 µm/s,
5.09 1/s, 0.00; seed 65. **D,** PproA, agarose-like: 0.42, 15.4 µm/s,
13.15 1/s, 0.21; seed 17. **E,** WT, agarose-like: 0.73, 23.2 µm/s, 7.81 1/s,
0.18; seed 99. **F,** PproB, agarose-like: 0.75, 28.6 µm/s, 6.82 1/s, 0.12;
seed 58. Every panel uses the same reorientation angle spread, σ = 1.247 rad,
and every agarose-like panel the same mean stall duration, 0.949 s.
Each agarose obstacle field uses the panel seed plus 300, and starting
positions use the panel seed plus 1.

## Supplementary Figure S5 | Speed and effective-diffusivity probability contours

**A–C,** Swimming speed against log10 effective diffusivity (log10 D_eff) for
WT/PproA, WT/PproB and PproA/PproB, respectively. Each panel places the
agarose-like and the liquid medium side by side on shared axes. Contours enclose
50% and 95% of the kernel-density probability mass. The first phenotype of a pair
is a filled band and the second is an outline, so two neighbouring colors stay
separable. The dashed line denotes D_eff = 1. Each medium prints its
paired-experiment count and its trajectory count per phenotype;
paired-experiment counts (agarose/liquid) are 18/16, 18/18 and 18/16. The
contours pool every trajectory of a phenotype, so they describe the trajectory
distribution and not the between-experiment uncertainty. The inferential unit
remains the paired experiment, which Figure 7A–D quantifies. The two contour
levels were fixed at 50% and 95% in advance and were not retuned to separate the
phenotypes. The density grid is padded by four kernel bandwidths per axis, so
every contour closes inside the grid and a 95% contour encloses 95% of the data.

Marginal kernel densities above and to the right of each axes use the same
fill-against-outline convention as the contours. The centroid marker of a
phenotype is the mean of its per-unit centroids in the speed and log10 D_eff
plane, and its whiskers are 95% confidence intervals from a paired-unit bootstrap
with 10000 resamples at a fixed seed. A whisker that does not extend past its
marker denotes a confidence interval narrower than the marker, and the thin
connector joins the two centroids of a pair. Each whisker is a marginal interval
for one phenotype, so two whiskers may overlap while the paired difference
excludes zero; the paired differences and their intervals are in the statistics
table and must not be read off the panel. The figure prints no P value. Every
registered value is a paired-unit estimate with its 95% interval.
