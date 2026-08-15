# Not done and explicit limitations

## Blocked by missing data or assets

- Figure 1A: editable flhDC/Ptet schematic source.
- Figure 1B: raw calibrated Ptet hook/filament microscopy and processing record.
- Figure 1F: editable Ppro promoter-series schematic source.
- Figure 1G: raw calibrated Ppro microscopy and processing record.
- Figure 3A: editable assembly-mutant schematic source.
- Figure 6 image regions: original calibrated microscopy fields and intended
  scale-bar length. Quantitative subpanels and the reconstructed design schematic
  remain available.
- A3 is no longer blocked. The low-allocation sweep ran on Michael Jahn's route,
  GEKKO with `remote=True` and solver 3 (IPOPT) on the public APMonitor server.
  Results are in `build/statistics/Figure_5/A3/`; the settings are in
  `models/cell_economy/LOCAL_SOLVER_VALIDATION.md`. A warm-start continuation
  with a multi-start solved all 21 steps on 14 August 2026, including the two,
  0.75% and 0.95%, that had failed. What remains open is not a failure but the
  scatter: the solved interior of the 0–1% interval does not follow one branch,
  so Figure 5B draws the 0% baseline and the 0.5–5% family and no curve between
  them. A solve that pins the interior to one branch would need a global
  optimiser, not a better initial guess.
- A6: TH9677/WT(S171) mother-machine data.
- A7: Ptet single-cell data at 0.5 ng/mL AnTc.
- Complete proteomics raw chain: raw MS files, FASTA, Spectronaut project and
  settings remain absent from the collaborator delivery.
- Figure 6E biological replication. The spatial-competition experiment exists
  only once. Its source is four workbooks in
  `data/Ppro-flhDC_population-motility-competition/`, one per plate region, each
  holding 12 to 18 region-of-interest sheets whose only columns are the two
  fluorescence channels and `Foci_number`. No date, plate or experiment column
  exists in any of them, so no biological repeat can be identified.
  The regions of interest are imaging fields within one experiment. The panel
  therefore reports mean and standard deviation across imaging fields and names
  them as such. A second independent competition experiment would be needed
  before any inferential comparison between the strains is defensible.

## Coauthor requests not addressed

- The revision brief requires every panel to appear in the Results text, and it
  names the simulation panels of the old Figure 2G and 2H, now Figure 3D and 3E,
  as described nowhere: describe them or move them to the supplement. Neither
  was done. This wave changed figures only, and the Results text is deferred to
  the manuscript-editing wave, so the request is still open.
- Michael Jahn suggested that the eight-sector cell-economy schematic could
  serve as Figure 1A, so the flow of cellular resources is established before
  any result. The brief calls that a narrative change rather than a figure edit
  and asks for it to be flagged, not implemented. The schematic therefore stays
  at the head of Figure 4. The decision was taken during the revision and is
  written down here for the first time.
- **Exact P values are now in the legends; this item is closed.** Decision §1.6
  asked for the effect size, the confidence interval and the exact P value. The
  first two were already in. The P values were inlined on 15 August 2026, and
  the authoring decision was this. A panel prints a P value only where it draws
  a comparison the argument rests on: F1_H, F2_A, F2_B, F2_C, F3_B, F3_C, F3_E,
  F4_B and F6_B. Every other panel now says in its legend that it draws no
  test, rather than acquiring one. F1_C and F1_D are the AnTc titration, read
  as a series and not as six contrasts, so each prints only the smallest
  corrected value of its family; that is what stops a reader inferring a
  per-level difference the data do not carry. F4_B prints the ribosomal-sector
  regression alone, because the ribosome-flagellum trade-off is the claim that
  figure rests on, and the legend names the registered table for the other six
  sectors. Every printed value is computed by `tools/build_revision_reports.py`
  and carries a row in `figure_numbers.csv`;
  `tests/test_legend_probabilities.py` fails if a legend quotes a value the
  register no longer produces. Benjamini-Hochberg values are labelled q and
  never P. Figure 6B has no registered correction, and its legend says so.
- Two coauthor Methods items belong to the manuscript and cannot be closed
  here: the missing Omnipose citation and the missing LC gradient detail. Both
  are written up with the exact reference and the exact list of absent
  acquisition parameters are recorded with the corresponding author.

## Needs an authoring decision

- Figure 4A prints below the 6 pt floor and cannot be fixed inside this
  collection. The panel is the collaborator's vendored schematic
  (`resources/images/salmonella_model.svg`), whose text is declared at 7, 9 and
  12 px on a 360 x 240 pt canvas. Its 48 mm slot scales that canvas by 0.133, so
  the smallest label prints at 2.65 pt and the body text at 4.54 pt.
- The asset has almost no reclaimable margin: its ink covers 335 x 230 pt of the
  canvas, so a tight crop reaches only about 4.9 pt. The body text needs a slot
  about 64 mm wide to reach 6 pt, and the smallest label needs about 109 mm,
  which is more than half the figure width.
- Three remedies exist and each is an authoring decision, not a build decision.
  Widen the slot and re-lay out the top row of Figure 4. Ask the collaborator for
  a schematic set at publication size. Or obtain explicit permission to raise the
  font sizes inside the vendored SVG. The third is an edit to collaborator
  content and is therefore not made here.
- The non-flagellated prediction, old panel 3F, now Figure 5B and 5C. Yann Dufour
  asked for a prediction for non-flagellated cells and for the gain expressed
  relative to non-motile cells. Michael Jahn called the idea good but not
  feasible: purely drifting cells reach no substrate, so he expected no feasible
  positive-growth solution, and he reported the simulation unstable below about
  0.5% flagellar mass fraction. That reason no longer holds. The model solves at
  exactly 0% flagellar allocation on the remote IPOPT route: alpha_Fla is 0, the
  dynamic objective ends at a growth rate of 1.0634 1/h, and the travelled
  distance stays at 8500 um, so the cell never reaches the substrate. Reaching
  no substrate does not make the problem infeasible. The cell grows on what is
  already there. The run is in `build/statistics/Figure_5/A3/`. The 0% step is
  also the robust one. With alpha_Fla fixed at 0 the cell cannot swim, the
  substrate stays at its initial 0.0911 mM, and the dynamic problem collapses
  onto a fixed-substrate steady state. An independent steady-state solve gives
  1.0627 1/h against the dynamic plateau of 1.0634 1/h, a gap of 0.069%. The
  baseline therefore does not depend on which local optimum the solver found.
  **This is now done for Figure 5B.** Marc approved the extension on 14 August 2026. The panel
  draws the 0% trajectory as a dashed grey reference beside the 0.5–5% family,
  and the legend states the gain: 56% to 66% in growth rate at 8 h, 8.3-fold to
  35.5-fold in compounded biomass. Figure 5C was not extended, and its 0.5–5%
  allocation axis is unchanged. What is still not drawn is any curve through the
  interior of the 0–1% interval; the reason is the solver scatter recorded
  above, not a missing run.

## Deliberately deferred

- Manuscript DOCX renumbering, Results edits and cross-reference replacement are
  deferred to the manuscript-editing wave.
- Git staging, commits, pushes and external deposition are not authorized.

## Scientifically inadvisable

- No scale bar is estimated from apparent cell size.
- No model prediction was forced at zero flagellar allocation. The solver
  reaches 0% on its own, and Figure 5B now draws that solved trajectory. The
  interior of the 0–1% interval is still not drawn: every step solves, but the
  solutions scatter across local optima, and no value there is smoothed or
  interpolated.
- No inference treats pooled wells, cells or trajectories as biological repeats.
- No plate-reader distribution is described as evidence of single-cell
  bimodality.
- No chemotaxis-function conclusion is drawn from protein abundance alone.
