# Figure contracts for the 2026-08-12 revision release

## Manuscript-level evidence chain

Core conclusion: tuning flagellar abundance creates a measurable growth cost but
can maximize fitness in structured nutrient environments through a balance of
proteome allocation, biosynthetic/rotational cost and access to substrate.

Backend: Python 3.12 exclusively for analysis, plotting, preview rendering,
assembly and visual QA.

Export contract: editable SVG and PDF, 300-dpi PNG review render, explicit panel
dimensions and placement, checksum-linked source data and statistics, and no
post-assembly manual edits. A TIFF export can be added if required by the target
journal at submission.

## Main figures

| Figure | Core conclusion | Archetype | Evidence hierarchy | Outstanding reviewer risks |
|---|---|---|---|---|
| 1 | The inducible systems tune hook/filament number across a controlled range. | Schematic-led image-plus-quantification composite | System design and representative images support quantitative hook/filament distributions and correlation. | Editable schematics, raw microscopy/FOV selection, segmentation lineage, scale calibration, AnTc unit discrepancy and “flagella” versus “filament” terminology. |
| 2 | Tunable flagellar investment has a growth cost in population and single-cell assays. | Quantitative grid | Same-day-WT-normalized population series and replicate-aware mother-machine measurements. | Missing WT(S171) mother-machine data and absent Ptet single-cell heterogeneity data. |
| 3 | Assembly and rotation contribute differently to the measured growth cost. | Asymmetric mixed-modality figure | Mutant population/single-cell measurements lead; static model partitions the cost. | Editable mutant schematic and unresolved assay-context disagreement. |
| 4 | Flagellar allocation reorganizes multiple proteome sectors and can be compared with cell-economy predictions. | Schematic-led quantitative composite | Editable model schematic, replicate proteomics, protein composition, model sweep and growth association. | Raw MS/Spectronaut chain and exact local solver runtime. |
| 5 | Motility benefit saturates and produces an intermediate predicted optimum. | Quantitative/model grid | Gradient model and biomass optimum lead; active-particle seed distributions add movement predictions. | Low-allocation solver domain and missing raw parameter-fitting inputs. |
| 6 | Flagellar number alters soft-agar motility and spatial competition. | Image-plus-quantification composite | Motility and spatial hook distributions support the competition design. | Original calibrated image fields and scale bars. |
| 7 | Direct-pair motility differences and hook-number distributions explain swimming phenotypes without treating derived quantities as independent. | Quantitative grid | Paired-unit effective diffusivity and its speed²/derived-τ decomposition lead; discrete day-aware hook counts support. Pooled-trajectory contours are Supplementary Figure S5. | Raw trajectory-to-summary pipeline remains partial. |

## Supplementary figures

| Figure | Role | Source-data requirement | Outstanding risk |
|---|---|---|---|
| S1 | Time-window robustness for Ppro single-cell growth. | Every `growth_norm` mark for the two exact mother/non-mother windows. | Large table handling and upstream tracking lineage. |
| S2 | Protein-level view underlying proteome-sector claims. | Protein × strain × replicate abundance and annotation/sector mapping. | Final promoter-series package absent; resolve Tsr/Tst label. |
| S3 | Static-model growth curve with experimental overlay. | Model sweep and exact strain-to-mass-fraction mapping. | Final model source and parameterization absent. |
| S4 | Pairwise motility metrics across liquid and agarose conditions. | Paired block-level values for all 12 panels. | Upstream raw trajectories and replicate/exclusion definitions. |
| S5 | Deterministic illustrative movement simulations. | Full trajectories, obstacle fields, calibration table and all seeds. | Calibration begins from a legacy summary; final assembly/visual acceptance. |
| S6 | Speed against effective-diffusivity probability contours, moved out of main Figure 7 to full width. | The direct-pair trajectory table and the paired-unit table that Figure 7 uses, plus the per-panel contour grid audit. | New in this revision, so no frozen 9 July reference exists to accept against; the raw trajectory-to-summary pipeline remains partial. |

## Typography and panel geometry

Every panel renders at the exact physical size of its slot in the figure
assembly. Builders take that size from `flagella_repro.theme.panel_figsize`,
which reads the slot from `config/assembly_*.yaml`. The assembly configuration
is therefore the single source of panel size; a builder must not carry its own
`figure_size_inches`.

This rule exists because the assembler places a panel with
`scale = min(box / viewBox)`. A panel drawn on a canvas larger than its slot is
shrunk, and its text shrinks with it. Rendering at slot size holds that scale at
1.0, so a point size requested in a builder is the same point size on the
printed page.

| Property | Value | Source |
|---|---|---|
| Typeface | Arial, falling back to Helvetica, Nimbus Sans, Liberation Sans | `theme.apply_publication_style` |
| Body, axis label, title | 8 pt | `theme.BASE_FONT_PT` |
| Tick label, legend | 7 pt | `theme.TICK_FONT_PT` |
| Minimum on-page size | 6 pt | `theme.MINIMUM_ON_PAGE_FONT_PT` |
| Figure width | 180 mm double column, 88 mm single column | `theme.DOUBLE_COLUMN_MM` |
| Outer page margin | 3.5 mm left and right | `config/assembly_*.yaml` |

The fallback typefaces are metrically compatible with Arial, so a host that
lacks Arial substitutes a face of identical widths and no label moves.

Nature Communications states both column widths: "A single column width measures
88 mm and a double column width measures 180 mm." The artwork guide for the
Nature branded research journals repeats them as "1-column width: 88 mm" and
"2-column width: 180 mm". Both pages were read on 14 August 2026. Every figure in
this collection is double column.

The collection declared 183 mm until 14 August 2026. The 3 mm came out of the two
outer margins, which fell from 5.0 mm to 3.5 mm. Every panel box and every
inter-panel gutter kept its size, so no panel re-rendered at a new scale and no
on-page font size moved. Take any future width change out of the margins and the
gutters for the same reason. A uniform rescale is the wrong tool: it shrinks
every panel, and the smallest type falls below the 6 pt floor.

`make figure-qa` enforces the minimum by computing the on-page size as
`declared_pt * assembly_scale * 72 / 25.4` and failing on any panel below the
threshold. A check against the size declared inside a panel file is not
sufficient and must not be reintroduced: it passes while the assembled page is
unreadable.

## Completion rule

A panel can be labelled `reproduced` only when its declared raw input or stable
repository record, deterministic analysis, every-mark source-data table,
statistics, panel output, provenance and final assembly placement all pass. Runs
that begin from migrated processed tables remain `partial_reproduction`, even
when their numerical and standalone visual outputs are deterministic.
