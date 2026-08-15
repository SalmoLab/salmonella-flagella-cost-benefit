# Upstream source record

- Repository: https://github.com/m-jahn/cell-economy-models
- Branch received: `master`
- Exact commit: `c5e534de7e2102d330356ecb6e78f6346f3cc14a`
- Collaborator delivery frozen: `archive/incoming/2026-08-12/collaborator_proteomics_cell_economy_2026/`
- Delivery manifest SHA-256: `d5443d716a7e1f9e931dbde0ee242a89030e4d67f1b65a3c218f31f70147f081`

The vendored model source and parameter table are byte-identical to the corresponding delivered working files and to the repository commit above. Final supplied result tables are preserved under `data/external/cell_economy_results/`.

The canonical downstream figure workflow is Python 3.12. The supplied fixed-result tables reproduce the manuscript headline values. GEKKO 1.3.2 is locked; a local `remote=False` validation attempt failed because the requested solver 3 was unavailable and the APOPT fallback declared the problem infeasible. See `models/cell_economy/LOCAL_SOLVER_VALIDATION.md`. The collaborator's sampling step also used unseeded random parameter perturbations.
