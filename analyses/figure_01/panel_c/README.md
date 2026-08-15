# F1_C — Ptet hook count

Canonical legacy source: `Figure1/Figure1C_hook-count_Ptet`.

Scientific question: how does induction of `PtetA-flhDC` change hook number per cell? The entry point reads 23,046 processed per-cell values and 21 biological-replicate means, recomputes Welch tests with Benjamini–Hochberg correction, verifies the archived statistics, and renders the current discrete count representation as pure vector SVG plus PDF and PNG. `replicate_id` is the biological unit (three replicates per condition); individual cells are descriptive observations, with the mean and SD calculated across replicate means. The migrated input is already filtered, so upstream segmentation filters and exclusions remain unresolved. File checksums, units and row counts are recorded in `../migration_inventory.csv` and `config/config.json`.

Run from the collection root:

```bash
.venv/bin/python3.12 -m analyses.figure_01.panel_c.scripts.plot
```

Every distribution observation and every plotted replicate-mean marker are
written to `build/source_data/Figure_1/C/` as `F1_C_distribution.csv` and
`F1_C_replicate_means.csv`. The exact statistics go to
`build/statistics/Figure_1/C/F1_C_statistics.csv`. Figure outputs are written to
`build/panels/Figure_1/C`; no output in `expected/` is approved yet. This is a processed-table-to-panel
reproduction. Raw microscopy segmentation inputs still block a full provenance
pass.

The archived tables state the anhydrotetracycline dose in the wrong unit. The
builder restates it as ng/mL, the unit Marc Erhardt confirmed on 15 August 2026.
The dose numbers are unchanged. See the "One corrected unit" section of
`docs/SOURCE_DATA_DICTIONARY.md`.
