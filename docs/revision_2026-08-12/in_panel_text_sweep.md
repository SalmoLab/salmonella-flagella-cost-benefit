# In-panel text sweep — every text block in 60 panels, sorted for decision

Compiled 2026-08-14 from the built panel SVGs in `build/panels/`.
Sources read: 61 SVG files (60 manuscript panels plus one diagnostic),
`docs/revision_2026-08-12/legends.md`,
`docs/revision_2026-08-12/panel_map_revision_2026-08-12.csv`, and
`/Users/marc/Documents/Work/Projects/2026_flagella-numbers_fitness-MSU/manuscript/20260812_Coauthor_feedback_summary_figure-worklist.docx`.

This document changes nothing. It lists what is there, says what it answers, and
prices what deletion would buy.

## 1  Method and scope

I extracted every `<text>` and `<tspan>` element from all 61 panel SVGs. I
excluded axis tick labels, axis titles and panel letters, because those are
structural. That left 314 raw text groups. I merged them into 84 decision rows:
one row per distinct annotation type per panel, with a repeat count.

Panel SVG coordinates are PostScript points. One panel point equals one page
millimetre times 2.8346, so panel positions map to page millimetres directly. I
read the axes bounding box out of each SVG. Text inside that box costs plot
area but no page height. Text outside it costs page height.

### Categories

| Category | Definition | Default |
|---|---|---|
| KEY | Defines what a mark means. The legend of the graphic. | KEEP |
| SUBSTITUTE | Stands in for a graphic, repeats the figure, or explains a result. | CANDIDATE FOR DELETION |
| PLACEHOLDER | Names a missing asset. Neither KEY nor SUBSTITUTE. | KEEP until the asset arrives |
| ATTRIBUTION | Names an author inside the artwork. | Decide separately |

PLACEHOLDER and ATTRIBUTION are the third and fourth categories the brief asked
me to flag. See §6.

### Counts

| Category | Decision rows | Prints on the page |
|---|---:|---:|
| KEY | 48 | 76 |
| SUBSTITUTE | 25 | 71 |
| MIXED (KEY line plus SUBSTITUTE line in one block) | 4 | 14 |
| PLACEHOLDER | 6 | 9 |
| ATTRIBUTION | 1 | 1 |
| **Total** | **84** | **171** |

A row that carries a set of labels, such as the 60 gene names of Supplementary
Figure 2, counts as one print. The count column of each table gives the detail.

## 2  Old-to-new figure mapping

The coauthor worklist uses the 2026-07-21 numbering. I resolved every comment
through `panel_map_revision_2026-08-12.csv`, which carries the legacy panel id
per panel. The mapping is exact for the main figures:

| Worklist panel | Now |
|---|---|
| 1A–1H | Figure 1 A–H, unchanged |
| 2A–2C | Figure 2 A–C |
| 2D–2H | Figure 3 A–E |
| 3A | Figure 4 B and Figure 4 D |
| 3B | Figure 4 C |
| 3C | Figure 4 A, B and E |
| 3D | Figure 4 F |
| 3E–3G | Figure 5 A–C |
| 4A–4E | Figure 6 A–E |
| 5A–5C | Figure 7 A–C, plus Supplementary Figure 3 A–I and Supplementary Figure 5 A–C |
| 5D–5F | Figure 7 E–G |
| old S5 | Figure 5 D and E, promoted to a main figure as Yann asked |

Two warnings on the supplementary mapping.

- Figure 7D is **new**. Its legacy id is `new:A4`. No coauthor comment covers it.
- The current Supplementary Figure 3 is **new** in this revision. It carries
  legacy id `Figure5/Figure5A_motility-competition_agarose-liquid`, that is, it
  was split out of old Figure 5A. The worklist entry "S3 is the model-overlay
  version of main-figure 3D" refers to a *different* S3, which is now folded
  into Figure 4B. The worklist entry "S4 legend — redundant per-panel strain
  enumerations (D/E/F, G/H/I, J/K/L)" names twelve panels; no current
  supplementary figure has that layout. Treat every worklist supplementary
  number as unmapped unless the panel map confirms it.

## 3  Full inventory

Position is given relative to the panel. "inside axes" means the text sits over
the plot; deleting it frees no page height. "header", "footer" and "above axes"
mean the text owns a dedicated strip; deleting it frees page height.

### Figure 1 — 180 × 212 mm (tall, over the 210 mm cap)

| Panel | Text (verbatim) | Reps | Position | Category | Coauthor comment | Recommendation |
|---|---|---:|---|---|---|---|
| A | `EDITABLE EXPERIMENTAL-SYSTEM SCHEMATIC` / `not supplied` | 1 | centre | PLACEHOLDER | — | Keep. It marks a missing asset. |
| B | `RAW REPRESENTATIVE HOOK-LABEL MICROSCOPY FIELD AND CROP METADATA` / `not supplied` | 1 | centre | PLACEHOLDER | — | Keep. |
| C | `2.62±0.55` / `N=4173` and six more pairs | 7 | inside axes, rotated 90° | SUBSTITUTE | **MJ, YD (worklist 1C legend):** "The hook-count values and N values appear in both figure and legend. Michael: remove from the legend if they are in the figure. Yann: put them in the main text instead. Both agree they leave the legend. Michael has already deleted them." | **KEEP.** The coauthors moved these values *into* the figure. Deleting them now reverses a delivered decision. Yann's alternative (main text) is still open; ask him before removing. |
| C | `Cell-count frequency` / `Independent replicate mean` / `Mean of replicate means` | 1 | key, below axes | KEY | **YD (1C):** "State what the dots and the lines represent". **MJ (1C, 1E):** wrote "Small colored dots represent individual cell count. Large grey dots: mean flagella per replicate. Line: global mean over all replicates." **MJ, YD (1C/1D violins):** "Define or remove the central dark-grey lines". | **KEEP.** This block is the answer to three separate requests. |
| D | `2.34±0.78` / `N=4173` and six more pairs | 7 | inside axes, rotated 90° | SUBSTITUTE | as 1C | KEEP, same reasoning. |
| D | `Cell-count frequency` / `Independent replicate mean` / `Mean of replicate means` | 1 | key | KEY | **YD (1D):** "Draw panel D in the same visual style as panels C and H". | KEEP. |
| E | `Cells per bubble` / `10` / `100` / `1000` | 1 | key | KEY | — | KEEP. It is a size key; no graphic replaces it. Values duplicate legend line 21 (§5). |
| F | `EDITABLE CONSTITUTIVE-PROMOTER SCHEMATIC` / `not supplied` | 1 | centre | PLACEHOLDER | **YD, MJ (1H → 1F):** "introduce the Ppro colour code already in the panel F schematic". | Keep. The request cannot be met until the asset arrives. |
| G | `RAW REPRESENTATIVE CONSTITUTIVE-SERIES MICROSCOPY FIELD AND CROP METADATA` / `not supplied` | 1 | centre | PLACEHOLDER | — | Keep. |
| H | `1.99±0.38` / `N=8525` and four more pairs | 5 | inside axes, rotated 90° | SUBSTITUTE | as 1C | KEEP, same reasoning. |
| H | `Cell-count frequency` / `Independent replicate mean` / `Mean of replicate means` | 1 | key | KEY | **YD (1H):** "what the colours represent". | KEEP. |

### Figure 2 — 180 × 72 mm

| Panel | Text | Reps | Position | Category | Coauthor comment | Recommendation |
|---|---|---:|---|---|---|---|
| A | `One growth curve (descriptive)` / `Independent experiment day` / `Mean ± 95% CI` | 1 | key | KEY | **YD (2A):** "Define the lines connecting the dots, or remove them (anchored on the symbol key)". **YD (global, Dispersion):** "State explicitly, in every legend, whether ± denotes SD, SE or a confidence interval." | **KEEP.** `Mean ± 95% CI` is the direct answer to the dispersion request. |
| B | same three lines | 1 | key | KEY | as 2A | KEEP. |
| C | `Cell distribution (descriptive)` / `Independent replicate mean` / `Mean ± 95% CI` | 1 | key | KEY | **YD (2C):** "Remove the interval boxes and lines from the single-cell violin panel." | KEEP. `(descriptive)` is a hedge, not a definition; trim it if you want the shortest key. |

### Figure 3 — 180 × 132 mm

| Panel | Text | Reps | Position | Category | Coauthor comment | Recommendation |
|---|---|---:|---|---|---|---|
| A | `ASSEMBLY-MUTANT SCHEMATIC` / `editable source` / `not supplied` | 1 | centre | PLACEHOLDER | — | Keep. |
| B | `One growth curve (descriptive)` / `Independent experiment day` / `Mean ± 95% CI` | 1 | key | KEY | **YD (global, Dispersion)** | KEEP. |
| C | `Cell distribution (descriptive)` / `Independent replicate mean` / `Mean ± 95% CI` | 1 | key | KEY | **YD (global, Dispersion)** | KEEP. |
| D | `Rotating` / `Non-rotating` | 1 | key, top right | KEY | **MJ (3.4, rotation cost):** the rotating/non-rotating contrast is the model result the reviewers want kept legible. | KEEP. It decodes solid versus dashed. |
| E | `Experiment days` / `Experiment mean ± 95% CI` / `Model (5% mass fraction)` | 1 | key, top left | KEY | **YD (2H) / MJ:** "why a bar plot, be consistent with the other panels" versus "the model predicts a single growth rate with no replicates and no SD". | **KEEP.** The key is how the panel shows data and model side by side without a bar. |

### Figure 4 — 180 × 209 mm (tall, at the 210 mm cap)

| Panel | Text | Reps | Position | Category | Coauthor comment | Recommendation |
|---|---|---:|---|---|---|---|
| A | `Cellular economy model for Salmonella typhimurium` · `Author: Dr. Michael Jahn` (one line, separated by a vertical bar) | 1 | top left, 7 pt grey | ATTRIBUTION | — | **Decide.** This is a byline inside the artwork. Michael is an author of the paper; the author list already credits him. Journals do not print bylines in figures. Ask Michael, then remove. |
| A | `Tra`, `Cbn`, `Aab`, `Rib`, `Oth`, `Etc`, `Fla`, `Lpb`, `cex`, `cin`, `cpre`, `aa`, `lip`, `e` ×5, `all proteins` | 1 (17 labels) | over the schematic | KEY | **MJ (3C reorder):** "the model schematic becomes the new 3A … showing the flow of cellular resources up front helps interpretation". **MJG (baseline):** "introduce the eight-sector division before panels A, B and C". | **KEEP.** These labels are the schematic. |
| B | sector titles `Oth` `Rib` `Cbn` `Aab` `Etc` `Lpb` `Tra` | 1 (7) | subplot headers | KEY | **MJ (3D vs S3):** the model overlay lives here now. | KEEP. |
| B | key: `model`, `model, beyond data`, `replicate`, `condition mean`, `ΔflhDC`, `Ppro1-flhDC`, `PproA-flhDC`, `WT`, `PproB-flhDC`, `PproD-flhDC` | 1 (10) | key, lower right cell | KEY | **YD, MJ (3D + model):** "Overlay a model-predicted curve on the experimental sector data." **MJ (global, Colour):** one colour system, fixed strain colours. | **KEEP.** The key is the only place the reader learns which line is model and which is measurement. |
| C | protein labels `hupA` `tufA` `fusA` `rpsR` … `oppA` | 1 (24) | external labels with leader lines | KEY | **YD, MJ (3B):** "Protein labels are unreadable. They are auto-placed and overflow the small bars; keep only the larger ones, FliC included." **KA (3B):** "The legend inside the bars is not legible." | **KEEP.** The current labels are the delivered fix: 24 external labels with leader lines, FliC named by rule. Deleting them re-opens the complaint. |
| C | sector titles `Oth` `Rib` `Cbn` `Aab` `Etc` `Lpb` `Fla` `Tra` | 1 (8) | subplot headers | KEY | as above | KEEP. |
| D | sector key `Oth` `Rib` `Cbn` `Aab` `Etc` `Lpb` `Fla` `Tra` | 1 (8) | key, above axes | KEY | **MJ (Colours):** "Keep the fixed eight-sector palette". | KEEP. |
| E | same sector key | 1 (8) | key, above axes | KEY | as D | KEEP. Consider one shared key for D and E; that saves a strip without losing meaning. |
| F | key: `model`, `model, beyond data`, `experiment day`, `strain mean`, plus five strain names | 1 (9) | key, above axes | KEY | **YD, MJ (3D + model)** | KEEP. |
| (diagnostic) | `build/diagnostics/Figure_4/` repeats the panel B text | 1 | — | — | — | Not a manuscript panel. Ignore. |

### Figure 5 — 180 × 136 mm

| Panel | Text | Reps | Position | Category | Coauthor comment | Recommendation |
|---|---|---:|---|---|---|---|
| A | `Fixed 3-h glucose gradient` / `Distance travelled by 8 h` / `Endpoint after 8 h` | 1 | key, top left | KEY | **YD, MJ (3E):** "Define the lines and the grey area in the simulated-migration panel. Michael has already written: *Lines: distance travelled. Grey area, substrate concentration in µM.*" | **KEEP, do not touch.** This block *is* the delivered answer, in the panel rather than the legend. Removing it re-opens Yann's question. |
| B | `0%: non-motile`, `0.5%`, `1%`, `2%`, `3%`, `4%`, `5%` | 1 (7) | inline, at each curve end | KEY | **MJ (3.3, the ~3 % optimum):** the message is the inflection point, not the exact number. | **KEEP.** Direct curve labels beat a colour key here. They are the cheapest possible legend. |
| C | — | 0 | — | — | — | Panel carries no annotation. |
| D | `Liquid — calibrated speed and turning` | 1 | header, above axes | MIXED | **YD (S5):** the simulation was promoted to a main figure. No comment asks for the caveat. | **Trim to `Liquid`.** The tail repeats legend lines 160–162. See §5. |
| D | `One seed mean (26 cells)` / `Median of 100 seed means` / `2.5–97.5% simulation interval` | 1 | key, top | KEY | **YD (global, Dispersion)** | KEEP. |
| E | `Agarose-like mesh — calibrated speed and turning` | 1 | header | MIXED | as D | Trim to `Agarose-like mesh`. |
| E | same three key lines | 1 | key | KEY | as D | KEEP. |

### Figure 6 — 180 × 142 mm

| Panel | Text | Reps | Position | Category | Coauthor comment | Recommendation |
|---|---|---:|---|---|---|---|
| A | `Well measurement` / `Day mean (analysis unit)` / `Mean ± 95% CI` | 1 | key | KEY | **YD (global, Dispersion).** **YD / MJ (4A, stars):** the key replaces significance stars with a stated unit and interval. | **KEEP.** It is the neutral answer to the stars conflict. |
| B | `Replicate (analysis unit)` / `Mean ± 95% CI` | 1 | key | KEY | as A | KEEP. |
| C | `0.44±0.95` / `N=257`, `2.66±2.11` / `N=257`, `3.92±2.22` / `N=257` | 3 | inside axes | SUBSTITUTE | **ME (4A legend):** "The reported numbers need checking (*Is this correct?*)." | **DELETE the three `N=257` lines, keep the three mean ± SD lines.** All three positions carry the same n. Printing it three times inside the panel, while the legend states it twice, is the clearest waste in this figure. |
| C | `Cell-count frequency` / `Mean of all cells` | 1 | key | KEY | **YD (1C), applied here for consistency** | KEEP. |
| D | `PproA-flhDC`, `PproB-flhDC`, `combine 1:1`, `mixed population`, `spot on soft agar`, `soft-agar expansion`, `sample the expansion front`, `R1`–`R4`, `quantify strain identity and hooks per cell` | 1 (11) | over the schematic | KEY | — | **KEEP.** This is a workflow schematic. The words are the drawing. |
| E | `Calibrated microscopy field required` | 4 | over each image slot | PLACEHOLDER | **ME (4A):** "Scale bar missing in the example images (baseline comment, still unanswered)." | Keep. It states why no scale bar is drawn. |
| E | `Region 1` … `Region 4` | 1 (4) | subplot headers | KEY | — | KEEP. |
| E | `PproA` / `PproB` / `±1 SD across fields` | 1 | key, bottom | KEY | **YD (global, Dispersion)** | KEEP. |

### Figure 7 — 180 × 222 mm (over every height cap)

| Panel | Text | Reps | Position | Category | Coauthor comment | Recommendation |
|---|---|---:|---|---|---|---|
| A | `D ratio 0.31` / `(0.25-0.40)` and `D ratio 0.37` / `(0.28-0.47)` | 2 | inter-row gap | SUBSTITUTE | **YD (5A):** "The pairwise enrichment maps are hard to read." | **DELETE.** These six numbers are printed a second time in panel D of the same figure (§5, panel-to-panel). |
| B | `D ratio 1.65` / `(1.30-2.02)` and `D ratio 1.48` / `(1.28-1.71)` | 2 | inter-row gap | SUBSTITUTE | as A | DELETE. |
| C | `D ratio 4.10` / `(2.90-5.76)` and `D ratio 3.10` / `(2.07-4.37)` | 2 | inter-row gap | SUBSTITUTE | as A | DELETE. |
| A–C | `Agarose (filled)` / `18 units` and `Liquid (open)` / `16 units` | 6 | header, above upper axes | MIXED | **YD (5A):** medium must be readable. | **Keep `Agarose (filled)` and `Liquid (open)`. Delete the two count lines.** The counts repeat legend line 274. |
| A–C | `violin: kernel density of unit means` / `dashed line: D_eff = 1` | 3 | footer, below lower axes | KEY, but triplicated | **YD (5A):** "The broken y-axis is unnecessary — add a line at *D* = 1 instead." | **Keep once, on panel A. Delete from B and C.** The dashed-line definition answers Yann directly, so it must survive somewhere in the panel row. Both lines repeat legend lines 268 and 273–274 verbatim. |
| D | `WT vs PproA`, `WT vs PproB`, `PproA vs PproB` | 1 (3) | subplot headers | KEY | — | KEEP. |
| D | `18 agarose, 16 liquid paired units` (and 18/18, 18/16) | 3 | second line of the x-axis title | SUBSTITUTE | — | **DELETE.** Repeats legend line 274 and the panel A–C headers. |
| D | `0.57` `0.55` `0.55` `0.68` `0.31` `0.37` and twelve more | 18 | beside each bar | SUBSTITUTE | — | **KEEP.** A symmetric log axis from 1/6.5 to 6.5 cannot be read to two decimals. These numbers are the panel's only quantitative output. Deleting them would make the panel worse. |
| D | `D_eff = speed² × τ / 2, so on this log axis the two component bars add to the D_eff bar` | 1 | footer, full width | SUBSTITUTE | — | **DELETE.** Near-verbatim repeat of legend lines 277–279. |
| D | `agarose` / `liquid` | 1 | key, top left | KEY | — | KEEP. |
| E | `3.14±1.05` / `N=2,931`, `1.73±0.58` / `N=3,524` | 2 | inside axes | SUBSTITUTE | **MJ, YD (1C legend), applied here** | KEEP. Same decision as Figure 1C: the coauthors put these values in the figure. |
| E | `WT vs PproA` | 1 | header | KEY | — | KEEP. |
| E | `Cell-count frequency` / `Independent day replicate mean` / `Mean of replicate means` | 1 | key | KEY | **YD (1C)** | KEEP. |
| F | `2.59±0.72` / `N=4,018`, `4.60±2.81` / `N=4,918` | 2 | inside axes | SUBSTITUTE | as E | KEEP. |
| F | `WT vs PproB` | 1 | header | KEY | — | KEEP. |
| F | `Cell-count frequency (11 cells above 20)` / two more lines | 1 | key | KEY | — | **KEEP.** The parenthesis states what the clipped axis hides. Nothing else does. |
| G | `2.42±1.74` / `N=7,904`, `3.71±2.41` / `N=6,494` | 2 | inside axes | SUBSTITUTE | as E | KEEP. |
| G | `PproA vs PproB` | 1 | header | KEY | — | KEEP. |
| G | `Cell-count frequency (13 cells above 20)` / two more lines | 1 | key | KEY | — | KEEP. |

### Supplementary Figure 1 — 180 × 72 mm

| Panel | Text | Reps | Position | Category | Coauthor comment | Recommendation |
|---|---|---:|---|---|---|---|
| A, B | `Mother-only` / `Non-mother` | 4 | subplot headers | KEY | — | KEEP. |
| A, B | `Cell distribution (descriptive)` / `Independent replicate mean` / `Mean of replicate means` | 2 | key | KEY | **YD (global, Dispersion)** | KEEP. |

### Supplementary Figure 2 — 180 × 119 mm

| Panel | Text | Reps | Position | Category | Coauthor comment | Recommendation |
|---|---|---:|---|---|---|---|
| A | 60 gene names `fliC` `tsr` `fliO` … `flgJ` | 1 (60) | subplot headers | KEY | **YD, MJ (3B):** protein identity must be readable. | **KEEP.** Each name identifies its own subplot. |
| A | strain key `ΔflhDC` `Ppro1-flhDC` `PproA-flhDC` `WT` `PproB-flhDC` `PproD-flhDC` | 1 (6) | key, top | KEY | **MJ (Colour)** | KEEP. |

### Supplementary Figure 3 — 180 × 190 mm

State check, as the brief asked: the nine panels were rebuilt at 2026-08-14
21:59. **The annotation block is still present in all nine.** The restyle in
progress has not removed it.

| Panel | Text | Reps | Position | Category | Coauthor comment | Recommendation |
|---|---|---:|---|---|---|---|
| A | `paired-unit ratio PproA/WT, 95 % CI` / `agarose 0.71 (0.67, 0.76), 18 units` / `liquid 0.67 (0.59, 0.75), 16 units` | 1 | **above the axes**, full width, 3 lines | SUBSTITUTE | **none.** This figure is new in the revision (legacy id `Figure5/Figure5A_…`). No worklist item names it. | **DELETE.** See §4, rank 1. |
| B | `paired-unit ratio PproB/WT, 95 % CI` / `agarose 1.23 (1.12, 1.32), 18 units` / `liquid 1.15 (1.10, 1.20), 18 units` | 1 | above axes | SUBSTITUTE | none | DELETE. |
| C | `paired-unit ratio PproB/PproA, 95 % CI` / `agarose 1.64 (1.49, 1.79), 18 units` / `liquid 1.53 (1.37, 1.67), 16 units` | 1 | above axes | SUBSTITUTE | none | DELETE. |
| D | `paired-unit difference PproA - WT, 95 % CI` / `agarose -0.27 (-0.31, -0.22), 18 units` / `liquid -0.20 (-0.25, -0.14), 16 units` | 1 | above axes | SUBSTITUTE | none | DELETE. |
| E | `paired-unit difference PproB - WT, 95 % CI` / `agarose 0.04 (0.00, 0.09), 18 units` / `liquid 0.04 (0.02, 0.08), 18 units` | 1 | above axes | SUBSTITUTE | none | DELETE. |
| F | `paired-unit difference PproB - PproA, 95 % CI` / `agarose 0.28 (0.21, 0.34), 18 units` / `liquid 0.19 (0.11, 0.26), 16 units` | 1 | above axes | SUBSTITUTE | none | DELETE. |
| G | `paired-unit ratio PproA/WT, 95 % CI` / `agarose 0.63 (0.54, 0.73), 18 units` / `liquid 0.70 (0.55, 0.86), 16 units` | 1 | above axes | SUBSTITUTE | none | DELETE. |
| H | `paired-unit ratio PproB/WT, 95 % CI` / `agarose 1.15 (1.06, 1.25), 18 units` / `liquid 1.08 (1.02, 1.15), 18 units` | 1 | above axes | SUBSTITUTE | none | DELETE. |
| I | `paired-unit ratio PproB/PproA, 95 % CI` / `agarose 1.87 (1.37, 2.63), 18 units` / `liquid 1.26 (1.06, 1.46), 16 units` | 1 | above axes | SUBSTITUTE | none | DELETE. |
| H only | `agarose` / `liquid` | 1 | key, bottom | KEY | **YD (5A):** medium must be readable. | **KEEP, and add it to A as well.** Only one of the nine panels carries the medium key. That is an inconsistency, not a saving. |

### Supplementary Figure 4 — 180 × 186 mm

| Panel | Text | Reps | Position | Category | Coauthor comment | Recommendation |
|---|---|---:|---|---|---|---|
| A–F | `PproA` / `WT` / `PproB` | 6 | row label, left | KEY | **MJ (Colour)** | KEEP. |
| A–F | `liquid — calibrated speed and turning`, `agarose-like mesh — calibrated speed and turning` | 6 | header, above axes | MIXED | — | **Trim to `liquid` / `agarose-like mesh`.** The tail repeats legend lines 350–352. |
| A–F | `20 µm` | 6 | beside the scale bar | KEY | **ME (4A):** "Scale bar missing in the example images." | **KEEP.** A scale bar without its value is not a scale bar. Value duplicates legend line 346 (§5). |
| A–F | `run end` / `stalled` / `non-motile` | 6 | key, top | KEY | — | KEEP. |

### Supplementary Figure 5 — 180 × 194 mm

| Panel | Text | Reps | Position | Category | Coauthor comment | Recommendation |
|---|---|---:|---|---|---|---|
| A | `18 paired experiments` / `WT 4,390 trajectories` / `PproA 2,823 trajectories`; and `16 paired experiments` / `WT 4,595` / `PproA 3,132` | 2 | inside axes, lower centre | SUBSTITUTE | — | **DELETE the `paired experiments` line, keep the trajectory counts.** The paired-experiment counts repeat legend line 411. The trajectory counts appear nowhere else. |
| B | `18 paired experiments` / `WT 6,213` / `PproB 5,443`; and `18` / `WT 4,741` / `PproB 3,781` | 2 | inside axes | SUBSTITUTE | — | as A. |
| C | `18 paired experiments` / `PproA 4,841` / `PproB 9,033`; and `16` / `PproA 4,087` / `PproB 3,921` | 2 | inside axes | SUBSTITUTE | — | as A. |
| A–C | `Agarose` / `Liquid` | 6 | subplot headers | KEY | **YD (5A)** | KEEP. |
| A–C | `WT` / `PproA` / `Unit centroid, 95 % CI` / `D_eff = 1` | 3 | key, top | KEY | **YD (5A):** "add a line at *D* = 1". **YD (global, Dispersion).** | **KEEP.** `D_eff = 1` is the delivered answer to the broken-axis complaint. |

## 4  Marc's decision list — SUBSTITUTE blocks only, ordered by cost

Cost is the page height that deletion frees, then the ink it frees. Height is
what matters: six figures are over a Nature Communications height cap
(the figure exceeded the double-column width, since corrected).

| # | Where | What to delete | Frees | Also fixes |
|---:|---|---|---|---|
| 1 | Supplementary Figure 3 A–I | the three-line paired-unit annotation block | **23.3 mm of page height** (7.8 mm per panel row × 3 rows) and 3,861 mm² of ink. S3 goes 190 → 167 mm and clears the 185 mm cap. | Nothing else. No coauthor asked for this text. |
| 2 | Figure 7 A–C | the footer pair on B and C (keep it on A) | 6.0 mm of height if the whole row loses the strip; 4.0 mm if only B and C lose it. 660 mm² of ink. | Removes a verbatim repeat of legend lines 268 and 273–274. |
| 3 | Figure 7 D | the footer sentence `D_eff = speed² × τ / 2, …` plus the three `18 agarose, 16 liquid paired units` axis lines | **4.8 mm of height**, 831 mm² of ink. | Removes a near-verbatim repeat of legend lines 277–279 and 274. |
| 4 | Figure 7 A–C | the `18 units` / `16 units` lines under the medium labels | 2.8 mm of height, 462 mm². | Removes a triple print of the same six counts. |
| 5 | Figure 7 A–C | the six `D ratio …` blocks | ~0 mm height (they sit in the inter-row gap), 880 mm² of ink. | Removes the only panel-to-panel value duplication in the package. |
| 6 | Supplementary Figure 5 A–C | the six `N paired experiments` lines | 0 mm height (inside the axes), ~250 mm². | Removes a repeat of legend line 411. |
| 7 | Figure 6 C | the three `N=257` lines | 0 mm height, ~90 mm². | Removes a triple print, and a repeat of legend lines 235 and 241. |
| 8 | Figure 5 D–E, Supplementary Figure 4 A–F | the tail `— calibrated speed and turning` (8 panels) | 0 mm height, ~700 mm². | Removes a repeat of legend lines 160–162 and 350–352. |
| 9 | Figure 1 C, D, H and Figure 7 E–G | the 31 `mean ± SD` / `N=` blocks | 0 mm height, ~1,400 mm² of plot area. | **Do not do this without asking Yann.** Michael and Yann agreed the values leave the *legend*; Michael already deleted them there. Deleting them from the panel too would leave them nowhere. |

Total height recovered if you do items 1–4: **Supplementary Figure 3 190 → 167 mm**
and **Figure 7 222 → 208 mm**.

Items 5–9 free ink, not page. They make the panels quieter. They do not make a
figure fit.

## 5  Panel-and-legend duplication

The coauthors asked twice that a value not appear in both places
(worklist 1C legend, and worklist Legends: "Both reviewers read the current
legends as paraphrasing the Results"). Here is every case I found. Line numbers
are `docs/revision_2026-08-12/legends.md`.

| Value or sentence | In the panel | In the legend | Verdict |
|---|---|---|---|
| `violin: kernel density of unit means` | Figure 7 A, B, C footer | line 268: "The violin is the kernel density of the unit means." | Verbatim duplicate. Cut from B and C. |
| `dashed line: D_eff = 1` | Figure 7 A, B, C footer | lines 273–274: "The dashed line denotes D_eff = 1." | Verbatim duplicate. Keep on A only. |
| `D_eff = speed² × τ / 2, so on this log axis the two component bars add to the D_eff bar` | Figure 7 D footer | lines 277–279: "…so on the log axis the two component bar lengths add to the product bar length." | Near-verbatim duplicate. Cut from the panel. |
| Paired-unit counts 18/16, 18/18, 18/16 | Figure 7 A–C headers (`18 units`, `16 units`) **and** Figure 7 D axis lines (`18 agarose, 16 liquid paired units`) | line 274: "Paired-unit counts (agarose/liquid) are 18/16, 18/18 and 18/16." | Printed three times: twice in the figure, once in the legend. Cut both panel prints. |
| Paired-experiment counts 18/16, 18/18, 18/16 | Supplementary Figure 5 A–C (`18 paired experiments`) | line 411: "paired-experiment counts (agarose/liquid) are 18/16, 18/18 and 18/16." | Duplicate. Cut from the panel. |
| `n = 257` | Figure 6 C, three times as `N=257` | lines 235 and 241 | Printed five times for one number. Cut the three panel prints. |
| `20 µm` | Supplementary Figure 4 A–F, beside the scale bar | line 346: "The scale bar in each panel is 20 µm." | Duplicate, but **keep the panel print**. Cut the legend sentence instead. A scale bar must carry its own value. |
| `10`, `100`, `1000` cells per bubble | Figure 1 E bubble key | line 21: "the key gives 10, 100 and 1000 cells per bubble." | Duplicate. **Keep the panel key, cut the legend clause.** |
| "calibrated speed and turning" | Figure 5 D, E and Supplementary Figure 4 A–F headers | lines 160–162 and 350–352 | Duplicate. Cut the panel tail; the legend states it properly. |

### Panel-to-panel duplication, inside one figure

| Value | First print | Second print |
|---|---|---|
| `0.31`, `0.37` | Figure 7 A, `D ratio` blocks | Figure 7 D, bar labels |
| `1.65`, `1.48` | Figure 7 B, `D ratio` blocks | Figure 7 D, bar labels |
| `4.10`, `3.10` | Figure 7 C, `D ratio` blocks | Figure 7 D, bar labels |

Six numbers, printed twice inside one figure. Figure 7 D is the panel built to
show them. Cut them from A–C.

### Clean cases, for the record

Two families of numbers are printed in the panel and **only pointed at** in the
legend. Those are correct and need no action:

- Figure 1 C, D, H and Figure 7 E–G `mean ± SD` and `N=`: legend lines 18 and
  295 say "Each condition prints its mean ± SD … and its cell count." Michael
  already deleted the values from the legend. This is the requested end state.
- Supplementary Figure 5 trajectory counts: legend line 410 says "its trajectory
  count per phenotype" without repeating the numbers.

## 6  The blocks that are neither KEY nor SUBSTITUTE

**PLACEHOLDER — 6 rows, 9 prints.** Figure 1 A, B, F, G; Figure 3 A; Figure 6 E
(four times). These read `EDITABLE … SCHEMATIC / not supplied` and
`Calibrated microscopy field required`. They are not commentary. They are a
contract: the panel states what asset is missing and why nothing was invented in
its place. Figure 6 E's placeholder is also the reason no scale bar is drawn
there, which answers a still-open baseline comment from you. Delete none of
them. Replace them.

**ATTRIBUTION — 1 row.** Figure 4 A carries the line
"Cellular economy model for Salmonella typhimurium · Author: Dr. Michael Jahn"
in 7 pt grey at the top-left corner. This is a byline inside the artwork. It is
neither a mark definition nor a result. Michael is a coauthor, so the paper
credits him already, and journals do not print bylines inside figures. Ask
Michael, then remove it.

**MIXED — 4 rows, 14 prints.** Several blocks pair a KEY line with a SUBSTITUTE
line inside one text group: `Agarose (filled)` + `18 units` in Figure 7 A–C, and
`Liquid` + `— calibrated speed and turning` in Figure 5 D–E and Supplementary
Figure 4 A–F. These need a partial trim, not a deletion. A blanket sweep would
take the convention out with the clutter.

## 7  My honest view

**Do items 1 to 4. Think hard about 5 to 8. Leave 9 alone.**

The sweep is worth doing, but for a narrower reason than it first looks. Only
two figures gain page height from it: Supplementary Figure 3 gains 23.3 mm and
Figure 7 gains 13.6 mm. Everywhere else the text sits inside the axes, so
deleting it frees ink and nothing more. Figure 1 is 212 mm tall and has 19
SUBSTITUTE blocks; deleting all 19 would shrink it by zero millimetres. If the
goal is to reach the height caps, in-panel text is the wrong lever for Figures
1 and 4. Figure 7 still lands at 208 mm after the full sweep, which clears the
210 mm row only if the caption stays under 150 words. Its caption is far longer
than that today.

The Supplementary Figure 3 annotation block is the one clear win. It is the
example the brief named, and the evidence supports the instinct: it is three
lines of prose standing where a graphic belongs, it sits in a dedicated strip
above the axes so removing it really does shrink the figure, no coauthor asked
for it, and every value it prints is already in Source Data (legend line 338).
Nine panels, 23 mm, no cost. Do it first.

**Where deleting text would make a figure worse.**

- **Figure 5 A.** The three-line key is Michael's own wording, delivered against
  Yann's request. Removing it undoes a completed item and puts the same question
  back in the next review round.
- **Figure 7 D bar numbers.** A symmetric log axis running from 1/6.5 to 6.5
  cannot be read to two decimals. Those 18 numbers are the panel's output. Strip
  them and the panel shows a shape with no scale.
- **Figure 4 C protein labels.** Yann, Michael and Kathir all complained that
  these were unreadable. The 24 external labels with leader lines are the fix.
  Removing them is not tidying; it is reverting.
- **Figure 1 C, D, H and Figure 7 E–G statistics.** Michael deleted these from
  the legend on the understanding that the figure keeps them. Deleting them from
  the figure as well would delete them from the manuscript. Yann's alternative
  was the main text, not nowhere. If you want them out of the panels, put them in
  the Results first and tell Yann and Michael that you took the second half of
  their proposal.
- **Supplementary Figure 4 `20 µm`.** A scale bar whose value lives only in the
  caption fails the first thing a reader does with a micrograph.

**One thing that is not a deletion problem.** Supplementary Figure 3 H is the
only one of nine panels that carries the `agarose` / `liquid` medium key. The
other eight leave the fill convention undefined. That is a missing KEY, not a
surplus SUBSTITUTE, and it is worth fixing in the same pass.

**A caution on the arithmetic.** Removing a text strip does not shrink a figure
on its own. The builder writes panel heights from `config/assembly_*.yaml`. The
23.3 mm on Supplementary Figure 3 and the 13.6 mm on Figure 7 arrive only if
someone also reduces `height_mm` and the panel `y` values in those two files.
Treat the numbers above as the space that becomes available, not as an automatic
saving.
