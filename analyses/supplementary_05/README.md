# Supplementary Figure 5 — speed against effective diffusivity

This analysis builds Supplementary Figure 5 and writes panels `S5_A`, `S5_B`
and `S5_C`. It was named `supplementary_06` until 15 August 2026, because it
produced Supplementary Figure 6 before the 12 August 2026 renumbering.
Directory and figure now agree.

S5A-C show the joint distribution of swimming speed and log10 effective
diffusivity for the three phenotype pairs: WT against PproA (A), WT against
PproB (B), and PproA against PproB (C). Each panel puts agarose and liquid side
by side at the full 173 mm supplementary width. These contours were main
Figure 7 panels A-C until the 12 August 2026 revision. A 55 mm main-figure box
could not hold them legibly, so the PI moved them here.

## Design

The two phenotypes of a pair differ in kind, not in shade. The first is a filled
translucent band, the second is an outline, and each keeps its palette colour.
Panel C puts two neighbouring reds against each other, and a fill against a line
stays separable where two line colours do not. Each phenotype carries two
levels, the 50 % and the 95 % highest-density region. A dashed grey line marks
D_eff = 1.

Each medium occupies a 2x2 sub-grid: the main axes, a speed marginal above it
and a log10 D_eff marginal to its right. The marginals repeat the
fill-against-outline distinction, and each marginal is rescaled to a peak of one
because the two phenotypes carry different trajectory counts. They make the
honest point that the horizontal axis carries most of the difference and the
vertical axis carries less.

## Why the contour levels are not tuned

The PI asked whether the contour levels could be optimised to emphasise the
difference between strains. They could, and that is the reason not to.
Tightening the outer level always increases apparent separation, because the
tails are where two clouds overlap most. The level is a free knob that the data
does not constrain, so a tuned level would report the knob and not the
measurement. The 50 % and 95 % masses are fixed in `CONTOUR_MASSES` and are not
retuned.

The measurement also says the second axis carries little. A two-dimensional
linear discriminant beats speed alone by 0 to 1.4 AUC points across the six
panel-medium cells, and log10 D_eff is the weaker axis in all six. Tuning a
contour would decorate the weaker dimension.

## Per-unit centroids, which are the inferential mark

A contour pools 7 213 to 13 874 trajectories, while every test in the manuscript
uses the paired experimental unit. Each axes therefore carries one centroid
marker per phenotype at the mean of its 16 to 18 per-unit centroids in the
(speed, log10 D_eff) plane, with 95 % confidence whiskers on each axis. A unit
centroid is the arithmetic mean of speed and of log10 D_eff over the
trajectories of one `metadata_key`, medium and phenotype.

The whiskers come from a paired-unit bootstrap that draws both phenotypes of a
unit together. `BOOTSTRAP_SEED` and `BOOTSTRAP_ITERATIONS` are imported from the
Figure 7 builder, so the convention is Figure 7's: 10 000 resamples from one
generator seeded at 20260812, walking A, B, C with agarose before liquid.
`centroid_tables` runs that pass once and caches it, so building one panel gives
the same numbers as building all three.

Paired differences, second phenotype minus first, with 95 % intervals:

| panel | medium  | comparison        |  n | d speed (µm/s)         | d log10 D_eff             |
|:------|:--------|:------------------|---:|:-----------------------|:--------------------------|
| A     | agarose | PproA minus WT    | 18 | -5.26 (-6.10, -4.21)   | -0.506 (-0.596, -0.399)   |
| A     | liquid  | PproA minus WT    | 16 | -6.88 (-8.09, -5.68)   | -0.432 (-0.550, -0.328)   |
| B     | agarose | PproB minus WT    | 18 | +5.71 (+3.96, +7.12)   | +0.218 (+0.113, +0.305)   |
| B     | liquid  | PproB minus WT    | 18 | +4.26 (+3.14, +5.38)   | +0.169 (+0.106, +0.233)   |
| C     | agarose | PproB minus PproA | 18 | +9.10 (+7.40, +10.73)  | +0.613 (+0.462, +0.761)   |
| C     | liquid  | PproB minus PproA | 16 | +10.23 (+7.77, +12.27) | +0.492 (+0.315, +0.641)   |

A whisker drawn on the panel is a marginal interval for one phenotype. Two
whiskers may overlap while the paired difference excludes zero, which is why the
paired differences belong in this table and not on the panel face.

## Density grid

The kernel density comes from `scipy.stats.gaussian_kde` with the Scott
bandwidth rule. Figure 7 evaluates that density on a fixed grid that stops at
60 µm/s and log10 D_eff = -1.3, so its 95 % contour runs into the grid edge and
is cut. A contour truncated by the evaluation grid is not a 95 % region.

This module pads the grid by four kernel bandwidths beyond the data on every
side and evaluates 260 x 260 points. Both phenotypes of a medium share one
lattice, so their contours stay directly comparable. The build asserts that the
largest density on any grid border stays below the 95 % level, and it fails if
it does not. The measured margin is at most 1.6e-4 of the 95 % level, so every
contour closes well inside the grid.

## Data

The panels do not re-derive the dataset. `checked_csv`, `load_direct_tracks` and
`PANEL_SPECS` are imported from
`analyses/figure_07_revision/build_figure_07_revision.py`, so this figure
provably plots the same direct-pair trajectories and the same paired-unit filter
as Figure 7. The paired-unit counts are 18 agarose and 16 liquid for A, 18 and
18 for B, and 18 and 16 for C.

## Outputs

Under `build/statistics/Supplementary_Figure_5/<panel>/`:

- `S5_<panel>_contour_grid_audit.csv` — the old grid, the new grid, both levels,
  the border margin and the bounding box of each 95 % contour.
- `S5_<panel>_unit_centroids.csv` — the plotted centroid of each phenotype with
  its bootstrap interval on both axes.
- `S5_<panel>_paired_centroid_differences.csv` — the paired differences of the
  table above.
- `S5_<panel>_caption_sentences.txt` — the caption sentences the panels no
  longer print, emitted verbatim from `CAPTION_SENTENCES`.

## Limitation the figure states in its caption

The contours pool trajectories within a phenotype. They describe the trajectory
distribution, not the between-experiment uncertainty. The inferential unit is
the paired experiment, and Figure 7D carries that inference. This sentence used
to print under every panel. It now belongs to the figure caption, because it
states one fact about the whole figure and three copies of it cost three lines
of panel height that the marginals need. The statement itself must survive: it
is the honesty that justifies the figure being supplementary. The build writes
the exact wording to `S5_<panel>_caption_sentences.txt`, so the legend and the
code cannot drift apart.

Status remains `partial_reproduction`: the run starts from migrated direct-pair
track and paired-unit tables, not from raw tracking acquisitions.

Run all panels:
`PYTHONPATH=$PWD/src MPLBACKEND=Agg .venv/bin/python analyses/supplementary_05/build_supplementary_05.py --panel all`.
