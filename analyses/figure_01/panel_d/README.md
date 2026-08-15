# F1_D — Ptet filament count

Canonical legacy source: `Figure1/Figure1C_flagella-count_Ptet`.

Scientific question: how does induction of `PtetA-flhDC` change filament number per cell? The entry point reads 23,046 processed per-cell values and 21 biological-replicate means, recomputes Welch tests with Benjamini–Hochberg correction, verifies the archived statistics, and renders the current violin representation with the current `Filament count` terminology. `replicate_id` is the biological unit (three replicates per condition); individual cells are descriptive observations, with mean and SD evaluated across replicate means. The migrated input is already filtered, so upstream segmentation filters and exclusions remain unresolved. File checksums, units and row counts are recorded in `../migration_inventory.csv` and `config/config.json`.

Run from the collection root:

```bash
.venv/bin/python3.12 -m analyses.figure_01.panel_d.scripts.plot
```

Every observation driving the violin density and every plotted replicate-mean
marker are written to `build/source_data/Figure_1/D/` as
`F1_D_distribution.csv` and `F1_D_replicate_means.csv`. The exact statistics go
to `build/statistics/Figure_1/D/F1_D_statistics.csv`. Figure outputs are
written to `build/panels/Figure_1/D`; no output in `expected/` is approved yet. This
remains partial because raw microscopy segmentation inputs are not migrated and
the legacy `Flagella count` versus current `Filament count` terminology
requires confirmation.

The archived tables state the anhydrotetracycline dose in the wrong unit. The
builder restates it as ng/mL, the unit Marc Erhardt confirmed on 15 August 2026.
The dose numbers are unchanged. See the "One corrected unit" section of
`docs/SOURCE_DATA_DICTIONARY.md`.
