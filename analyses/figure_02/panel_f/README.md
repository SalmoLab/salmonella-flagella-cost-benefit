# F2_F — assembly-mutant single-cell growth

This partial reproduction rebuilds current Figure 2F from the processed
mother-machine table in legacy bundle
`Figure3/Figure3D_growth-rate_assembly-mutants_single-cell`, which maps to the
renumbered current Figure 2F. It does not claim raw-to-final reproduction.

The read-only legacy CSV has SHA-256
`1ba51a1c9815daa9f427554fd6ab07733734c9000ba05a2e3cc2cc2494a0ff84`
and 334,160 rows. `scripts/migrate.py` reads it in chunks and selects
`_subset=all_cells`, `_window_start_min=200`, and `_window_end_min=800`. The
result contains 110,983 cells. The 129,101,403-byte legacy source remains
outside the collection; deterministic Parquet and gzip-compressed current-panel
extracts are checksum-addressed in `metadata/migration_inventory.json`.

The biological unit is an independent experiment (`replicate`, R1 or R2 per
strain); tracked cells are observational units within experiments. The violin
geometry describes per-cell `growth_rate_per_h` (h^-1), its internal box
summarises the cell distribution, and grey points are biological-replicate
means. There is no inferential test or multiplicity correction in this panel.
No rows other than the declared subset/time-window selection are excluded.

Run from the collection root:

```text
.venv/bin/python3.12 -m analyses.figure_02.panel_f.scripts.migrate
.venv/bin/python3.12 -m analyses.figure_02.panel_f.scripts.plot
```

Use `--write` on migration only to rebuild from the checksum-identified legacy
table. Outputs are `data/processed/figure_02/F2_F/`,
`data/source_data/figure_02/F2_F.csv.gz`, `build/panels/F2_F/`, and panel-local
plus central provenance JSON files.

Status: `partial_reproduction`. Raw microscopy, tracking inputs and the
image-to-cell extraction workflow remain absent; final composite assembly and
pixel-level regression are not part of this panel target yet.
