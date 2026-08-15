# Figure 2A — Ptet population growth

The input contains 420 technical growth curves across six experiment days.
The plot shows technical curves, day-level means, and the mean of biological
days with a seeded bootstrap 95% interval. Paired two-sided t-tests compare
each induction condition to WT; Benjamini–Hochberg correction is applied within
the panel.

Biological unit: experiment day. Technical unit: plate-reader growth curve.
Legacy identifier: `Figure3/Growth rate Ptet_population_final`.

Run: `.venv/bin/python analyses/figure_02/panel_a/scripts/plot.py`.

Limitation: the canonical run currently begins with the migrated fitted-curve
table. Raw workbook-to-fit processing and July assembly/cropping remain open.

