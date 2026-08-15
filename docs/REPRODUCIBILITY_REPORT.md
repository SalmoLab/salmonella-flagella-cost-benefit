# Reproducibility implementation report

## Scope and release state

This report describes the 12 August 2026 seven-figure revision build. The
authoritative specification is the frozen coauthor prompt
(`reference/2026-08-12-revision/revision_prompt/`, SHA-256
`0ac2c53eac902141a0297e0f244a13ec7f6c973243a7999c35d540c4ffde7591`). The
legend and text baseline is the 21 July merged-coauthor manuscript; the
9 July SVG exports remain the visual-quality baseline. The collection is a
reproducible partial-baseline revision, not yet a complete scientific
reproduction release.

The authoritative panel inventory contains 63 records across seven main and
six supplementary figures:

- 58 `partial_reproduction` workflows that execute from checksum-backed
  canonical inputs;
- 5 `blocked_asset` panels awaiting editable schematics and/or raw microscopy
  assets: Figure 1A, 1B, 1F, 1G and Figure 3A;
- 0 `blocked_external` panels.

No blocked or partial panel is promoted to `reproduced`. The frozen July
images remain the canonical visual targets until each raw-to-panel chain and
visual acceptance gate is complete. The five blocked panels render as
unmistakable placeholders and cannot be reported as reproduced.

## Implemented and verified

- The revision baseline is frozen under `reference/2026-08-12-revision/`
  with the prompt, the merged-coauthor manuscript, its embedded media, the
  July visual references and `BASELINE_EXCEPTION.md`.
- The central provenance tree contains 60 current schema-valid documents with
  zero provenance-validation errors, one canonical producer per panel.
- The artifact registry contains 377 records and the panel-artifact registry
  contains 491 links. The partial-artifact synchronizer registers 356
  generated artifacts and 431 panel links, and verifies them as stable across
  repeated builds.
- `make reproduce-available` executes the 55 available workflows, assembles
  all twelve figures under `build/figures/<figure_name>/`, and reports the
  five asset-blocked panels with `complete: false`.
- All panel outputs use the normalized `build/panels/<figure_name>/<panel_label>/`
  structure. `build/final`, `build/figure_04` and legacy panel-ID directories
  do not exist.
- The partial Source Data workbook
  (`build/source_data/Source_Data_revision_partial.xlsx`) contains 108
  checksum-validated source and statistics tables and is visibly marked
  partial.
- The Figure 7 effective-diffusivity decomposition `D_eff = v²τ/2` closes
  with a maximum log-identity error of 4.1 × 10⁻¹⁶ (tolerance 1 × 10⁻¹²).
  Direct-pair experimental-unit counts are 18/16 (WT/PproA), 18/18
  (WT/PproB) and 18/16 (PproA/PproB) for agarose/liquid.
- Figure 5C reproduces the unique 3% flagellar-allocation optimum under the
  manuscript configuration.
- Figure 7A–C plot the paired experimental unit: one marker per unit, joined
  within each imaging session, annotated with the D ratio and its 95% CI. The
  plotted per-unit mean of ln D_eff is the same aggregation the ratio is built
  from, so the ratio of the plotted groups' geometric means reproduces the
  quoted `D_ratio` to 6.7 × 10⁻¹⁶.
- Panel D shows three rows: the measured speed² ratio, the derived τ ratio and,
  below a thin rule, the D_eff product. The product row is drawn so the reader
  sees the two component bar lengths add to it on the log axis. The statistics
  table carries `D_ratio` and its CI as well.
- Figure 7E–G use the same discrete count-per-cell geometry as Figure 1C, 1D
  and 1H. A kernel density on integer hook counts is not used anywhere.
- The speed/diffusivity probability contours are Supplementary Figure 5. Their
  density grid is padded by four kernel bandwidths per axis, and the build
  asserts that no contour reaches a grid boundary, so a 95% contour encloses
  95% of the data rather than 95% of a truncated grid.
- Figure QA: SVG text is editable and no significance-star text remains. Every
  panel now renders at the exact physical size of its assembly slot, so the
  assembly scale is 1.0 and a declared point size is the printed point size.
  The median panel prints at 7.00 pt. One panel fails the 6 pt rule: Figure 4A,
  the vendored collaborator schematic, at 2.65 pt. See `not_done.md`.
- Every canonical builder takes its colours from `config/palette.yaml` through
  `flagella_repro.theme`; no canonical builder carries a colour literal or its
  own font size. The single typeface is Arial with metric-compatible fallbacks.
- Analysis tasks A1–A9 are documented with methods, inferential units and
  outcomes in `docs/revision_2026-08-12/analysis_report.md`.
- No canonical code contains personal, `/tmp` or `/mnt/data` absolute paths.

## Public-command acceptance

The current command contract behaves deliberately as follows:

| Command | Result | Interpretation |
|---|---:|---|
| `make bootstrap` | pass | Creates the Python 3.12.11 environment from the frozen lock and proves package import. |
| `make inventory` | pass | 60 panels, 377 artifacts, 491 links; zero errors, five asset warnings, no external blockers. |
| `make organize` | pass | Refreshes the normalized panel/figure tree and status manifests for all 60 panels and 12 figures. |
| `make reproduce-available` | pass | Executes the 55 partial workflows and assembles all twelve figure folders. |
| `make source-data-available` | pass | Builds the explicitly partial, checksum-gated workbook (123 tables, plus README, INDEX and DATA_DICTIONARY sheets). |
| `make figure-qa` | expected refusal | Editable-text and star-text checks pass for all 60 panels. The on-page font check fails on Figure 4A alone, at 2.65 pt. |
| `make test` | pass | 73 tests, including registry, provenance, workflow, Source Data, layout, assembly, colour-vision and on-page font-size coverage. |
| `make reproduce` | expected refusal | Fails before execution and names exactly the five blocked assets (F1_A, F1_B, F1_F, F1_G, F3_A) plus the honest partial list. |
| `make audit` | expected refusal | All 63 provenance records validate; only the five asset-only panels lack regenerated canonical outputs. |
| `make clean-room` | expected refusal | Reports the same partial/raw/asset gates rather than claiming a complete release. |

## Remaining release blockers

1. Recover the five blocked visual assets and their raw acquisition,
   processing, crop, calibration and editable-source metadata
   (Figure 1A, 1B, 1F, 1G; Figure 3A). Figure 6 microscopy regions also
   need calibrated original fields and the intended scale-bar length.
2. Obtain the promoter-series raw MS files, FASTA and Spectronaut
   project/settings to extend the accepted protein-level workflow back to raw
   spectra.
3. Reproduce the cell-economy solve with the collaborator's exact
   APMonitor/IPOPT runtime or a scientifically reviewed port. The 0–1%
   allocation sweep harness records `blocked_exact_solver_unavailable` for
   every step; the demonstrated dynamic-model domain remains 0.5–5%.
4. Replace remaining migrated processed-input starts with complete
   raw-to-processed chains, including raw motility parameter fitting.
5. Visually accept all twelve assembled figures, then promote canonical
   artifact IDs only after numerical and visual regression gates pass.
6. Decide how Figure 4A reaches the 6 pt floor. The vendored collaborator
   schematic cannot be fixed inside this collection; the options are a wider
   slot, a replacement asset, or permission to edit the vendored typography.
7. Add real repository accessions, licences and DOI-bearing release
   locations; complete the Data and Code Availability statements.
8. Run the Docker clean-room build in CI or on a Docker-capable host; the
   local Python CairoSVG renderer remains blocked by an x86_64-only Cairo
   library.

The strict release gate remains: network-disabled reproduction of all 63
panels and twelve final figures using only collection-contained or
checksum-fetched inputs, followed by a zero-error audit.
