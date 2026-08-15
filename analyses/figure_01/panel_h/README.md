# F1_H — Ppro hook count

Canonical legacy source: `Figure2/Figure2E_hook-count_Ppro`.

Scientific question: how does synthetic `Ppro-flhDC` promoter strength change hook number per cell? The entry point reads the 162-row replicate histogram table representing 41,661 cells and 15 biological-replicate means, recomputes Welch tests with Benjamini–Hochberg correction, verifies the archived statistics, and renders the current discrete count panel as pure vector SVG plus PDF and PNG. `replicate_id` is the biological unit (three replicates per strain); reconstructed cells are descriptive observations, with mean and SD calculated across replicate means. Workbook parsing/filtering is upstream and is not yet canonical. Checksums and row counts are in `../migration_inventory.csv` and `config/config.json`.

Run from the collection root:

```bash
.venv/bin/python3.12 -m analyses.figure_01.panel_h.scripts.plot
```

Every histogram-frequency mark, every plotted replicate-mean marker, and the
exact statistics are also written to `data/source_data/figure_01/` as
`F1_H_distribution.csv`, `F1_H_replicate_means.csv`, and
`F1_H_statistics.csv`. Figure outputs are written to `build/panels/F1_H`; no
output in `expected/` is approved yet. This is a processed-table-to-panel
reproduction. The archived Excel workbook and its table-extraction step have
not yet been migrated into the canonical raw-data workflow.
