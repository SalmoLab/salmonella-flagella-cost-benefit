# Analysis and figure code: the cost-benefit trade-off of peritrichous flagellation in bacteria

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21950613.svg)](https://doi.org/10.5281/zenodo.21950613)

Code that produces the figures of Giralt-Zúñiga et al., "The cost-benefit
trade-off of peritrichous flagellation in bacteria": seven main figures, five
supplementary figures, 60 panels.

Every panel has one producer script under `analyses/`, one output directory
under `build/panels/`, and one provenance document recording its inputs,
software versions and random seeds. `docs/PANEL_CONTRACT.md` describes the
rule; `docs/REPOSITORY_MAP.md` explains the directory layout.

## Requirements

Python 3.12 and `make`. `make bootstrap` installs uv 0.8.11 and CPython
3.12.11, creates `.venv` from `uv.lock`, and writes the environment record to
`build/environment/bootstrap.json`. Exact package versions are listed in
`docs/revision_2026-08-12/software_versions.md`.

Figure rendering also needs `rsvg-convert` (librsvg) and Ghostscript, which are
not installed by `make bootstrap`.

## Data

The data are not in this repository. A clone reproduces nothing until you add
them. Download the data deposit (**[data DOI pending]**, see
`docs/AVAILABILITY_STATEMENTS.md`) and unzip it at the repository root, so that
`data/processed/`, `data/external/` and `data/source_data/` sit there. The
archive unzips to exactly that layout. It also writes `README.txt` and
`CHECKSUMS.tsv` beside them; neither collides with a repository file and you
may delete both.

That deposit already carries the six simulated-trajectory tables of
Supplementary Figure 4. They are published a second time as their own record
(**[trajectory DOI pending]**), because the manuscript Data Availability
statement cites them separately. For reproduction you need only the data
deposit.

`data/raw/` and `data/interim/` hold no data. Raw microscopy and tracking files
are not part of this collection; each provenance document that depends on them
says so in its `limitations` field.

`reference/` and `archive/` are frozen internal baselines. They are not
deposited, and no panel reads them.

## Usage

| Command | Purpose |
|---|---|
| `make bootstrap` | Create the pinned environment. Once. |
| `make inventory` | Validate the registries in `config/`. |
| `make reproduce-available` | Run every panel with a registered source (~30 min). |
| `make figure-qa` | Render previews, colour-vision simulations, check font sizes. |
| `make source-data-available` | Build one Source Data file per figure. |
| `make data-deposits` | Build the two Zenodo data archives in `build/deposits/`. |
| `make supplementary-information` | Build the combined Supplementary PDF. |
| `make audit` | Cross-check registries, outputs and provenance. |
| `make test` | Run the test suite. |
| `make reproduce` | Strict gate. Refuses while any panel is incomplete. |

Assembled figures are written to `build/figures/`, single panels to
`build/panels/<figure>/<label>/`, statistics to `build/statistics/`, and
300 dpi previews to `build/diagnostics/figure_previews/`.

`make audit` and `make figure-qa` exit non-zero, and `make reproduce` refuses.
These are the expected states described under Limitations, not failures.

## Supplementary figure numbering

The former Supplementary Figure 3 was withdrawn on 12 August 2026 because it
duplicated part of Figure 4F, and the later supplementary figures moved up one
number. Directories under `analyses/` were renamed to match on 15 August 2026,
so `analyses/supplementary_03/` builds Supplementary Figure 3, `_04` builds 4
and `_05` builds 5.

A few files under `build/` predate the change. When a directory name and a
panel ID disagree, `config/panels.csv` is authoritative. The full mapping is in
`docs/REPOSITORY_MAP.md`.

## Limitations

Five panels — Figure 1A, 1B, 1F, 1G and Figure 3A — have no registered source
asset. They render a labelled placeholder rather than an invented graphic, and
are the reason `make reproduce` refuses. Figure 6E likewise draws no scale bar,
because the calibrated microscopy fields are not available and a scale bar
inferred from apparent cell size would be a guess.

Of the 60 panels, 55 execute from a registered source. Two reproduce from raw
inputs; the rest start from migrated processed tables. Figure 4A embeds a
collaborator schematic whose smallest label falls below the 6 pt print
threshold, which is why `make figure-qa` exits non-zero.

Panel outputs are not byte-reproducible: SVG and PDF carry creation timestamps
and generated element identifiers. After any rebuild, run
`tools/sync_revision_provenance.py` and then
`tools/register_partial_artifacts.py --write` to resynchronise the recorded
checksums.

## Documentation

`docs/REPOSITORY_MAP.md` covers the directory layout,
`docs/PANEL_CONTRACT.md` the rule every panel follows, and
`docs/OUTPUT_LAYOUT.md` the contents of `build/`. The revision record,
including figure legends, the change log and the parameter sources for the
motility simulation, is in `docs/revision_2026-08-12/`.

## Citation

Cite the manuscript, and this repository through its Zenodo DOI
10.5281/zenodo.21950613, which always resolves to the current version.

To cite the exact code that produced the published figures, use the version DOI
of the release instead: 10.5281/zenodo.21950614 (v1.0.0). A later version may
not reproduce them. Machine-readable metadata is in `CITATION.cff`.

## Licence

GPL-3.0-only for the code, CC-BY-4.0 for documentation and figures. The
vendored upstream code keeps its own licences: MIT for the motility simulation
(Max Planck Unit for the Science of Pathogens) and GPL-3.0-only for the
cell-economy models (M. Jahn). `COPYRIGHT` names the copyright holders and the
scope; `LICENSES.md` maps every directory and takes precedence.

## Contact

Marc Erhardt, Humboldt-Universität zu Berlin — marc.erhardt@hu-berlin.de
