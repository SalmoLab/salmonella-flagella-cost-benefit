# Data and code availability work record

This file records unresolved repository actions. It is not yet a submission-ready
statement and must not contain invented accessions or DOIs.

## Planned access routes

- Mass-spectrometry proteomics: PRIDE/ProteomeXchange accession — **pending**.
- Other raw and processed source data: stable DOI-bearing repository — **pending**.
- Supplementary Figure 4 simulated trajectories: the same DOI-bearing
  repository. The bundle is built and checksummed; only the DOI is
  **pending**. See [the deposit section](#supplementary-figure-4-trajectory-deposit).
- Canonical code and workflow release: versioned repository plus archived DOI —
  **pending**.
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

**Where it will live.** The DOI-bearing repository, **[repository and DOI
pending]**. Do not invent an accession. The build writes the same bundle to
`build/source_data/deposit/Supplementary_Figure_4_trajectories/`.

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

### Data Availability

The raw mass-spectrometry proteomics data and associated identification and
quantification files will be deposited in the ProteomeXchange Consortium through
the PRIDE partner repository under accession **[PXD pending]**. Processed data,
figure source-data tables, microscopy source material and associated metadata will
be deposited under **[repository and DOI pending]**. Repository records and this
statement must be updated together before submission.

### Code Availability

The versioned analysis, simulation and figure-generation code required to
reproduce the manuscript results will be available from **[repository pending]**
and archived under **[DOI pending]**. The release will include a Python 3.12
environment lock, workflow definition, model parameters, random seeds and exact
reproduction commands. The cell-economy model source and licence remain pending
receipt and verification of the final collaborator package.

## Release gate

Do not finalize these statements until reviewer links/accessions resolve outside
the depositor account, licences are recorded, and a clean-room build has passed
against the exact deposited versions.
