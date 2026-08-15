# Data and Code Availability — draft statements

Draft text for the manuscript, in Nature Communications style. Every identifier
that does not exist yet is written as a bracketed placeholder in **bold**.
Do not submit while a placeholder remains.

This file is the submission-ready wording. The working record of what is still
open is [`DATA_AVAILABILITY.md`](DATA_AVAILABILITY.md). If the two disagree, the
working record wins and this file is wrong.

---

## The five planned deposits

| # | What | Where | Who acts | Identifier |
|---|---|---|---|---|
| 1 | Mass-spectrometry proteomics: raw files, identification and quantification output | ProteomeXchange, through the PRIDE partner repository | Kathirvel Alagesan | **[PXD pending]** |
| 2 | The processed input tables, the external deliveries and the figure source data | Zenodo, direct upload | Marc Erhardt | **[data DOI pending]** |
| 3 | The Supplementary Figure 4 simulated-trajectory bundle | Zenodo, direct upload | Marc Erhardt | **[trajectory DOI pending]** |
| 4 | Motility simulation source code | Zenodo, through a GitHub release of `MPUSP/salmonella-motility-simulation` | Michael Jahn | **[motility DOI pending]** |
| 5 | This analysis and figure collection | Zenodo, through a GitHub release | Marc Erhardt | **10.5281/zenodo.21951357** (v1.0.1) |

Deposits 4 and 5 are separate records. The motility simulation is a third-party
MIT code base with its own authorship; it is cited, not absorbed.

Deposits 2 and 3 are separate records for a reason. Deposit 2 is what a reader
unzips to rebuild a panel. Deposit 3 is the trajectory bundle that the Data
Availability statement names on its own, with the seeds and the regeneration
command of every table. Deposit 2 contains a byte-identical copy of the six
trajectory tables, so that it reproduces every available panel without a second
download. The two records point at each other through their Zenodo related
identifiers.

`make data-deposits` builds both archives, byte for byte the same on every run.
The metadata to paste into the Zenodo web form, including the sha256 of each
archive, is in
[`revision_2026-08-12/zenodo_data_deposits.md`](revision_2026-08-12/zenodo_data_deposits.md).

**Version DOI, not concept DOI.** Zenodo mints both. The concept DOI,
10.5281/zenodo.21950613, resolves to whatever version is newest; a future
v2.0.0 would answer it and would not reproduce these figures. Every statement
below therefore cites the version DOI, **10.5281/zenodo.21951357**, and names
the concept DOI only as the pointer to the current version. The repository
badge and `CITATION.cff` keep the concept DOI, which is correct there.

---

## Data Availability

> The mass-spectrometry proteomics data generated in this study, including the
> raw files and the identification and quantification output, have been
> deposited in the ProteomeXchange Consortium via the PRIDE partner repository
> under accession code **[PXD pending]**. The processed data tables underlying
> every figure, together with the associated metadata, have been deposited in
> Zenodo under **[data DOI pending]**. The simulated trajectories of
> Supplementary Figure 4 have been deposited in Zenodo under
> **[trajectory DOI pending]**, and are also contained in the data deposit.
> They are deposited rather than supplied as Source Data because they are
> exactly regenerable model output; the Source Data file for that figure
> contains the per-condition and per-cell summary tables from which every
> plotted value can be checked. Source data are provided with this paper.

**Notes for the submitting author.**

- Nature Communications wants the sentence "Source data are provided with this
  paper" verbatim when a Source Data file is supplied. It is kept at the end.
- `make source-data-available` writes twelve Source Data files, one per figure,
  to `build/source_data/submission/`. The combined workbook
  `build/source_data/Source_Data_revision_partial.xlsx` is internal and must not
  be submitted.
- The trajectory split was approved on 14 August 2026. Its full rationale, the
  row counts and the checksums are in
  [`DATA_AVAILABILITY.md`](DATA_AVAILABILITY.md#supplementary-figure-4-trajectory-deposit).
- Both Zenodo data records are direct uploads, not GitHub releases. Reserve the
  DOI on each draft before you publish either one, so that each record can name
  the other. See
  [`revision_2026-08-12/zenodo_data_deposits.md`](revision_2026-08-12/zenodo_data_deposits.md).
- Both data deposits are CC-BY-4.0. The code release is GPL-3.0-only. They are
  different records and different licences on purpose.
- Raw microscopy data are not yet assigned a repository. If they stay
  undeposited, add one sentence naming what is available from the corresponding
  author on request, and say why. Do not leave it silent.

---

## Code Availability

> The analysis, simulation and figure-generation code that reproduces the
> results of this study is available at
> `https://github.com/`**SalmoLab/salmonella-flagella-cost-benefit** and is
> archived at Zenodo under **10.5281/zenodo.21951357** (release v1.0.0). The
> release contains the pinned Python 3.12
> environment, the workflow definition, the panel registry, the model
> parameters, the random seeds and the exact reproduction commands. The
> coarse-grained cell-economy model of Jahn et al. is included as an unmodified
> vendored copy of `https://github.com/m-jahn/cell-economy-models` at commit
> `c5e534de7e2102d330356ecb6e78f6346f3cc14a`, under its own GPL-3.0-only licence. The
> agent-based motility simulation is available at
> `https://github.com/MPUSP/salmonella-motility-simulation` at commit
> `96ca0e741c8c4990b1cfa59b2daafee59d74cb7b` under an MIT licence, archived at
> Zenodo under **[motility DOI pending]**; the corrections applied in this study
> are documented and version-controlled within the analysis code release.

**Notes for the submitting author.**

- Nature Communications asks for an archival identifier, not a bare repository
  URL. The Zenodo DOI carries that role. Keep both: the URL for a reader who
  wants the living repository, the DOI for the citable record.
- The statement cites the **version DOI** of the tagged release,
  10.5281/zenodo.21951357, not the concept DOI. This is the point of the
  statement: the concept DOI, 10.5281/zenodo.21950613, resolves to the newest
  version, and a later version need not reproduce these figures. The concept
  DOI belongs in `CITATION.cff` and on the repository badge, and both keep it.
- If a referee asks for the living record rather than the frozen one, add one
  clause: "the concept DOI 10.5281/zenodo.21950613 resolves to the current
  version". Do not replace the version DOI with it.
- Both vendored commits and both licences are verified against the repository
  and are recorded in `models/*/upstream/UPSTREAM_SOURCE.md` and
  [`../LICENSES.md`](../LICENSES.md).
- The motility DOI depends on Michael Jahn making a GitHub release. Until he
  does, the sentence cannot be completed. Confirm with him that commit
  `96ca0e74` is the version to cite.
- **Release v1.0.0 is incomplete, and a v1.0.1 must fix it.** `.gitignore`
  carried an unanchored `data/` rule, so it also excluded
  `models/motility_simulation/upstream/data/`. A clone therefore lost
  `config.yml` and `motility_summary_parameters.csv`, and Supplementary
  Figures 4 and 5 could not build from a clone at all. The upstream
  `CHECKSUMS.sha256` lists both files, so the vendored tree contradicted its
  own record and the phrase "unmodified vendored copy" above was not true of
  the clone. The rule is now anchored to `/data/`. Add the two files, tag
  v1.0.1, let Zenodo mint a new version DOI, and cite that DOI in the
  statement. Verified on 15 August 2026: with the two files restored, all six
  Supplementary Figure 4 panels build from a fresh clone plus the data deposit.

---

## The honest-limits sentence

The collection reproduces 55 of 60 panels and two of them end to end. A reviewer
who clones the repository and finds `make reproduce` refusing should not be
surprised by it. One sentence in the Methods removes that surprise. Suggested
wording:

> Figure panels are regenerated from registered processed data tables with
> recorded provenance; the code release states, per panel, which panels start
> from processed rather than raw instrument output and which five image panels
> could not be regenerated from a registered source.

This is a suggestion, not a requirement. It costs one sentence and it forecloses
a referee question.

---

## Release gate

Do not finalize either statement until all six conditions hold:

1. every accession and DOI resolves from a browser that is not signed in to the
   depositing account;
2. the licence of every deposit is recorded in `config/artifacts.csv` and in
   [`../LICENSES.md`](../LICENSES.md);
3. the tagged code release passes `make test` and a clean-room build against the
   exact deposited data version;
4. `.zenodo.json`, `CITATION.cff` and these statements name the same title,
   authors, version and licence;
5. the sha256 printed on each Zenodo record page matches the sha256 recorded in
   [`revision_2026-08-12/zenodo_data_deposits.md`](revision_2026-08-12/zenodo_data_deposits.md);
6. each of the two data records names the other in its related identifiers, and
   the code record names both.
