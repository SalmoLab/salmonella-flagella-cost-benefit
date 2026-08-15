# Supplementary Figure 5 inputs

| Canonical input | Origin |
|---|---|
| `data/processed/figure_07_revision/direct_pair_track_measurements.csv.gz` | Migrated direct-pair trajectory table; checksum pinned in the Figure 7 builder |
| `data/processed/figure_07_revision/paired_experimental_unit_measurements.csv` | Migrated paired experimental-unit table; supplies the reciprocal-label metadata keys |
| `analyses/figure_07_revision/build_figure_07_revision.py` | Supplies `checked_csv`, `load_direct_tracks` and `PANEL_SPECS`; imported, never modified |

The two tables are read through `checked_csv`, which refuses a file whose SHA-256 does not match the pinned value. No raw tracking acquisition is an input, which is why the panel status stays `partial_reproduction`.
