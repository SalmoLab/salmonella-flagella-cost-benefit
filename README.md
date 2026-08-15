# The cost-benefit trade-off of peritrichous flagellation in bacteria — analysis and figure code

<!-- Uncomment after the first Zenodo release and fill in the real DOI.
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
-->

This repository holds the code that draws every figure of the manuscript
**"The cost-benefit trade-off of peritrichous flagellation in bacteria"**
(Giralt-Zúñiga et al.). It covers the 12 August 2026 revision: seven main
figures, five supplementary figures, 60 panels.

Each panel has one canonical producer script under `analyses/`, one output
directory under `build/panels/`, and one provenance document that names its
inputs, its software and its random seeds. You can follow any number in a figure
legend back to the file it came from. [Trace a number back to its
source](#trace-a-number-back-to-its-source) walks one such chain, six hops, all
verifiable.

## Thirty seconds

**What you get by cloning.** The code, the registries, the provenance records,
the pinned environment and the tests. 5.7 MB.

**What you do not get by cloning.** The data. `data/`, `reference/` and
`archive/` are 540 MB and live in a separate archive, because git is the wrong
place for them. **A fresh clone reproduces nothing until you download the data
deposit and unpack it as `data/`.** See
[Get the data](#get-the-data) below.

**Which paper.** See [How to cite](#how-to-cite). The manuscript, its
accessions and its DOIs are listed in
[`docs/AVAILABILITY_STATEMENTS.md`](docs/AVAILABILITY_STATEMENTS.md).

**How to reproduce the figures.** `make bootstrap`, then
`make reproduce-available`. That runs every panel that has a registered source,
in one pass, in about 30 minutes on one core, and writes the assembled figures
to `build/figures/`. See [Quick start](#quick-start). To find the producer of a
single panel, look it up in the [figure
map](docs/REPOSITORY_MAP.md#figure-to-analyses-directory-map) — never guess from
a directory name.

**What is deliberately not reproducible.** Five image panels and the raw-data
layer. This is stated, not hidden — see [Known
limitations](#known-limitations). In short: 55 of 60 panels execute, 2 reproduce
end to end, 53 start from migrated processed tables rather than from raw
instrument output, and 5 have no registered source asset at all and draw a
labelled placeholder instead of an invented graphic. `make reproduce`, the
strict gate, refuses today and is meant to.

**On the supplementary numbers.** The old Supplementary Figure 3 was withdrawn
on 12 August 2026 and the later supplementary figures moved up one number. The
`analyses/` directories were renamed to match on 15 August 2026. See
[Supplementary numbering](#supplementary-numbering).

---

## Get the data

`.gitignore` excludes four directories. Only the first is deposited publicly,
and it is the only one you need to reproduce a panel:

| Directory | Size | What it is | Where it comes from |
|---|---|---|---|
| `data/` | 140 MB | The processed input tables every panel reads. | the Zenodo data deposit |
| `reference/` | 106 MB | Frozen July 2026 figures and the manuscript. Reproduction targets. | not public; the authors' unpublished work |
| `archive/` | 131 MB | Untouched collaborator deliveries. | not public; per-delivery permission |
| `build/` | 160 MB | Every generated output. | rebuilt by `make reproduce-available` |

To reproduce panels you need `data/` only. Download the Zenodo data deposit
(**[data DOI pending]** — see
[`docs/AVAILABILITY_STATEMENTS.md`](docs/AVAILABILITY_STATEMENTS.md)) and unpack
it so that `data/processed/`, `data/external/` and `data/source_data/` sit at
the repository root.

`data/raw/` and `data/interim/` hold only `.gitkeep`, in the deposit as here.
The raw microscopy and the tracking files are not in this collection. Every
provenance document that depends on them says so in its `limitations` field.
That is the honest boundary of what this repository can rebuild.

---

## Quick start

Run these from the repository root. All targets are in `Makefile`.

| Command | What it produces | Time |
|---|---|---|
| `make bootstrap` | Installs uv 0.8.11 and CPython 3.12.11, syncs `.venv` from `uv.lock` with `--frozen`, installs this project as a wheel, and writes `build/environment/bootstrap.json`. Needed once. | minutes, first run only |
| `make inventory` | Validates `config/panels.csv`, `config/artifacts.csv` and `config/panel_artifacts.csv`. Prints the registry counts. | < 1 s |
| `make organize` | Refreshes `build/panels/` and `build/figures/` and copies `docs/revision_2026-08-12/` to `build/reports/`. | < 1 s |
| `make reproduce-available` | Runs every provenance-backed panel workflow and writes `build/workflow/available_reproduction.json`. | ≈ 30 min, one core |
| `make figure-qa` | Renders 300 dpi previews, grayscale and deuteranopia simulations, and checks on-page font size. Writes `build/diagnostics/figure_qa.json`. | ≈ 10 s |
| `make source-data-available` | Builds one Source Data file per figure in `build/source_data/submission/`, the repository deposit in `build/source_data/deposit/`, and the combined internal workbook `build/source_data/Source_Data_revision_partial.xlsx`, all from checksum-validated tables. | ≈ 1 min |
| `make audit` | Cross-checks the registry, the panel outputs and the central provenance. | ≈ 5 s |
| `make reproduce` | Strict gate. Refuses while any panel is partial or asset-blocked. | < 1 s (refuses) |
| `make test` | Runs the pytest suite. 130 tests. | ≈ 35 s |

Every target except `make bootstrap` needs `data/` in place. See
[Get the data](#get-the-data).

`make reproduce` is designed to fail today. It passes only when all 60 panels
reach status `reproduced`. Two do.

Two other targets exit non-zero for reasons listed under
[Known limitations](#known-limitations): `make audit` (five blocked assets) and
`make figure-qa` (one panel below the font floor). Both are documented, expected
states, not regressions.

---

## Where do I find…?

Everything under `build/` appears once you have run the target that writes it.
A fresh clone has no `build/` directory. See [Get the data](#get-the-data).

| I want… | Look here |
|---|---|
| the assembled figures | `build/figures/<name>/<name>_revision_partial.svg`, 12 of them |
| a quick look at a whole figure | `build/diagnostics/figure_previews/<name>.png`, 300 dpi |
| one panel | `build/panels/<figure_name>/<label>/` — SVG, PDF, PNG, `status.json`, `provenance.json` |
| the code that draws a panel | `analyses/<dir>/…` — find `<dir>` in the [figure map](docs/REPOSITORY_MAP.md#figure-to-analyses-directory-map), not by guessing the name |
| the data behind a panel | the `inputs` list in `build/provenance/<figure_name>/<label>.json` |
| the statistics behind a number in a legend | `build/statistics/<figure_name>/<label>/` |
| every number quoted in a legend, with the file and the rule that produces it | `docs/revision_2026-08-12/figure_numbers.csv` |
| the figure legends | `docs/revision_2026-08-12/legends.md` |
| the Source Data files to submit | `build/source_data/submission/`, one file per figure |
| the tables that go to the DOI repository, not to the journal | `build/source_data/deposit/` |
| the combined Source Data workbook, internal only | `build/source_data/Source_Data_revision_partial.xlsx` |
| what changed in this revision | `docs/revision_2026-08-12/change_log.md` |
| what we did not do, and why | `docs/revision_2026-08-12/not_done.md` |
| what each top-level directory holds | `docs/REPOSITORY_MAP.md` |
| what the `build/` tree contains | `docs/OUTPUT_LAYOUT.md` |
| the rule every panel must satisfy | `docs/PANEL_CONTRACT.md` |
| the pinned software environment | `docs/ENVIRONMENT.md` |

---

## Supplementary numbering

On 12 August 2026 the old Supplementary Figure 3 was withdrawn. It duplicated
the lower half of Figure 4F. The later supplementary figures moved up one
number, and for three days the directories under `analyses/` kept the old
numbers. They were renamed on 15 August 2026, so directory and figure now
agree:

| Open this directory | You get this figure | Panel IDs |
|---|---|---|
| `analyses/supplementary_03/` | **Supplementary Figure 3** | `S3_A` … `S3_I` |
| `analyses/supplementary_04/` | **Supplementary Figure 4** | `S4_A` … `S4_F` |
| `analyses/supplementary_05/` | **Supplementary Figure 5** | `S5_A` … `S5_C` |

`analyses/`, `config/`, `metadata/`, `data/` and every panel ID now use the
current numbers. `build/` does too, but still carries a few files written
before the change.
[`docs/REPOSITORY_MAP.md`](docs/REPOSITORY_MAP.md#other-places-the-old-numbers-survive)
lists each one.

Still, trust `config/panels.csv` and the panel ID over a directory name. The
full 12-row map is in
[`docs/REPOSITORY_MAP.md`](docs/REPOSITORY_MAP.md#figure-to-analyses-directory-map).
The withdrawal is recorded in `docs/revision_2026-08-12/change_log.md`.

---

## Trace a number back to its source

Take the number **110983** from the Figure 3 legend in
`docs/revision_2026-08-12/legends.md`:

> "The violin describes 110983 cell values and carries no inference."

Six hops, each verifiable:

1. **Legend → panel.** The sentence belongs to Figure 3C, so the panel ID is
   `F3_C`. The graphic is `build/panels/Figure_3/C/F3_C.svg`.
2. **Panel → provenance.** `build/provenance/Figure_3/C.json` records the
   command `.venv/bin/python3.12 -m analyses.figure_03_revision.panel_c.scripts.plot`.
   The producer is `analyses/figure_03_revision/panel_c/`.
3. **Provenance → per-panel counts.** `build/panels/Figure_3/C/summary.csv` lists
   `n_cells` per strain: 16990, 20543, 19593, 19162, 19095, 15600. They sum to
   110983.
4. **Provenance → statistics.** `build/statistics/Figure_3/C/F3_C_statistics.csv`
   holds the inference: paired two-sided t-test on replicate means, `n=2`
   biological pairs per strain, mean paired difference, 95 % CI, p value and
   Benjamini-Hochberg q value. The violin itself carries no test, which is why
   the legend says so.
5. **Provenance → source data.** The output
   `build/source_data/Figure_3/C/F3_C_source_data.csv.gz` has 110983 rows and
   sha256 `a2245640…`. It is sheet-level input to the Source Data workbook.
6. **Source data → raw input.** The provenance input
   `data/processed/figure_02/F2_F/cell_points.parquet` has 110983 rows and
   sha256 `8de33e97…`. Note the legacy directory name `figure_02/F2_F`: this
   table was migrated before the renumbering.

The chain stops there. `data/raw/` and `data/interim/` hold only `.gitkeep`.
`analyses/figure_02/panel_f/metadata/migration_inventory.json` names the legacy
file the processed table came from
(`manuscript_plots_final/…/underlying_violin_points_per_cell.csv`, 334160 rows,
sha256 `1ba51a1c…`), the filter that selected 110983 of those rows, and the
column list. The raw microscopy and the tracking files are not in this
repository. The provenance says so in its `limitations` field.

Verify hops 3, 5 and 6 with:

```bash
cat build/panels/Figure_3/C/summary.csv
.venv/bin/python -c "import pandas as pd; \
  print(len(pd.read_parquet('data/processed/figure_02/F2_F/cell_points.parquet')))"
```

---

## Current state

Every claim below names the command that proves it. Each was re-run on
15 August 2026 against this working tree. Run them yourself; that is the point
of the table.

| Fact | Command | Observed |
|---|---|---|
| 60 panels, 389 artifacts, 503 registry links | `make inventory` | `Registry inventory: 60 panels, 389 artifacts, 503 links`, exit 0 |
| 60 panel directories, 12 figure directories | `make organize` | `organized 60 panel directories and 12 figure directories`, exit 0 |
| 55 of 60 panels execute; 5 are asset-blocked | `make reproduce` preflight | `blocked_asset: F1_A, F1_B, F1_F, F1_G, F3_A`; the other 55 are listed as partial or reproduced. `make reproduce-available` records the same split in `build/workflow/available_reproduction.json` |
| 2 panels are fully reproduced, 53 partial, 5 blocked | `build/provenance/*/*.json` status fields | `reproduced: F5_D, F5_E` |
| 12 assembled figures exist | `ls build/figures/*/*_revision_partial.svg` | 12 files |
| Source Data holds 125 tables for 60 panels; 4 pre-renumbering duplicates dropped | `build/source_data/Source_Data_revision_partial.manifest.json` | `tables: 125`, `panel_records: 60`, `status: partial`, 4 `superseded_duplicates` |
| 12 per-figure Source Data files, all XLSX, largest 7.7 MB, 28.2 MB in total | `build/source_data/Source_Data_per_figure.manifest.json` | `file_count: 12`, `tables: 125`, `formats: ["xlsx"]`, `largest_file_bytes: 7744604` |
| 6 Supplementary Figure 4 trajectory tables are deposited, not submitted | `build/source_data/deposit/Supplementary_Figure_4_trajectories/MANIFEST.tsv` | 6 tables, 1,248,156 rows, 28.4 MB, DOI pending |
| exactly one panel fails print QA | `make figure-qa` | `small_font_failures: [build/panels/Figure_4/A/Figure_4_A.svg]`, no editable-text or star-text failures across 60 SVG files, one per panel, exit 2 |
| the whole test suite passes | `make test` | `130 passed in 34.39s`; the count grows as tests are added |
| Strict reproduction refuses | `make reproduce` | refuses at preflight, exit 2, lists 5 blocked and 53 partial panels |
| the central provenance store is consistent | `make audit` | `Provenance inventory: 60 documents, 0 validation errors`; `Findings: 5 errors, 0 warnings`, exit 2 |

---

## Known limitations

**Five image assets are blocked.** `F1_A`, `F1_B`, `F1_F`, `F1_G` and `F3_A`
point only to a frozen July reference, not to a regenerated output. Their panel
directories hold a status file and an explicit placeholder, never an invented
graphic. `make audit` reports each as `canonical_output_missing`.
`config/panels.csv` gives them status `needs_asset_migration`.

**Figure 4A prints too small.** `make figure-qa` fails on
`build/panels/Figure_4/A/Figure_4_A.svg`. Its smallest effective type is 2.65 pt
against a 6 pt floor. The panel embeds `assets/schematics/salmonella_model.svg`,
a collaborator asset declaring 7, 9 and 12 px in a 360×240 pt viewBox. The
48×55 mm slot scales it by 0.133. A 6 pt body text needs a slot about 64 mm
wide. Widening the slot or editing collaborator artwork are both outside the
panel. No other panel fails QA.

**Reproduction is partial, not complete.** 53 panels carry status
`partial_reproduction`. They start from migrated processed tables, not from raw
instrument output. `data/raw/` and `data/interim/` are empty. Each provenance
document states its own limitation in plain text. This is why `make reproduce`
refuses and why the workbook is named `Source_Data_revision_partial.xlsx`.

**Panel outputs are not byte-reproducible, and re-running the build breaks
`make audit` until you resynchronize.** Rerunning `make reproduce-available` on
an already-built tree writes new PDF, PNG and SVG bytes for the same panel —
tens of bytes different, from embedded creation dates and generated element
ids. The recorded checksums in `config/artifacts.csv` and in
`metadata/provenance/` then no longer match, and `make audit` reports
`artifact_sha256_mismatch` and `provenance_validation` errors on top of the
five expected ones. The numbers in the figures do not change; only the container
bytes do. Two tools, which the `Makefile` does not call, put the registry back in
step:

```bash
# analyses/**/metadata/provenance.json -> metadata/provenance/
PYTHONPATH=src .venv/bin/python tools/sync_revision_provenance.py
# build/ -> config/artifacts.csv; omit --write for a dry run
PYTHONPATH=src .venv/bin/python tools/register_partial_artifacts.py --write
make audit                       # back to the expected 5 errors
```

`PYTHONPATH=src` matters: without it both tools import the stale wheel in
`.venv`, as described two paragraphs below. Run both after every rebuild. Treat
a recorded checksum as the record of one build, not as a claim that the bytes
are deterministic.

**The installed package in `.venv` is older than `src/`.**
`make bootstrap` installs this project as a plain wheel, not as an editable
link, because macOS re-hides the editable `.pth` file. The copy at
`.venv/lib/python3.12/site-packages/flagella_repro/` therefore freezes at the
last bootstrap. It predates the renumbering. The `Makefile` sets
`PYTHONPATH=src`, so every `make` target runs live code. A hand-written
`.venv/bin/python -m flagella_repro …` does not: it reports the withdrawn panel
IDs `S4_G`…`S4_L` and `S5_D`…`S5_F` as missing. Prefix manual calls with
`PYTHONPATH=src`, or rerun `make bootstrap`.

**The environment record is stale.** `build/environment/bootstrap.json` was
written on 11 August 2026. It still says `panel_count: 56` and carries a
blocked list in the pre-revision numbering, where `F3_A` and `S3_A` denote
different panels than they do today. Rerun `make bootstrap` to refresh it. Do
not quote it.

---

## How to cite

Cite both the paper and this code release.

- **The paper.** Giralt-Zúñiga, M. J., Jahn, M., Franklin, J. L., Alagesan, K.,
  Kondrot, F., Kaganovitch, E., Hallenga, L., Derado, S., Hughes, K. T.,
  Popp, P. F., Charpentier, E., Dufour, Y. S. & Erhardt, M. *The cost-benefit
  trade-off of peritrichous flagellation in bacteria.* **[journal, year and DOI
  pending]**
- **This release.** See [`CITATION.cff`](CITATION.cff). GitHub renders it under
  **Cite this repository** on the landing page. The archival DOI is
  **[Zenodo DOI pending]**.

Related deposits, and who holds each, are listed in
[`docs/AVAILABILITY_STATEMENTS.md`](docs/AVAILABILITY_STATEMENTS.md).

---

## Licence

Read [`LICENSES.md`](LICENSES.md) before you reuse anything. Code and
documentation carry different licences, and the vendored trees carry their own:

- all of the collection's own code and configuration, including
  `models/cell_economy/` — **GPL-3.0-only**, see the [`LICENSE`](LICENSE) file
  at the root. Marc Erhardt chose this on 15 August 2026, in place of the MIT
  licence chosen earlier the same day;
- documentation, figure output and the separate data deposit — **CC-BY-4.0**;
- `models/motility_simulation/upstream/` — **MIT**, © Max Planck Unit for the
  Science of Pathogens. A byte-identical copy of
  [`MPUSP/salmonella-motility-simulation`](https://github.com/MPUSP/salmonella-motility-simulation)
  at commit `96ca0e74`;
- `models/cell_economy/upstream/` and `assets/schematics/salmonella_model.svg` —
  **GPL-3.0-only**, © M. Jahn. A byte-identical copy of
  [`m-jahn/cell-economy-models`](https://github.com/m-jahn/cell-economy-models)
  at commit `c5e534de`.

Both vendored trees keep their own `LICENSE` file and a `CHECKSUMS.sha256`
record. Do not edit them; do not relicense them. MIT stays correct for the
motility-simulation tree: MIT combines into a GPL-3.0-only work one way, and the
upstream copy itself is not relicensed.

`models/cell_economy/LICENSE` stays in place. It now names the same licence as
the root, and records that the subtree also holds third-party GPL code under a
different copyright holder.

---

## Deeper documentation

- [`docs/REPOSITORY_MAP.md`](docs/REPOSITORY_MAP.md) — every top-level directory, the figure map, the proposed renames
- [`docs/OUTPUT_LAYOUT.md`](docs/OUTPUT_LAYOUT.md) — the `build/` tree
- [`docs/PANEL_CONTRACT.md`](docs/PANEL_CONTRACT.md) — what a canonical panel must satisfy
- [`docs/FIGURE_CONTRACTS.md`](docs/FIGURE_CONTRACTS.md) — per-figure assembly contracts
- [`docs/REPRODUCIBILITY_REPORT.md`](docs/REPRODUCIBILITY_REPORT.md) — verified command outcomes and release gates
- [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md) — CPython 3.12.11, `requirements.lock`, `Dockerfile`
- [`docs/AVAILABILITY_STATEMENTS.md`](docs/AVAILABILITY_STATEMENTS.md) — draft Data and Code Availability statements, and the four planned deposits
- [`docs/DATA_AVAILABILITY.md`](docs/DATA_AVAILABILITY.md) — the working record behind them
- [`docs/SOURCE_DATA_DICTIONARY.md`](docs/SOURCE_DATA_DICTIONARY.md) — source-table columns and units
- [`docs/FETCHING_EXTERNAL_DATA.md`](docs/FETCHING_EXTERNAL_DATA.md) — retrieval contract for large and external inputs
- [`docs/SCIENTIFIC_SOURCE_INTAKE_2026-08-12.md`](docs/SCIENTIFIC_SOURCE_INTAKE_2026-08-12.md) — collaborator deliveries and acceptance
- [`docs/revision_2026-08-12/`](docs/revision_2026-08-12/) — the revision record: legends, change log, gaps, handoff

---

## Contributing

Issues and pull requests are welcome. Four rules keep the provenance chain
intact:

1. **Never edit a vendored `upstream/` tree.** Both are checksummed byte-for-byte
   copies of third-party code. Record any change in `UPSTREAM_SOURCE.md` and
   implement it beside the tree, as `models/motility_simulation/corrected/` does.
2. **Never treat a file under `build/` as an input.** Everything there is
   generated. A canonical producer that reads from `build/` has a bug.
3. **Never write an absolute or machine-local path** into canonical code or into
   a provenance document. `/tmp` and `/mnt/data` paths fail the registry tests.
4. **Run `make test` before you open a pull request.** 130 tests, about 35 s.

`docs/PANEL_CONTRACT.md` states what a canonical panel must satisfy.

## Contact

Marc Erhardt — marc.erhardt@hu-berlin.de — corresponding author.
