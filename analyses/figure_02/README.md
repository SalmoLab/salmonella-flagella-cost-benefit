# Figure 2 migration status

Figure 2A, 2B and 2E have deterministic partial reproductions from the fitted
growth-rate tables preserved in the legacy bundle. They recompute day-level
means, paired statistics, source-data rows and standalone vector/raster panels.

These are not full raw-to-final reproductions: the canonical plate-reader
workbook analysis and the July composite assembly/crop still need migration and
visual acceptance. Figure 2C/F and Supplementary Figure S1 require the large
single-cell tables plus their upstream tracking lineage. Figure 2D requires its
editable schematic. Figure 2G/H remain blocked on the final model sources.

Run the available population panels from the collection root:

```bash
.venv/bin/python analyses/figure_02/panel_a/scripts/plot.py
.venv/bin/python analyses/figure_02/panel_b/scripts/plot.py
.venv/bin/python analyses/figure_02/panel_e/scripts/plot.py
```

