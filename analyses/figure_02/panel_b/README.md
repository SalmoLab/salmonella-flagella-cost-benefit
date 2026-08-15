# Figure 2B — Ppro population growth

The input contains fitted technical plate-reader curves. Growth rates are
converted from per-minute fits to 1/h, then summarized by experiment day.
Paired two-sided t-tests compare each promoter strain to WT with
Benjamini–Hochberg correction within the panel.

Biological unit: experiment day. Technical unit: plate-reader growth curve.
Legacy identifier: `Figure2/Figure2A_growth-rate_Ppro_population`.

Run: `.venv/bin/python analyses/figure_02/panel_b/scripts/plot.py`.

Limitation: the canonical run currently begins with the migrated fitted-curve
table. Raw workbook-to-fit processing and July assembly/cropping remain open.

