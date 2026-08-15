# Analysis report for revision tasks A1–A9

All reported quantities are generated from canonical tables during the revision
build. Values below are rounded for prose; machine-precision outputs, inferential
units and code paths are registered under `build/statistics/` and panel
provenance.

## A1 | Proteome-sector changes

**Method.** Sector means were calculated for six promoter-series conditions,
each with four biological proteomics replicates. Each of seven non-flagellar
sector means was regressed on the condition-mean flagellar mass fraction. Tests
form one predeclared family and use Benjamini–Hochberg correction.

**Result.** Rib decreased with flagellar allocation (slope −1.491, 95% CI
−1.809 to −1.173, q = 0.00141). Cbn (0.287, 0.128–0.445), Aab (0.0737,
0.0319–0.1154) and Tra (0.0856, 0.0368–0.1343) increased; q = 0.0144 for each.
Oth, Etc and Lpb showed no detectable trend in this six-condition analysis.

**Implication.** The claim that only flagellar and ribosomal sectors change does
not survive. The replacement text should state that the strong ribosomal decline
is accompanied by smaller systematic increases in carbon metabolism,
amino-acid biosynthesis and transport.

## A2 | Experimental/model sector overlay

**Method.** The build creates both raw-value and change-from-reference overlays.
Experimental ΔflhDC and model zero are kept as separately defined references.
Experimental panels show all four proteomics replicates and mean ± SD; model
curves are deterministic.

**Result.** Raw values are close near the fitted baseline. Reference subtraction
shows agreement for the ribosomal decline but opposing experimental/model trends
for Cbn, Aab, Etc and Tra.

**Implication.** The change-from-reference overlay is Figure 4B. The raw overlay
is retained as a diagnostic and must not be used to imply broad model agreement.

## A3 | Low flagellar-allocation model domain

**Method.** A deterministic harness enumerates 21 allocation values from 0% to
1% in 0.05-percentage-point steps and records requested solver, remote setting,
status, objective, growth, distance, substrate and error message.

**Result.** Every row is explicitly `blocked_exact_solver_unavailable`. The
supplied successful dynamic outputs cover 0.5–5%; local GEKKO 1.3.2 cannot use
the collaborator's solver 3/IPOPT, and the tested APOPT fallback has no solution.

**Implication.** No zero-allocation prediction is drawn. The demonstrated model
domain is reported as 0.5–5% until the exact runtime or checksum-verified sweep
is supplied.

## A4 | Effective-diffusivity decomposition

**Method.** The implemented code relation is `τ = 2D_eff/v²`, hence
`D_eff = v²τ/2` in two dimensions. Per-trajectory log D, twice log speed and log
τ are averaged within direct-pair experimental unit and phenotype. Paired
contrasts receive equal unit weight; uncertainty is the 95% percentile interval
from 10,000 fixed-seed paired-unit bootstrap resamples.

**Result.** The canonical result table reports the D ratio, speed-squared ratio,
τ ratio and exact log-identity closure for all three phenotype pairs in both
media. Figure 7A–C annotate the D ratio with its 95% CI, and Figure 7D displays
the speed-squared and τ components; closure must be ≤1 × 10⁻¹².

**Implication.** Effective diffusivity is a derived composite, and τ is a
persistence-equivalent derived timescale in this dataset. Results and Discussion
must not present speed, τ and D_eff as three independent lines of evidence.

## A5 | Chemotaxis-protein allocation

**Method.** Summed CheA, CheW, Tar and Tsr mass fractions were compared with a
predeclared 19-protein structural/apparatus set across the six condition means.
The log–log slope was tested against proportional scaling (slope 1).

**Result.** Slope = 1.111 (95% CI 0.945–1.276); p = 0.137 against slope 1.
All requested proteins were present in all four replicates of all six conditions.

**Implication.** Differential scaling is not detected, but abundance cannot test
chemotactic performance. The result is report/source data only; no figure-level
functional conclusion is drawn.

## A6 | WT(S171) single-cell growth

**Method.** Mother-machine strain identities were checked against the population
sample map.

**Result.** TH9677/WT(S171) is absent. Available Ppro mother-machine strains are
EM9662/Ppro1, EM9661/PproA, EM9660/PproB and EM8513/PproD.

**Implication.** No substitute WT is added. Ppro1 is the explicitly labelled
within-replicate reference in Figure 2C.

## A7 | Heterogeneity at 0.5 ng/mL AnTc

**Method.** Available data modalities were audited for a Ptet single-cell growth
distribution at the specified concentration.

**Result.** No such dataset exists. Plate-reader wells and hook-count microscopy
cannot support a dip test, mixture model or non-growing single-cell fraction.

**Implication.** This task is not testable. The manuscript's single-cell
heterogeneity interpretation should be removed or explicitly labelled untested.

## A8 | WT growth-rate offset

**Method.** Independent-day TH9677 controls from the Ptet and Ppro population
series were compared, and the fitting implementation was checked as a possible
source of the offset.

**Result.** Ptet-series TH9677 was 1.0867 ± 0.0239 h⁻¹ and Ppro-series TH9677
was 1.6236 ± 0.0543 h⁻¹ (mean ± SD; n = 6 days each). The difference was
0.5369 h⁻¹ (exploratory 95% CI 0.4965–0.5824), a ratio of 1.494; Welch p ≈
1.2 × 10⁻⁷. The series were collected in different 2024/2025 batches. Fitting
method accounts for only approximately 1.2% of the offset.

**Implication.** Figures 2–3 normalize population growth to same-day TH9677 and
retain absolute rates in Source Data. The offset is batch-associated and not
accepted as a biological background effect.

## A9 | Assembly-mutant growth effects

**Method.** Mutant-minus-TH5861 population effects were paired across six
experimental days. Confidence intervals are paired 95% intervals; five tests
receive BH correction. The two mother-machine experiments are shown
descriptively and pooled cells are not inferential units.

**Result.** Population differences in h⁻¹ were: ΔflhDC +0.2151 (95% CI
0.1746–0.2555, q = 9.40 × 10⁻⁵), ΔflgE +0.1844 (0.1628–0.2059,
q = 1.80 × 10⁻⁵), ΔflgKL −0.0336 (−0.0730–0.0059, q = 0.0865),
motB(D33N) +0.0572 (0.0092–0.1051, q = 0.0465), and ΔflgM flhAΔc
−0.0207 (−0.0458–0.0043, q = 0.0865). ΔflgM flhAΔc is approximately
WT-like in population measurements but about 0.218 h⁻¹ lower in the
mother-machine context.

**Implication.** The mutant sentence can be quantitative, but the
population/single-cell disagreement remains an assay-context limitation rather
than a pooled-cell statistical result.
