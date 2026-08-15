# Revised Figure 6 — soft-agar motility and competition

Core conclusion: promoter-controlled flagellar abundance changes soft-agar expansion and spatial sorting during direct competition.

The figure is an asymmetric mixed-modality figure built exclusively in Python. Panels A and B show independent repeat units as points with mean and 95% t confidence interval; no significance stars or replicate bars are used. Panel C shows cell-level hook-count distributions with the median (white point) and interquartile range (black line) defined explicitly. Panel D is a deterministic, editable reconstruction of the supplied competition-design PPTX; its source checksum is fixed in the builder. Panel E plots per-cell hook-count frequency curves beneath four explicit microscopy placeholders.

Panel E is not image-complete. The source package lacks the original four calibrated microscopy fields, crop coordinates and pixel-to-length calibration. The code therefore does not manufacture a scale bar from the July composite. Replace each placeholder only after checksum-frozen raw fields and calibration metadata are supplied.

Run:

```text
.venv/bin/python analyses/figure_06_revision/build_figure_06_revision.py --check
.venv/bin/python analyses/figure_06_revision/build_figure_06_revision.py
```

Canonical graphics are written to `build/panels/Figure_6/<panel>/`; source data and statistics are mirrored under `build/source_data/Figure_6/` and `build/statistics/Figure_6/`.
