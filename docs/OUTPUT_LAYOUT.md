# Canonical output organization

Everything under `build/` is generated. Delete the tree and
`make reproduce-available && make organize && make figure-qa` rebuilds it.
`.gitignore` excludes `build/`. Generated files are never canonical inputs.

There is no catch-all `final` directory. `build/final/` and `build/figure_04/`
are obsolete and must not be recreated. The word `final` is reserved for a
future complete, visually accepted release.

Figure names are `Figure_1` … `Figure_7` and `Supplementary_Figure_1` …
`Supplementary_Figure_5`. `build/` always uses the **current** numbering, even
where `analyses/` and `data/` still use the pre-revision names. See
[`REPOSITORY_MAP.md`](REPOSITORY_MAP.md#figure-to-analyses-directory-map).

```text
build/                          178 MB
├── panels/                      20 MB   61 directories: 60 registered panels + 1 diagnostic
├── figures/                    8.9 MB   12 assembled figures
├── source_data/                126 MB   per-panel tables, submission/ and the combined workbook
├── statistics/                 172 KB   tests, effects, intervals and units
├── provenance/                 368 KB   organized copy of the panel provenance
├── diagnostics/                 22 MB   previews, accessibility simulations, QA record
├── reports/                    112 KB   copy of docs/revision_2026-08-12/
├── workflow/                    44 KB   reproduction manifests
└── environment/                4.0 KB   environment bootstrap record
```

---

## `build/panels/<figure_name>/<label>/`

One directory per registered panel, 60 in all. Each holds:

| File | Content |
|---|---|
| `<PANEL_ID>.svg`, `.pdf`, `.png` | the graphic in three formats |
| `status.json` | panel ID, title, status, the producing `analysis_directory`, every declared output with sha256, the `reference_target`, and `invented_outputs: false` |
| `provenance.json` | the panel-local copy of the provenance document |
| `artifacts.json` | declared outputs with sha256 and byte counts |

Some panels add a table, for example `build/panels/Figure_3/C/summary.csv`.

Asset-blocked panels (`F1_A`, `F1_B`, `F1_F`, `F1_G`, `F3_A`) carry an explicit
placeholder graphic plus status and provenance metadata. Their `status.json`
names the missing asset under `blocker.reason` and points `reference_target` at
the frozen July figure. No invented scientific graphic is ever written.

This tree holds registered manuscript panels only, so it has exactly 60
directories. Diagnostics live under `build/diagnostics/` instead.

Panel filenames follow the panel ID (`F3_C.svg`). Figure 4A is the exception:
its file is `Figure_4_A.svg`, because it wraps the vendored asset
`assets/schematics/salmonella_model.svg`.

## `build/figures/<figure_name>/`

Twelve directories, one per manuscript figure. Each holds:

- `<figure_name>_revision_partial.svg` — the assembly, built from
  `config/assembly_<figure>.yaml`
- `<figure_name>_revision_partial.manifest.json` — the checksum manifest
- `status.json` — the per-panel status map, the assembly manifests, the
  reference target, and `complete_final_figure_available: false`

The `_revision_partial` suffix is honest naming, not a placeholder. It stays
until every panel of that figure reaches status `reproduced`.

## `build/source_data/`

Per-panel tables under `<figure_name>/<label>/`, plus the Source Data files.

- Eight figure directories exist: `Figure_1` … `Figure_7` and
  `Supplementary_Figure_1`. The remaining supplementary panels write their
  tables to `data/source_data/<analysis_dir>/` instead. The builder reads both.
- `submission/` — one Source Data file per figure, twelve in total. This is the
  set we submit. Each file carries its own README, INDEX and DATA_DICTIONARY.
  All twelve are `.xlsx` today, 28.2 MB in total, the largest 7.7 MB. A figure
  ships as `.zip` of tab-separated `.txt` files only if its workbook exceeds the
  journal's 30 MB cap.
- `deposit/Supplementary_Figure_4_trajectories/` — the six simulated-trajectory
  tables that go to the DOI-bearing repository instead of the journal, plus
  `README.txt` and `MANIFEST.tsv`. 28.4 MB. The tables are copied byte for byte,
  so their checksums still match the audited provenance.
- `Source_Data_per_figure.manifest.json` — per file: format, bytes, sha256,
  table count, panels and sheet names, plus `superseded_duplicates` and the
  `deposit` record.
- `Source_Data_revision_partial.xlsx` — the combined workbook, internal only.
- `Source_Data_revision_partial.manifest.json` — sha256, table count,
  `status: partial`, the five `missing_panels`, and `deposited_tables`.

Four panels record the same table twice: a pre-renumbering copy under
`data/source_data/` and the current copy under `build/source_data/`. The builder
drops the legacy copy, but only after it proves the current copy contains every
row and column of it. See
[`SOURCE_DATA_DICTIONARY.md`](SOURCE_DATA_DICTIONARY.md).

Large tables are gzip-compressed CSV (`F3_C_source_data.csv.gz`). The collection
uses no git-lfs and holds a 100 MB per-file policy, so oversized legacy tables
are migrated as checksum-backed extracts rather than copied whole. Each affected
provenance document says so in its `limitations` field.

## `build/statistics/<figure_name>/<label>/`

Exact tests, effect sizes, intervals and units. One CSV per reported quantity.
Eight figure directories hold content today; panels whose plotted summary
carries no inference write none. Examples:

- `Figure_3/C/F3_C_statistics.csv` — paired t-test, 95 % CI, p and BH q value
- `Figure_6/B/Figure_6B_paired_statistics.csv`
- `Supplementary_Figure_5/A/S5_A_paired_centroid_differences.csv`, plus
  `S5_A_caption_sentences.txt`, the generated sentences for the legend

## `build/provenance/<figure_name>/<label>.json`

The organized copy of each panel's provenance, written by
`tools/organize_build.py`. Schema version 1.0.0. Fields: `panel_id`, `status`,
`generated_at_utc`, `command`, `inputs` (path, sha256, bytes, rows), `outputs`,
`software`, `parameters`, `random_seeds`, `limitations`.

The authoritative store is `metadata/provenance/`, which git tracks. This copy
exists so a reader can stay inside `build/`.

**It currently holds 69 documents, not 60.** Nine describe withdrawn panel IDs
from before the 12 August 2026 renumbering:
`Supplementary_Figure_4/G.json` … `L.json` and
`Supplementary_Figure_5/D.json` … `F.json`, all stamped 12 Aug 2026 17:22.
`make organize` does not remove them. Ignore any file whose `panel_id` is not a
row of `config/panels.csv`.

## `build/diagnostics/`

| Path | Content |
|---|---|
| `figure_previews/<figure_name>.png` | 300 dpi raster of each assembled figure, 12 files. The fastest way to look at a figure. |
| `grayscale/<figure_name>.png` | sRGB luminance simulation, 12 files |
| `deuteranopia/<figure_name>.png` | Machado et al. (2009) deuteranomaly matrix, severity 100, 12 files |
| `figure_qa.json` | the QA record: per-panel viewBox, assembly scale, editable text nodes, declared and effective font size; the failure lists `small_font_failures`, `editable_text_failures`, `star_text_failures` |
| `Figure_4/` | the raw (non-differenced) overlay that panel B shows as a change from reference, plus its table `raw_overlay.csv` |
| `Figure_5/` | timestep-convergence and delivered-parameter audits for the active-particle simulation |
| `Figure_7/preview/`, `Figure_7_candidates/` | alternative geometries considered for Figure 7 |

`make figure-qa` writes all of it. The on-page font floor is 6.0 pt. One panel
fails: `build/panels/Figure_4/A/Figure_4_A.svg` at 2.65 pt.

## `build/reports/revision_2026-08-12/`

A verbatim copy of `docs/revision_2026-08-12/`, refreshed by `make organize`.
Twelve files: the legends, the change log, the reviewer gaps, the submission
to-do, the not-done list, the analysis report, the cross-reference audit, the
handoff, `figure_numbers.csv` and `panel_map_revision_2026-08-12.csv`.

Edit the copy under `docs/`. The one under `build/` is overwritten.

## `build/workflow/`

- `available_reproduction.json` — written by `make reproduce-available`. Lists
  `executed_panels` (55), `blocked_asset_panels` (5), `blocked_external_panels`
  (0), `missing_analysis_provenance_panels` (0), the environment lock, and
  `complete: false`.
- `available_inventory_only.json` — a wave-1 plan from 11 August 2026. It
  reports 45 panels and 11 external blockers and is **stale**. Do not quote it.

`make reproduce` would write `strict_reproduction.json`. It has never run to
completion, because strict preflight refuses while any panel is partial or
asset-blocked.

## `build/environment/bootstrap.json`

The record `make bootstrap` writes: platform, Python version, panel count and
blocked panel IDs. The current file is dated 11 August 2026 and predates the
revision. It reports 56 panels and a blocked list written in the pre-revision
numbering, in which `F3_A` and `S3_A` denote different panels than they do
today. Rerun `make bootstrap` before you quote it.

---

## Related documents

- [`README.md`](../README.md) — commands, current state, known limitations
- [`REPOSITORY_MAP.md`](REPOSITORY_MAP.md) — every top-level directory and the figure map
- [`PANEL_CONTRACT.md`](PANEL_CONTRACT.md) — what a canonical panel must satisfy
- [`SOURCE_DATA_DICTIONARY.md`](SOURCE_DATA_DICTIONARY.md) — source-table columns and units
