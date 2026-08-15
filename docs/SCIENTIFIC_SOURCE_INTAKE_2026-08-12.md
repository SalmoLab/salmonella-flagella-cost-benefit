# Scientific source intake — 12 August 2026

## Frozen deliveries

| Delivery | Files | Bytes | Manifest SHA-256 | Code identity |
|---|---:|---:|---|---|
| Proteomics and cell-economy package | 175 | 129,335,384 | `d5443d716a7e1f9e931dbde0ee242a89030e4d67f1b65a3c218f31f70147f081` | `m-jahn/cell-economy-models@c5e534de7e2102d330356ecb6e78f6346f3cc14a` |
| Updated Salmonella motility simulation | 18 | 7,992,822 | `12d9867bd2069641ad94c685f263be0aceb4e431c06ad2d217bf20d5c5f6750e` | `MPUSP/salmonella-motility-simulation@96ca0e741c8c4990b1cfa59b2daafee59d74cb7b` |

Both payloads are preserved unchanged under `archive/incoming/2026-08-12/`. Exact source snapshots used by the workflow are vendored under `models/`, with upstream URL, commit and licence records.

## Proteomics acceptance

The delivered promoter-series table contains six conditions with four replicates each: ΔflhDC, Ppro1-flhDC, PproA-flhDC, WT, PproB-flhDC and PproD-flhDC. Splitting the six two-member protein groups gives 2,751 accessions. The delivered annotation contains 1,304 annotated protein groups (1,306 accessions) representing 70.0494% of protein mass. Sector mass fractions sum to one per sample within floating-point tolerance.

The mean PproD flagellar fraction is 0.033911, flagellar and ribosomal sector means correlate at `r = -0.9884`, and FliC is the dominant flagellar contribution. The supplied identifier is `tsr`; `Tst` in the manuscript/S2 legend is a typo. The delivery does not contain raw MS files, the Spectronaut project/settings or the FASTA, so F3A/B/D and S2A reproduce deterministically from the protein-level export onward but not from raw spectra.

The manuscript statement of 1,304 refers to annotated protein groups; 1,306 is the accession count after expanding ambiguous groups. The manuscript also contains an unresolved 4,548 annotated-protein versus 4,533-FASTA-entry discrepancy that cannot be closed without the missing FASTA.

## Static cell-economy acceptance

At 5% flagellar mass and saturated substrate, the delivered final tables give:

| Comparison | Growth rate (1/h) | Penalty relative to F=0 |
|---|---:|---:|
| F=0 baseline | 1.775847 | 0% |
| F=5%, rotation/ATP cost | 1.626823 | 8.3917% |
| F=5%, no rotation cost | 1.645099 | 7.3626% |

The delivered population-growth table gives 13.0148% for WT-(fliC ON) and 9.5071% for motB-D33N relative to ΔflhDC. These reproduce the manuscript's 13%, 9.5%, 8.4% and 7.4% values. F2G-H, F3C and S3A are generated from these fixed tables.

The source and parameter set are preserved, but the parameter-sampling log does not record a random seed. GEKKO 1.3.2 is now pinned. A local `remote=False` validation attempt requested solver 3, fell back to APOPT because solver 3 was unavailable, and terminated as infeasible after 609 iterations. Therefore the fixed-result reproduction is accepted; the solver stage remains blocked on the collaborator's exact APMonitor/IPOPT runtime or a scientifically reviewed numerical port.

## Gradient-model acceptance

The final 8,500-µm gradient time series reproduce normalized final biomass `[0.2350, 0.5861, 0.9314, 1.0000, 0.9585, 0.8632]` at `[0.5, 1, 2, 3, 4, 5]%` flagellar mass, rounding exactly to the manuscript vector `[0.24, 0.59, 0.93, 1.00, 0.96, 0.86]`. The optimum is unique at 3%. F3E-G are generated from the complete supplied time series.

## Updated Supplementary Figure 5

S5A-F now use the exact updated collaborator algorithm, configuration and parameter table. The current manuscript mapping is A=PproA liquid, B=WT liquid, C=PproB liquid, D=PproA agarose, E=WT agarose and F=PproB agarose. Panel seeds are 24, 106, 65, 17, 99 and 58 respectively; agarose obstacle seeds are panel seed + 300. Every cell position/state and obstacle is exported. Two complete reruns produced byte-identical scientific tables and graphics.

The upstream package also contains a `WT_slow` demonstration, which is deliberately excluded because it is not a current manuscript panel. The parameter table is experimentally informed, but raw trajectory-to-parameter fitting inputs were not supplied, so S5 remains `partial_reproduction` rather than `reproduced`.

## Current collection status

- All 11 former collaborator-source panels have canonical Python producers, source-data tables, SVG/PDF/PNG outputs and validated provenance.
- `make reproduce-available` executes 50 panel workflows and assembles all ten figure folders.
- There are no remaining `blocked_external` panels.
- Six independent visual-asset gaps remain: F1A, F1B, F1F, F1G, F2D and F4D.
- Strict completion also requires raw-MS-to-protein reproduction, a clean local GEKKO rerun, the missing editable F3C schematic and raw parameter-fitting inputs for S5.
