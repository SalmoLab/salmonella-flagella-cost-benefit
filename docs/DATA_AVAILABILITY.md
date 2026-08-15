# Data and code availability work record

This file records unresolved repository actions. It is not yet a submission-ready
statement and must not contain invented accessions or DOIs.

## Planned access routes

- Mass-spectrometry proteomics: PRIDE/ProteomeXchange accession — **pending**.
- Other processed and source data: Zenodo, direct upload. The archive is built
  and checksummed; only the DOI is **pending**. See
  [the archive section](#the-two-built-data-archives).
- Supplementary Figure 4 simulated trajectories: a second Zenodo record, direct
  upload. The bundle is built and checksummed; only the DOI is **pending**. See
  [the deposit section](#supplementary-figure-4-trajectory-deposit).
- Canonical code and workflow release: done. GitHub release `v1.0.0` of
  `SalmoLab/salmonella-flagella-cost-benefit`, archived at Zenodo under version
  DOI **10.5281/zenodo.21950614**; concept DOI **10.5281/zenodo.21950613**.
- Microscopy raw data: repository/location and size assessment — **pending**.
- External cell-economy model: exact commit, licence and archival permission —
  **pending collaborator package**.
- External motility simulation: Michael Jahn set the repository public on
  13 August 2026. Our frozen snapshot records the URL
  `https://github.com/MPUSP/salmonella-motility-simulation`, commit
  `96ca0e741c8c4990b1cfa59b2daafee59d74cb7b` and an MIT licence, all taken from
  the delivery rather than from the public repository. Confirm the citable URL,
  commit and licence against the public repository, and agree an archival DOI —
  **pending**.

## The two built data archives

`make data-deposits` writes both Zenodo uploads to `build/deposits/`. Both are
byte-reproducible; a rebuild gives the same sha256.

| Archive | Bytes | sha256 |
|---|---|---|
| `flagella_cost_benefit_data_v1.0.0.zip` | 60,019,267 | `2be09c8830261b0de115823d74cd7e7a25822c9cbd85008fa62e364d53d62126` |
| `flagella_cost_benefit_S4_trajectories_v1.0.0.zip` | 28,430,263 | `ee8b2b6f41f5080b2ade67fb3fec8a386d3fc5aaa9fdb3bebf97909851fb27ec` |

The data archive holds `data/external/` (39 files), `data/processed/`
(83 files) and `data/source_data/` (134 files): 256 files, 145.6 MB
uncompressed. It unzips at the repository root and reproduces every panel that
has a registered source. All 98 registered `data/` artifacts of
`config/artifacts.csv` resolve from it with the recorded sha256.

Two decisions are recorded here because a reader of the deposit will ask.

**`data/source_data/` is included.** It was populated by migration scripts, so
it is generated rather than collected. It is nonetheless the registered input of
eight panel producers — `figure_04_revision`, `figure_05_revision`,
`figure_06_revision`, `figure_07_revision`, `supplementary_03`,
`supplementary_04`, `collaborator_science` and the `s2_a` report — and
`config/artifacts.csv` registers 35 of its files as `partial_source_data`
inputs. Leaving it out would make the archive smaller and the deposit
unusable.

**`data/source_data/superseded_2026-07/` is excluded.** Nine directories of
source data for the July 2026 figure layout, 60 kB. Nothing in the code reads
them and no figure in the paper plots them. Publishing them beside the paper
would invite a reader to plot panels the paper withdrew. They stay on disk and
with the authors, as their own `README.md` intends, and are available on
request. Size played no part in this: it is 0.04 % of the archive.

`.DS_Store`, `__pycache__` and `.gitkeep` are excluded as machine litter and
repository placeholders.

**One licence exception.** [`../LICENSES.md`](../LICENSES.md) puts
`data/external/cell_economy_results/` (28 files, 236 kB) under GPL-3.0-only,
following the delivering package rather than the deposit. A Zenodo record holds
one licence, so the record licence is CC-BY-4.0 and the archive `README.txt`
names the exception. Confirm this before publishing.

The metadata for both Zenodo records is in
[`revision_2026-08-12/zenodo_data_deposits.md`](revision_2026-08-12/zenodo_data_deposits.md).

## Source Data files

`make source-data-available` writes one Source Data file per figure to
`build/source_data/submission/`: `Source Data Figure 1` to `Source Data
Figure 7`, and `Source Data Supplementary Figure 1` to `5`. Twelve files. This
matches the Nature Communications rule of one file per figure and the 30 MB
per-file cap.

Each file stands on its own. It carries a README, an INDEX and a
DATA_DICTIONARY for its own tables, so a reviewer who opens one file alone can
read it. A figure ships as `.xlsx` when it stays within the cap, and as a `.zip`
of tab-separated `.txt` files when it does not. The layout and the unit
convention are described in
[`SOURCE_DATA_DICTIONARY.md`](SOURCE_DATA_DICTIONARY.md).

The combined workbook `build/source_data/Source_Data_revision_partial.xlsx` is
kept for internal use. It must not be submitted.

## Supplementary Figure 4 trajectory deposit

Marc approved this split on 14 August 2026. The six simulated-trajectory tables
of Supplementary Figure 4 are deposited, not submitted.

**What the deposit contains.** Six gzip-compressed CSV tables,
`S4_A` to `S4_F_simulated_trajectories.csv.gz`, 1,248,156 rows in total,
28.4 MB compressed. Each holds the position of every simulated cell at every
time step: 26 cells × 8001 steps at a 0.0025 s time step over 20 s. The bundle
also carries `README.txt` and `MANIFEST.tsv`, which list the sha256, the seeds
and the exact regeneration command of every table.

**Where it will live.** Its own Zenodo record, **[trajectory DOI pending]**. Do
not invent an accession. `make source-data-available` writes the bundle to
`build/source_data/deposit/Supplementary_Figure_4_trajectories/`, and
`make data-deposits` packages it unchanged, adding a deposit-level `README.txt`
and a `CHECKSUMS.tsv`. The data archive carries a byte-identical copy of the six
tables, so a reader who wants to reproduce the panel needs only that one
download.

**Why it is deposited rather than submitted.** The tables are raw model output,
not measurement. No reviewer will re-derive a figure value by hand from 208,026
rows. They are exactly regenerable from the recorded seeds and parameters. They
were 57.6 % of the Source Data volume and forced the one format exception in an
otherwise uniform package.

**What replaces them.** `Source Data Supplementary Figure 4` keeps the six
obstacle fields and adds two tables derived from the trajectories:

- `S4_condition_summary` — one row per panel. The model inputs the legend
  quotes (motile fraction, run speed, reorientation rate, stall probability),
  the three seeds, the obstacle geometry, and the population statistics of the
  drawn tracks.
- `S4_cell_summary` — one row per simulated cell, 156 rows. Start and end
  position, net displacement, maximum excursion, track path length, mean track
  speed, and the final state of every track the figure draws.

A reader can check the figure from these two tables alone. The Source Data
README states what was deposited, why, where it will live and how to regenerate
it, and lists the sha256 of every deposited table.

## Draft manuscript sections

The submission-ready wording now lives in
[`AVAILABILITY_STATEMENTS.md`](AVAILABILITY_STATEMENTS.md). Only the open items
stay here.

### Data Availability — still open

- The PRIDE/ProteomeXchange accession, **[PXD pending]**. Kathirvel Alagesan
  acts.
- The two Zenodo data DOIs, **[data DOI pending]** and
  **[trajectory DOI pending]**. Both archives are built and checksummed. Marc
  Erhardt uploads.
- Microscopy raw data have no repository. If they stay undeposited, the
  statement needs one sentence naming what the corresponding author can supply,
  and why.

### Code Availability — settled

The code is released and archived: GitHub release `v1.0.0` of
`SalmoLab/salmonella-flagella-cost-benefit`, version DOI
**10.5281/zenodo.21950614**, concept DOI **10.5281/zenodo.21950613**. The
statement cites the version DOI, because the concept DOI resolves to whatever
version is newest.

One item stays open: the motility-simulation DOI, **[motility DOI pending]**,
which depends on Michael Jahn making a GitHub release.

## Release gate

Do not finalize these statements until reviewer links/accessions resolve outside
the depositor account, licences are recorded, and a clean-room build has passed
against the exact deposited versions.
