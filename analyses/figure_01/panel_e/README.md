# F1_E — Ptet hook–filament relationship

Canonical legacy source: `Figure1/Figure1D_hook-filament-count_Ptet`.

Scientific question: how closely do hook and completed-filament counts covary within induced `PtetA-flhDC` cells? The entry point reads 18,873 processed cells from three biological replicates, regenerates all 51 bubble counts, recomputes Spearman rho and the exact 27 replicate-bootstrap combinations, verifies them against the archived tables, and renders the current cropped presentation without the legacy title/footer. Cells determine bubble frequencies and the correlation; replicate resampling supplies the 95% interval. The migrated input is already filtered, so upstream segmentation filters and exclusions remain unresolved. Checksums and row counts are in `../migration_inventory.csv` and `config/config.json`.

Run from the collection root:

```bash
.venv/bin/python3.12 -m analyses.figure_01.panel_e.scripts.plot
```

The 51 exact plotted bubble marks and the correlation/interval statistics are
also written to `data/source_data/figure_01/F1_E_bubble_counts.csv` and
`F1_E_statistics.csv`. Figure outputs are written to `build/panels/F1_E`; no
output in `expected/` is approved yet. This is a processed-table-to-panel
reproduction; raw microscopy segmentation and final multi-panel assembly
remain outstanding.
