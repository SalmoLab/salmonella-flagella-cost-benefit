# Upstream source record

- Repository: https://github.com/MPUSP/salmonella-motility-simulation
- Branch received: `main`
- Exact commit: `96ca0e741c8c4990b1cfa59b2daafee59d74cb7b`
- Collaborator delivery frozen: `archive/incoming/2026-08-12/updated_salmonella_motility_simulation/`
- Delivery manifest SHA-256: `12d9867bd2069641ad94c685f263be0aceb4e431c06ad2d217bf20d5c5f6750e`

The vendored source, configuration, parameter table, licence and environment declarations are byte-identical to the files at the commit above. `CHECKSUMS.sha256` covers every vendored file that existed before this record was added.

The upstream environment declares Python 3.14.4. The canonical manuscript workflow uses the project-wide locked Python 3.12 environment; the supplied source has been executed and tested successfully there without modifying its algorithms. The manuscript wrapper excludes the additional `WT_slow` demonstration because the current Supplementary Figure 5 contains only PproA, WT and PproB.
