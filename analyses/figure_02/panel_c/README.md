# F2_C — Ppro single-cell growth distributions

This partial reproduction rebuilds current Figure 2C from the processed
mother-machine cell table archived in legacy bundle
`Figure2/Figure2B_growth-rate_Ppro_single-cell`. It does not claim to reproduce
the missing raw-image-to-track pipeline.

The read-only legacy CSV has SHA-256
`6f4b48f0380ec2482f50febefb42423caf0aa101a86c228b835baf52c304101d`
and 385,802 rows. `scripts/migrate.py` reads it in chunks and selects
`_subset=all_cells`, `_window_start_min=200`, and `_window_end_min=800`. The
result contains 126,934 cells. Because the source is 133,835,554 bytes and Git
LFS is unavailable, the canonical collection stores a deterministic Parquet
subset and a deterministic gzip-compressed source-data CSV; the migration
inventory records checksums for both and for the external legacy input.

The biological unit is an independent experiment (`replicate`, R1 or R2 per
strain); tracked cells are observational units within those experiments. The
violin geometry describes per-cell `growth_rate_per_h` (h^-1), its internal box
summarises the cell distribution, and grey points are biological-replicate
means. There is no inferential test or multiplicity correction in this panel.
No rows other than the declared subset/time-window selection are excluded.

Run from the collection root:

```text
.venv/bin/python3.12 -m analyses.figure_02.panel_c.scripts.migrate
.venv/bin/python3.12 -m analyses.figure_02.panel_c.scripts.plot
```

Use `--write` on the migration command only to rebuild the compact extraction
from the checksum-identified legacy table. Outputs are
`data/processed/figure_02/F2_C/`,
`data/source_data/figure_02/F2_C.csv.gz`, `build/panels/F2_C/`, and the
panel-local plus central provenance JSON files. The current strain order and
labels are encoded in `config/config.json`.

Status: `partial_reproduction`. Raw microscopy, tracking inputs and the
image-to-cell extraction workflow remain absent; final composite assembly and
pixel-level regression are not part of this panel target yet.
