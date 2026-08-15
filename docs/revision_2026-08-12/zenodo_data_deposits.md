# Zenodo metadata for the two data deposits

Paste sheet for the Zenodo web form. Two records, both direct uploads. Neither
is a GitHub release, so neither is created by the GitHub integration.

Build the archives first:

```bash
make data-deposits
```

The archives land in `build/deposits/`. They are byte-reproducible: rebuild them
on another machine or another day and the sha256 does not move.

| Record | File | Bytes | sha256 |
|---|---|---|---|
| Deposit 2, data | `flagella_cost_benefit_data_v1.0.0.zip` | 60,019,267 | `2be09c8830261b0de115823d74cd7e7a25822c9cbd85008fa62e364d53d62126` |
| Deposit 3, trajectories | `flagella_cost_benefit_S4_trajectories_v1.0.0.zip` | 28,430,263 | `ee8b2b6f41f5080b2ade67fb3fec8a386d3fc5aaa9fdb3bebf97909851fb27ec` |

The numbering follows the deposit table in
[`../AVAILABILITY_STATEMENTS.md`](../AVAILABILITY_STATEMENTS.md).

---

## Before you start: reserve both DOIs

Each record names the other. Zenodo cannot give you a DOI after publication and
let you edit the other record for free, so do this in order:

1. Create both drafts. Upload the file to each.
2. On each draft, open **Digital Object Identifier** and press
   **Reserve DOI**. Zenodo shows the DOI it will mint.
3. Write each reserved DOI into the other record's related identifiers, and
   into the code record's related identifiers.
4. Publish both.

Write both minted DOIs back into `docs/AVAILABILITY_STATEMENTS.md`,
`docs/DATA_AVAILABILITY.md` and `README.md`, replacing
**[data DOI pending]** and **[trajectory DOI pending]**.

---

## Shared fields

These are the same on both records.

**Resource type:** Dataset.

**Publication date:** the day you publish.

**Version:** `1.0.0`. It matches the code release, the git tag, `CITATION.cff`
and `.zenodo.json`.

**Language:** English (eng).

**Access:** Open.

**Licence:** Creative Commons Attribution 4.0 International (CC-BY-4.0).
Zenodo identifier `cc-by-4.0`.

The code release is GPL-3.0-only. The data are CC-BY-4.0. Different records,
different licences, on purpose. `LICENSES.md` in the repository holds the map
and is the authority.

**One licence exception, in the data record only.** `LICENSES.md` puts
`data/external/cell_economy_results/` (28 files, 236 kB) under **GPL-3.0-only**,
following the licence of the delivering package rather than the deposit. Zenodo
holds one licence per record, so the record licence stays CC-BY-4.0 and the
exception is named in the description and in the archive `README.txt`. This is
the same pattern the code record already uses for the two vendored upstream
trees. Marc should confirm the exception before publishing; if he would rather
not mix licences in one record, the alternative is to drop that tree from the
archive, which would leave the cell-economy panels unbuildable.

### Creators

Thirteen, in this order. Taken verbatim from `CITATION.cff`. Zenodo's name
field takes `Family, Given`.

| # | Name | Affiliation | ORCID |
|---|---|---|---|
| 1 | Giralt-Zúñiga, María José | Max Planck Unit for the Science of Pathogens, Berlin, Germany; Institute of Biology/Molecular Microbiology, Humboldt-Universität zu Berlin, Berlin, Germany | — |
| 2 | Jahn, Michael | Max Planck Unit for the Science of Pathogens, Berlin, Germany | 0000-0002-3913-153X |
| 3 | Franklin, Joshua L. | Department of Microbiology and Molecular Genetics, Michigan State University, East Lansing, MI, USA | — |
| 4 | Alagesan, Kathirvel | Max Planck Unit for the Science of Pathogens, Berlin, Germany | — |
| 5 | Kondrot, Florian | Max Planck Unit for the Science of Pathogens, Berlin, Germany | — |
| 6 | Kaganovitch, Eugen | Institute of Biology/Molecular Microbiology, Humboldt-Universität zu Berlin, Berlin, Germany | — |
| 7 | Hallenga, Lasse | Institute of Biology/Molecular Microbiology, Humboldt-Universität zu Berlin, Berlin, Germany | — |
| 8 | Derado, Sarya | Institute of Biology/Molecular Microbiology, Humboldt-Universität zu Berlin, Berlin, Germany | — |
| 9 | Hughes, Kelly T. | School of Biological Sciences, University of Utah, Salt Lake City, Utah, USA | — |
| 10 | Popp, Philipp F. | Institute of Biology/Molecular Microbiology, Humboldt-Universität zu Berlin, Berlin, Germany | — |
| 11 | Charpentier, Emmanuelle | Max Planck Unit for the Science of Pathogens, Berlin, Germany | — |
| 12 | Dufour, Yann S. | Department of Microbiology and Molecular Genetics, Michigan State University, East Lansing, MI, USA | — |
| 13 | Erhardt, Marc | Max Planck Unit for the Science of Pathogens, Berlin, Germany; Institute of Biology/Molecular Microbiology, Humboldt-Universität zu Berlin, Berlin, Germany | — |

Only Michael Jahn's ORCID could be verified inside this repository. Leave every
other ORCID field empty. Do not guess: a wrong ORCID points at a different
person, and Zenodo rejects a malformed one.

### Keywords

Both records get the nine keywords of the code record, from `CITATION.cff`:

```
flagella
bacterial motility
Salmonella enterica
proteome allocation
growth trade-off
cost-benefit trade-off
reproducible research
figure reproduction
Snakemake
```

Add these two to the data record:

```
source data
research data
```

Add these two to the trajectory record instead:

```
agent-based simulation
cell trajectories
```

---

## Relation vocabulary, verified

Zenodo takes its relation types from the DataCite metadata schema. I checked
each one used below against the DataCite 4.6 controlled list
(`https://datacite-metadata-schema.readthedocs.io/en/4.6/appendices/appendix-1/relationType/`),
where the definitions read, with A the record you are editing and B the
identifier you enter:

| Relation | DataCite definition |
|---|---|
| `isSupplementTo` | "indicates that A is a supplement to B" |
| `isSupplementedBy` | "indicates that B is a supplement to A" |
| `isPartOf` | "indicates A is a portion of B; may be used for elements of a series" |
| `hasPart` | "indicates A includes the part B" |
| `isDerivedFrom` | "indicates B is a source upon which A is based" |

What that gives:

- The data records supplement the paper, so each names the manuscript DOI with
  **`isSupplementTo`**. Not the reverse: the paper is not a supplement to the
  data.
- The data records also supplement the code release, so each names the code
  version DOI with **`isSupplementTo`**. The code record already plans the
  reciprocal `isSupplementedBy` towards the data record — see note (4) in
  `.zenodo.json`. The pair is consistent.
- The trajectory bundle is a subset of the data archive, byte for byte. The
  trajectory record therefore uses **`isPartOf`** towards the data record, and
  the data record uses **`hasPart`** towards the trajectory record. This is
  more precise than a second supplement relation, and it tells a downloader
  that one download can replace two.
- The trajectories are the output of the upstream motility simulation, so the
  trajectory record names that repository with **`isDerivedFrom`**, matching
  what the code record already does.

Rejected on purpose: `isIdenticalTo` (the two archives are not identical, only
overlapping), `isCitedBy` (nothing cites them yet) and `isCompiledBy` (it
describes a compilation tool, not a data-to-code dependency).

---

## Record 1 — the data deposit

**Upload file:** `build/deposits/flagella_cost_benefit_data_v1.0.0.zip`

### Title

```
Input data for the figures of "The cost-benefit trade-off of peritrichous flagellation in bacteria"
```

### Description

Paste as HTML. Replace the sha256 line only if you rebuilt the archive.

```html
<p>The input data behind every figure of the manuscript <em>"The cost-benefit trade-off of peritrichous flagellation in bacteria"</em> (Giralt-Z&uacute;&ntilde;iga et al.). Download this record, unzip it at the root of a clone of the analysis code, and the figure panels rebuild.</p>

<p><strong>Contents.</strong> One zip archive with three trees, 256 files and 145.6 MB uncompressed:</p>
<ul>
<li><code>data/external/</code> — 39 files. Collaborator deliveries: the promoter-series proteomics tables and the cell-economy model results.</li>
<li><code>data/processed/</code> — 83 files. Processed measurement tables. Most panel producers read from here.</li>
<li><code>data/source_data/</code> — 134 files. The registered per-panel source tables, one directory per figure.</li>
</ul>
<p>The archive also carries <code>README.txt</code> and <code>CHECKSUMS.tsv</code>. <code>CHECKSUMS.tsv</code> lists every file with its size and its sha256.</p>

<p><strong>How to use it.</strong> Clone <code>https://github.com/SalmoLab/salmonella-flagella-cost-benefit</code> at tag <code>v1.0.0</code>, unzip this archive at the repository root, then run <code>make bootstrap</code> and <code>make reproduce-available</code>. 55 of the 60 panels have a registered source and rebuild from these tables. Five image panels have no registered source asset and render a labelled placeholder; the repository README names them. This is a stated limit of the collection.</p>

<p><strong>What these tables are.</strong> They are not raw instrument output. They are the registered starting points of the panel producers, recorded one by one in <code>config/artifacts.csv</code> of the code release, each with its sha256. Raw mass-spectrometry files are deposited separately in ProteomeXchange through PRIDE. Raw microscopy and tracking files are not part of this collection, and each affected provenance document says so.</p>

<p><strong>Overlap with the trajectory record.</strong> <code>data/source_data/supplementary_04/</code> holds the six simulated-trajectory tables of Supplementary Figure 4. The separate record <em>"Simulated trajectories of Supplementary Figure 4"</em> holds the same six files, byte for byte, with the seeds and the regeneration command of each one. This archive keeps them so that it rebuilds every available panel on its own. You need only one of the two downloads.</p>

<p><strong>Archive checksum.</strong> <code>flagella_cost_benefit_data_v1.0.0.zip</code>, 60,019,103 bytes, sha256 <code>2be09c8830261b0de115823d74cd7e7a25822c9cbd85008fa62e364d53d62126</code>. The archive is byte-reproducible: <code>make data-deposits</code> in the code release rebuilds it with the same checksum.</p>

<p><strong>Licence.</strong> CC-BY-4.0, with one exception: <code>data/external/cell_economy_results/</code> (28 files) keeps <strong>GPL-3.0-only</strong>, the licence of the cell-economy models package it came from (M. Jahn). The full GPL-3.0 text ships with the code release. <code>LICENSES.md</code> in the code repository holds the per-directory map and is the authority. The analysis code is a separate record under GPL-3.0-only.</p>
```

### Related identifiers

| Identifier | Relation | Resource type |
|---|---|---|
| *[manuscript DOI]* | isSupplementTo | Publication / Journal article |
| `10.5281/zenodo.21950614` | isSupplementTo | Software |
| *[reserved trajectory DOI]* | hasPart | Dataset |
| `https://github.com/SalmoLab/salmonella-flagella-cost-benefit` | isSupplementTo | Software |

Add the manuscript row only once the paper has a DOI. Zenodo rejects a
placeholder.

Use the **version** DOI `10.5281/zenodo.21950614`, not the concept DOI
`10.5281/zenodo.21950613`. The concept DOI resolves to whatever version is
newest, and a future v2.0.0 need not reproduce these figures.

---

## Record 2 — the trajectory deposit

**Upload file:** `build/deposits/flagella_cost_benefit_S4_trajectories_v1.0.0.zip`

### Title

```
Simulated trajectories of Supplementary Figure 4 of "The cost-benefit trade-off of peritrichous flagellation in bacteria"
```

### Description

```html
<p>The six simulated-trajectory tables behind Supplementary Figure 4 of the manuscript <em>"The cost-benefit trade-off of peritrichous flagellation in bacteria"</em> (Giralt-Z&uacute;&ntilde;iga et al.).</p>

<p><strong>Contents.</strong> Six gzip-compressed CSV tables, <code>S4_A</code> to <code>S4_F_simulated_trajectories.csv.gz</code>, 1,248,156 rows in total. Each table holds the position of every simulated cell at every time step of one panel: 26 cells over 8001 steps, at a 0.0025 s time step across 20 s. The archive also carries <code>README.txt</code>, <code>MANIFEST.tsv</code> and <code>CHECKSUMS.tsv</code>. <code>MANIFEST.tsv</code> gives, for every table, the row and column count, the sha256, the three random seeds, the exact regeneration command and the provenance record in the code release.</p>

<p><strong>Why these are deposited and not supplied as Source Data.</strong> They are model output, not measurement. They are exactly regenerable from the recorded seeds and parameters, they exceed the journal file limit, and no reader re-derives a plotted value by hand from 208,026 rows. Source Data Supplementary Figure 4, supplied with the paper, carries the obstacle fields and two summary tables derived from these trajectories, from which every plotted value can be checked. This record is for a reader who wants the full model output.</p>

<p><strong>Provenance.</strong> Produced by the agent-based motility simulation at <code>https://github.com/MPUSP/salmonella-motility-simulation</code>, commit <code>96ca0e741c8c4990b1cfa59b2daafee59d74cb7b</code> (MIT), through the analysis code release. Software: python 3.12.11, numpy 2.5.2, pandas 2.3.3, matplotlib 3.11.1, pyyaml 6.0.3.</p>

<p><strong>Relation to the data record.</strong> The data deposit of this collection contains a byte-identical copy of these six tables at <code>data/source_data/supplementary_04/</code>. This record publishes them on their own because the manuscript Data Availability statement cites them separately.</p>

<p><strong>Archive checksum.</strong> <code>flagella_cost_benefit_S4_trajectories_v1.0.0.zip</code>, 28,430,263 bytes, sha256 <code>ee8b2b6f41f5080b2ade67fb3fec8a386d3fc5aaa9fdb3bebf97909851fb27ec</code>. The archive is byte-reproducible: <code>make data-deposits</code> in the code release rebuilds it with the same checksum.</p>

<p><strong>Licence.</strong> CC-BY-4.0. The analysis code is a separate record under GPL-3.0-only; the upstream simulation is MIT.</p>
```

### Related identifiers

| Identifier | Relation | Resource type |
|---|---|---|
| *[manuscript DOI]* | isSupplementTo | Publication / Journal article |
| `10.5281/zenodo.21950614` | isSupplementTo | Software |
| *[reserved data DOI]* | isPartOf | Dataset |
| `https://github.com/MPUSP/salmonella-motility-simulation` | isDerivedFrom | Software |

Add the manuscript row only once the paper has a DOI.

---

## After publication

1. Check that each DOI resolves from a browser that is not signed in to the
   depositing account.
2. Check that the sha256 Zenodo prints beside each file matches the table at
   the top of this page.
3. Replace **[data DOI pending]** and **[trajectory DOI pending]** in
   `docs/AVAILABILITY_STATEMENTS.md`, `docs/DATA_AVAILABILITY.md` and
   `README.md`.
4. Edit the code record `10.5281/zenodo.21950614` and add both data DOIs with
   relation `isSupplementedBy`, resource type Dataset. Note (4) in
   `.zenodo.json` records this step.
5. Record the licence of both deposits in `LICENSES.md`.
