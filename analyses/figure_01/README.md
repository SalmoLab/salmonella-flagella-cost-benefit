# Figure 1 migration status

This directory contains the current-numbering Figure 1 migration. It does not depend on `manuscript_plots_final` at runtime; the legacy paths and byte-identical table copies are recorded in `migration_inventory.csv`.

## Reproduce available quantitative panels

Run from `manuscript_reproducible/` with the pinned Python 3.12 environment:

```bash
.venv/bin/python3.12 -m analyses.figure_01.panel_c.scripts.plot
.venv/bin/python3.12 -m analyses.figure_01.panel_d.scripts.plot
.venv/bin/python3.12 -m analyses.figure_01.panel_e.scripts.plot
.venv/bin/python3.12 -m analyses.figure_01.panel_h.scripts.plot
```

Each command validates input row counts, recomputes the statistical result represented by the panel, checks it against the archived result, and writes SVG/PDF/PNG and generated statistical tables under `build/panels/`. Checksum-bearing provenance is written both to the panel's `metadata/` directory and the audit tree at `metadata/provenance/figure_01/`.

## Current status

| Panel | Status | Reproduction boundary |
|---|---|---|
| F1_A | blocked asset | Editable schematic source and export recipe absent |
| F1_B | blocked asset | Raw microscopy, FOV selection, processing and calibration absent |
| F1_C | partial, rerunnable | Processed cells → statistics and standalone plot |
| F1_D | partial, rerunnable | Processed cells → statistics and standalone plot |
| F1_E | partial, rerunnable | Processed cells → bubble counts, Spearman result and standalone plot |
| F1_F | blocked asset | Editable schematic source and export recipe absent |
| F1_G | blocked asset | Raw microscopy, FOV selection, processing and calibration absent |
| F1_H | partial, rerunnable | Histogram counts → statistics and standalone plot |

The four quantitative panels are not yet full raw-data-to-final-figure reproductions. Figure assembly, visual regression, and raw microscopy/segmentation lineage remain open.

The archived tables state the anhydrotetracycline dose in the wrong unit. `plotting.py` restates it as ng/mL, the unit Marc Erhardt confirmed on 15 August 2026, as each table enters the build. The dose numbers are unchanged, and the archived copies under `data/processed/figure_01/` keep the old strings so they stay byte-identical to the legacy bundle. See the "One corrected unit" section of `docs/SOURCE_DATA_DICTIONARY.md`.

`migrate_legacy_tables.py` is read-only by default. `--write` is required to re-copy the selected source tables and update the migration inventory.
