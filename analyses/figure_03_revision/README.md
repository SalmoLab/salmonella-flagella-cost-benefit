# Revised Figure 3

This directory contains the confirmed mapping from former Figure 2D-H to
Figure 3A-E. Panel A remains an explicit blocked asset; panels B-E are
deterministic Python entry points.

Every panel renders at the exact size of its slot in `config/assembly_figure_03.yaml`,
through `flagella_repro.theme.panel_figsize("Figure_3", label)`. The assembler then
scales the panel by 1.0, so a point size requested from the theme is the same point
size on the printed page. No panel config carries its own figure size.

The experimental growth panels normalize each independent experiment to its
same-day or same-replicate reference. Technical wells and individual tracked
cells remain descriptive source data and are not treated as inferential units.
