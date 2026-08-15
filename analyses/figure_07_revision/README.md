# Revised Figure 7 — single-cell swimming behaviour

Core conclusion: flagellar abundance changes effective diffusivity, and effective diffusivity is a composite—not independent—quantity.

Panels A–C use only direct, reciprocal-label competition experiments. Each marker is one paired experimental unit, grouped by medium (agarose, liquid). A thin line joins the two phenotypes measured in the same `metadata_key`; the lines never pair individual trajectories. The plotted value is the per-unit mean of `ln D_eff`, shown as `log10`. That is the same aggregation the panel D decomposition uses, so the ratio of the two groups' geometric means equals the annotated D ratio exactly; the builder asserts this to a relative tolerance of 1e-12. Each panel states the D ratio with its 95 % bootstrap CI, the number of paired units, the violin summary, and the `D_eff = 1 µm²/s` reference line.

The speed-versus-diffusivity probability contours moved to a supplementary figure. `hdr_levels` stays in this module because the supplementary builder imports it together with `checked_csv`, `load_direct_tracks` and `PANEL_SPECS`.

Panel D verifies the exact two-dimensional relation used by the analysis, `D_eff = v² τ / 2`, and decomposes paired-unit log contrasts using 10,000 bootstrap resamples with seed `20260812`. Here `τ = 2 D_eff / v²` is a derived persistence-equivalent timescale, not an independently measured persistence observable. Panel D plots only the speed² and τ rows: panels A–C already state the D ratio. The written table `Figure_7D_effective_diffusivity_decomposition.csv` still carries `D_ratio` and its CI, because A–C annotate it and the Source Data must contain it.

Panels E–G show cell-level hook counts with the `discrete_count` geometry of Figure 1 panels C, D and H: one mark per observed integer whose half-width follows the square root of its frequency, individual dots where a count is carried by 12 cells or fewer, grey markers for the six independent day replicates, and a black bar at the mean of the replicate means. Hook count is an integer, so a kernel density would smear the zero class. The hook axis is clipped at each panel's maximum, never above 20 hooks per cell; the panel key names the cells above the clip and `Figure_7{E,F,G}_numeric_audit.csv` counts them.

Run:

```text
.venv/bin/python analyses/figure_07_revision/build_figure_07_revision.py --check
.venv/bin/python analyses/figure_07_revision/build_figure_07_revision.py
```

Canonical graphics are written to `build/panels/Figure_7/<panel>/`; source data and statistics are mirrored under `build/source_data/Figure_7/` and `build/statistics/Figure_7/`.

`build_candidates.py` is the historical side-by-side of the two replacements for the pairwise enrichment maps. The PI chose the paired-unit design at final size, and it is now the canonical A–C design.
