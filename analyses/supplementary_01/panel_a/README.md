# S1_A — normalized growth, 200–800 min

This panel uses `growth_norm` from the processed single-cell table archived in
the main Figure 2B legacy bundle, not the stale named supplement bundle. The
legacy input has SHA-256
`6f4b48f0380ec2482f50febefb42423caf0aa101a86c228b835baf52c304101d`.
The checksum-backed migration selects `mother_only` and `non_mother` rows in the
200–800 min window and yields 126,934 observations.

Independent experiment (`replicate`, R1/R2) is the biological unit; tracked
cells are observational units. Each violin describes every per-cell normalized
growth value, and the black bar is the cell-level mean shown in the July
reference. The dashed reference is 1.0. No inferential test or multiplicity
correction is shown. No rows beyond the declared subset/window filter are
excluded.

Run from the collection root:

```text
.venv/bin/python3.12 -m analyses.supplementary_01.panel_a.scripts.migrate
.venv/bin/python3.12 -m analyses.supplementary_01.panel_a.scripts.plot
```

Use migration `--write` only to rebuild the extraction. Canonical outputs are
`data/processed/supplementary_01/S1_A/`,
`data/source_data/supplementary_01/S1_A.csv.gz`, `build/panels/S1_A/`, and the
panel-local plus central provenance records. Status: `partial_reproduction`;
the raw image-to-track and normalization lineage remains absent.
