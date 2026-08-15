# Repository map

Every top-level directory of the collection, what it holds, and who writes it.
Start at [`README.md`](../README.md) if you want the commands instead.

Two words carry a fixed meaning here:

- **authored** — a person writes it. Git tracks it. Editing it changes the build.
- **generated** — a command writes it. Never edit it by hand.

---

## Top-level directories

| Directory | Holds | Authored or generated | In git | The one thing to know |
|---|---|---|---|---|
| `analyses/` | The canonical producer for every panel: one script, one config and one metadata folder per panel. 512 files. | authored | yes, 421 files | **The directory names lie.** See the [figure map](#figure-to-analyses-directory-map) below. Legacy twins sit next to the live directories. |
| `archive/` | Untouched collaborator deliveries under `archive/incoming/2026-08-12/`, plus `migration_manifest.csv`. 131 MB. | authored, then frozen | **no** | Read-only evidence. Never edit a delivery in place; intake copies out of it. |
| `assets/` | Non-generated graphics: `schematics/salmonella_model.svg`, the competition-design source, `CHECKSUMS.sha256`. | authored | yes | Only two image assets are registered. Everything else a figure shows is drawn by code. `salmonella_model.svg` is the reason Figure 4A fails QA. |
| `build/` | All generated output: panels, figures, statistics, source data, provenance, diagnostics, reports, workflow and environment records. 178 MB. | generated | **no** | Delete it and `make reproduce-available` rebuilds it. Structure is in [`OUTPUT_LAYOUT.md`](OUTPUT_LAYOUT.md). The Source Data files to submit are in `build/source_data/submission/`, one per figure. The combined Supplementary Information PDF is `build/supplementary_information/`, written by `make supplementary-information`. |
| `config/` | The registries: `panels.csv`, `artifacts.csv`, `panel_artifacts.csv`, `figures.yaml`, twelve `assembly_*.yaml`, `palette.yaml`, `style.yaml`, fetch and validation manifests. 22 files. | authored | yes | `config/` uses the **current** figure numbers everywhere. It is the authority when a directory name disagrees. |
| `data/` | `raw/`, `interim/`, `processed/`, `external/`, `source_data/`. 139 MB. | mixed: `external/` and `processed/` are authored or migrated; `source_data/` is generated | **no** | `raw/` and `interim/` hold only `.gitkeep`. Reproduction starts at `processed/`. Subdirectory names still use the old figure numbers. |
| `docs/` | This map, the panel and figure contracts, the environment and data-availability records, and `revision_2026-08-12/`. | authored, partly generated | yes | `docs/revision_2026-08-12/` is the revision record. `tools/build_revision_reports.py` writes some of its files; `make organize` copies the whole directory to `build/reports/`. |
| `metadata/` | The central provenance store, `metadata/provenance/<figure_dir>/<PANEL_ID>.json`. One document per panel. | generated | yes, 60 files | Exactly 60 documents are expected. It currently holds 78: eighteen macOS `<panel> 2.json` copies break `make audit` and `make source-data-available`. Its subdirectories use the **current** numbering, so `metadata/provenance/supplementary_04/` and `analyses/supplementary_04/` mean different figures. |
| `models/` | Vendored model code: `cell_economy/upstream/` (with `LICENSE`, `UPSTREAM_SOURCE.md`, `CHECKSUMS.sha256`), `gradient/`, `motility_simulation/`. | authored, vendored | yes | An exact upstream snapshot with checksums. Do not patch it in place; record any change in `UPSTREAM_SOURCE.md`. |
| `reference/` | Frozen baselines: `2026-07-09/` (the July figures and manuscript) and `2026-08-12-revision/` (revision prompt, merged manuscript, embedded media, July visual reference). 106 MB. | authored, then frozen | **no** | The five blocked panels point here instead of to a regenerated output. `reference/2026-07-09/` uses **July** figure numbers. |
| `scripts/` | `bootstrap_environment.sh` only. | authored | yes | It pins uv 0.8.11 and CPython 3.12.11 and installs the project as a wheel, not as an editable link. That wheel goes stale when `src/` changes. |
| `src/` | The package `flagella_repro`: CLI, registry validation, provenance schema, reproduction driver, figure QA, theme, source-data workbook. | authored | yes | This is live code. `make` sets `PYTHONPATH=src`; manual `python -m flagella_repro` calls do not, and pick up the stale wheel. |
| `tests/` | 19 pytest modules plus `conftest.py`, covering registries, provenance, output layout, font QA, SVG assembly and the revision figures. | authored | yes | `make test` runs them in about 15 s and all pass. They are the cheapest check that a change did no harm. |
| `tools/` | Standalone build steps the `Makefile` calls: `organize_build.py`, `assemble_available_figures.py`, `build_source_data_workbook.py`, `run_figure_qa.py`, `build_supplementary_information.py`, `build_software_versions.py`, intake and freeze helpers. 15 files. | authored | yes | Panel producers live in `analyses/`; `tools/` only organizes, assembles and checks. `build_source_data_workbook.py` writes both the per-figure Source Data files and the combined workbook. |
| `workflow/` | `Snakefile`, 33 lines. | authored | yes | It is a thin wrapper. The real work is `flagella_repro.reproduction.reproduce_available_panels`. `mode` is `available` or `strict`. |

Loose files at the root: `Makefile` (the public interface), `pyproject.toml`,
`uv.lock`, `requirements.lock`, `Dockerfile`, `CITATION.cff`, `LICENSE`,
`LICENSES.md`, `REFERENCE_RELEASE.md`, `reference_manifest.csv`.

`LICENSE` is GPL-3.0-only and covers all of the collection's own code.
`models/cell_economy/LICENSE` names the same licence; it stays because that
subtree also holds third-party GPL code under a different copyright holder.
[`LICENSES.md`](../LICENSES.md) maps every directory to its licence and is the
authority.

### Why `data/`, `reference/` and `archive/` are outside git

`.gitignore` excludes all three, plus `build/`. Together they are 554 MB.
`archive/` and `reference/` are frozen evidence; `data/` holds large migrated
inputs. None of them are regenerable from the repository, so they are backed up
separately and are read-only for the build. Track them with git-lfs or a data
repository if they must be versioned. `build/` is excluded for the opposite
reason: every file in it is reproducible.

---

## Figure to analyses-directory map

Read this before you open anything under `analyses/`. The **producer** column
comes from the `command` and `inputs` fields of
`build/provenance/<figure_name>/<label>.json`, not from directory names.

| Figure | Panel IDs | Producer directory | Watch out |
|---|---|---|---|
| Figure 1 | `F1_A`…`F1_H` (8) | `analyses/figure_01/` | `panel_a`, `panel_b`, `panel_f`, `panel_g` are asset-blocked. `render_blocked_assets.py` writes their placeholders. |
| Figure 2 | `F2_A`…`F2_C` (3) | `analyses/figure_02/` | The directory has eight panel folders. Only `panel_a`…`panel_c` produce current Figure 2 panels. |
| Figure 3 | `F3_A`…`F3_E` (5) | `analyses/figure_03_revision/` | `F3_C` reads `data/processed/figure_02/F2_F/`, a legacy path. `F3_A` is asset-blocked. |
| Figure 4 | `F4_A`…`F4_F` (6) | `analyses/figure_04_revision/` | `F4_A` embeds `assets/schematics/salmonella_model.svg` and fails `make figure-qa`. |
| Figure 5 | `F5_A`…`F5_E` (5) | `analyses/figure_05_revision/` | `F5_D` and `F5_E` also read `analyses/motility_adopted_parameters/`, which builds the one adopted parameter table on top of `analyses/motility_parameter_calibration/`, `analyses/motility_turn_angle_comparison/` and `analyses/motility_stall_parameter_comparison/`. They are the only two panels with status `reproduced`. Each takes minutes. |
| Figure 6 | `F6_A`…`F6_E` (5) | `analyses/figure_06_revision/` | One builder, `build_figure_06_revision.py --panel <label>`. |
| Figure 7 | `F7_A`…`F7_G` (7) | `analyses/figure_07_revision/` | One builder, `build_figure_07_revision.py --panel <label>`. |
| Supplementary Figure 1 | `S1_A`, `S1_B` (2) | `analyses/supplementary_01/` | Reuses the plotting code of `analyses/figure_02/panel_c/`. |
| Supplementary Figure 2 | `S2_A` (1) | `analyses/collaborator_science/build_panels.py --panel S2_A` | The panel config sits in `analyses/supplementary_02/panel_a/`, but the builder does not. |
| Supplementary Figure 3 | `S3_A`…`S3_I` (9) | `analyses/supplementary_03/` | Built by `build_s3.py --panel <label>`. |
| Supplementary Figure 4 | `S4_A`…`S4_F` (6) | `analyses/supplementary_04/` | Built by `build_s4.py --panel <label>`. Also reads `analyses/motility_adopted_parameters/` for the adopted parameter table, the same file Figure 5D and 5E read. |
| Supplementary Figure 5 | `S5_A`…`S5_C` (3) | `analyses/supplementary_05/` | Built by `build_supplementary_05.py --panel <label>`. Also reads `analyses/figure_07_revision/`. |

The pre-revision twins `analyses/figure_03/`, `figure_04/` and `figure_05/` were
deleted on 15 August 2026. Nothing replaces them; the producer column is now the
only directory for each figure.

### The supplementary numbering, and why it was off by one

The July Supplementary Figure 3 duplicated the lower half of the current
Figure 4F. It read the same input file and drew the same association. It was
withdrawn on 12 August 2026 and the later supplementary figures moved up one
number: S4→S3, S5→S4, S6→S5. `docs/revision_2026-08-12/change_log.md` records
the decision.

The `analyses/` directories kept the old numbers for three days, so
`supplementary_04` built Supplementary Figure 3. They were renamed on
15 August 2026, together with their builders, their `data/processed/` and
`data/source_data/` inputs, and the `ANALYSIS_DIRS` map in
`tools/organize_build.py`. Directory and figure now agree everywhere.

### Other places the old numbers survive

| Path | Says | Means |
|---|---|---|
| `data/processed/figure_02/F2_F/` | Figure 2F | input to `F3_C` |
| `data/source_data/figure_04/`, `figure_05/` | Figure 4, Figure 5 | pre-revision names, matching the `analyses/` twins deleted in stage B. No registry or provenance reference found. Candidates for the same treatment as the nine below; not yet investigated in full. |
| `build/provenance/Supplementary_Figure_4/G.json`…`L.json`, `build/provenance/Supplementary_Figure_5/D.json`…`F.json` | panels S4_G…S4_L, S5_D…S5_F | withdrawn panel IDs. Written 12 Aug 2026 17:22, before the renumbering; the live files were rewritten on 13 Aug. `make organize` does not remove them. |
| `build/environment/bootstrap.json` | `panel_count: 56` and a blocked list in pre-revision IDs | written 11 Aug 2026, before the revision. `F3_A` and `S3_A` there are not today's panels. |
| `reference/2026-07-09/` | July figure numbers | the frozen July baseline. Correct as history. |
| `config/figures.yaml` `reference_source_id` | e.g. `Figure3 → Figure2` | deliberate: it maps a current figure to its July source |

`data/source_data/s2_a/` looks like the same kind of orphan but is not. It is
registered in `config/artifacts.csv` and referenced by the `S2_A` provenance.

The nine pre-revision orphans `f2_g/`, `f2_h/` and `f3_a/`…`f3_g/` moved to
`data/source_data/superseded_2026-07/` on 15 August 2026. They were proven
unreferenced, not deleted: `data/` is outside git, so a deletion there cannot be
undone. That directory's `README.md` records what each one was and how to
re-check that nothing has started reading them.

### Two conventions for source data

A panel records its tables in one of two places, and both are in use:

- **`build/source_data/<Figure>/<label>/`** — Figures 1 to 7. The copy under
  `data/source_data/figure_0N_revision/` is written by the builder but recorded
  by nothing, so it is a mirror, not the canonical table.
- **`data/source_data/<directory>/`** — `S1_A` records both; `S3_*` and `S4_*`
  record only this one.

The `f3_g` case shows why the difference matters. A test pinned the manuscript's
3 % optimum against `data/source_data/f3_g/`, a file no build step writes. The
number moved to Figure 5C in the revision, so a change in the gradient model
would have changed `build/source_data/Figure_5/C/relative_biomass.csv` and left
the test passing against a stale copy. The test now reads the live table.

Worth settling on one convention.

### The seven `motility_*` directories

They all serve one model, but they are not equal. Two derive the parameters the
manuscript uses. Five are investigations that justify a choice; their
conclusions are already written up in `docs/revision_2026-08-12/`, and their
value now is that a reviewer can re-run them.

| Directory | Role |
|---|---|
| `motility_parameter_calibration/` | **Derivation.** `calibrate.py` scales the delivered turning parameters. |
| `motility_adopted_parameters/` | **Derivation.** `derive_adopted_parameters.py` composes the one adopted table and owns `adopted_parameter_table_path()`, the single accessor every manuscript panel uses. |
| `motility_turn_angle_comparison/` | Check: per-strain against global turn angle. Written up in `turn_angle_model_comparison.md`. |
| `motility_stall_parameter_comparison/` | Check: the stall-parameter variant grid, and a double-counting test. Written up in `stall_parameter_comparison.md`. |
| `motility_noise_scale_check/` | Check: sensitivity to the noise scale. |
| `motility_effective_diffusivity_check/` | Check: effective diffusivity against the delivered value. |
| `motility_domain_boundary_check/` | Check: box compression at the domain boundary. |

Read the two derivation directories to understand what the panels use. Read the
five checks only to see why a parameter was chosen.

These were considered for grouping into one `motility/` tree with `derivation/`
and `checks/` subdirectories. That was rejected on 15 August 2026: the move
would rewrite 7 `sys.path` import sites, 20 provenance documents, 13 documents
and 3 mirrored `data/processed/` directories, and would force a rebuild of
`F5_D`, `F5_E` and `S4_A`…`S4_F` — the eight most expensive panels in the
repository. The shared `motility_` prefix already sorts them together, and no
name here is wrong or misleading. The cost bought nothing but one nesting level.

---

## Trace a number back to its source

The worked example lives in [`README.md`](../README.md#trace-a-number-back-to-its-source).
It walks the count **110983** from the Figure 3 legend to
`data/processed/figure_02/F2_F/cell_points.parquet` in six verified hops.

The general recipe:

1. Find the panel ID for the legend sentence. Main figures use `F<n>_<label>`,
   supplementary figures use `S<n>_<label>`.
2. Open `build/provenance/<figure_name>/<label>.json`. It names the command,
   every input with its sha256 and row count, every output, the software
   versions, the parameters, the random seeds and the honest limitations.
3. For a test statistic, read `build/statistics/<figure_name>/<label>/`.
4. For the plotted values, read the source-data output listed in the same
   provenance file.
5. For a shortcut, `docs/revision_2026-08-12/figure_numbers.csv` lists each
   number quoted in a legend with its figure, its panel ID, the source file it
   comes from and the rule that computes it. `tools/build_revision_reports.py`
   runs every rule and writes the result, so the register cannot drift. A source
   that stops producing its number stops the build.

---

## Applied: the supplementary directories were renamed

Applied on 15 August 2026. `analyses/supplementary_04`, `05` and `06` built
Supplementary Figures 3, 4 and 5 respectively. Each is now named for the figure
it builds.

### What moved

```
analyses/supplementary_04            -> analyses/supplementary_03
analyses/supplementary_05            -> analyses/supplementary_04
analyses/supplementary_06            -> analyses/supplementary_05
  build_s4.py                        -> build_s3.py
  build_s5.py                        -> build_s4.py
  build_supplementary_06.py          -> build_supplementary_05.py
data/processed/supplementary_04      -> data/processed/supplementary_03
data/processed/supplementary_05      -> data/processed/supplementary_04
data/source_data/supplementary_04    -> data/source_data/supplementary_03
data/source_data/supplementary_05    -> data/source_data/supplementary_04
```

The moves ran in ascending order, `04`→`03` first. Each rename frees the name
the next one needs, so no temporary name was required. `metadata/provenance/`
already used the current numbers and did not move.

Also updated: the path constants and provenance `command` field in each builder;
`ANALYSIS_DIRS` in `tools/organize_build.py`; `DEPOSITED_TABLE_PATHS` and the
regeneration instructions in `src/flagella_repro/source_workbook.py`; every
panel `README.md`, `INPUT_MANIFEST.md` and `scripts/reproduce.py`; and the tests
that name a builder or a source-data path.

### Cost, as paid

Every provenance document records the sha256 of each input path, so all 18
supplementary provenance documents and their registry rows became invalid. The
18 panels were rebuilt directly rather than through
`make reproduce-available --forceall`, which would have rebuilt all 55
executable panels. The registry was then resynchronised with
`tools/sync_revision_provenance.py`, `tools/register_partial_artifacts.py
--write`, `tools/assemble_available_figures.py`, and a second registration.

Every rebuilt panel was checked byte for byte against its predecessor, ignoring
embedded creation dates and generated element IDs. No graphic changed.
