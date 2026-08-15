# Licence map

This file records what licence covers each part of the collection. It is the
authority when `LICENSE`, `models/cell_economy/LICENSE`, `config/artifacts.csv`,
`config/fetch_manifest.csv`, `CITATION.cff` and `.zenodo.json` disagree.

**Status on 15 August 2026: the licence is decided.** Marc Erhardt chose
**GPL-3.0-only** for the collection's own code on that date. It replaces the
MIT licence he chose earlier on the same day. He does not want a permissive
licence.

- **GPL-3.0-only** for all of the collection's own code. The text is in
  `LICENSE` at the root.
- **CC-BY-4.0** for documentation, for figure output and for the separate data
  deposit.

This change dissolves the earlier split rather than complicating it.
`models/cell_economy/` was already GPL-3.0-only, because
`low_allocation_sweep.py` imports Michael Jahn's GPL-3.0-only upstream model.
The root licence is now the same licence, so no combined-work exception is left
to explain. `models/cell_economy/LICENSE` stays in place, because that subtree
also holds third-party GPL code under a different copyright holder.

The vendored trees under `models/*/upstream/` keep the licence they arrived
with. Nothing in this decision changes them. MIT stays correct for
`models/motility_simulation/upstream/`.

`config/artifacts.csv` needs no change. It carries a real licence on all 389
artifacts: 342 `CC-BY-4.0`, 26 `GPL-3.0-only` and 21 `not_redistributed`. No
artifact reads `internal_pending_release` or `internal_reference`. The registry
holds no code file, which is why no row ever read `MIT` and why the code licence
lives in `LICENSE` and in this file instead.

---

## The per-directory map

`CITATION.cff` and `.zenodo.json` each hold one licence identifier, and both say
GPL-3.0-only, because both describe the software record. `CITATION.cff` uses the
SPDX form `GPL-3.0-only`; `.zenodo.json` uses `gpl-3.0-only`, which is how
Zenodo's licence vocabulary spells the same SPDX identifier. This table is the
full picture.

| Path | Licence | Who holds the copyright |
|---|---|---|
| `src/`, `analyses/`, `tools/`, `tests/`, `workflow/`, `scripts/`, `config/` | **GPL-3.0-only** | The authors of `CITATION.cff` |
| `Makefile`, `Dockerfile`, `pyproject.toml`, the lock files | **GPL-3.0-only** | The authors of `CITATION.cff` |
| `models/motility_simulation/corrected/` | **GPL-3.0-only** | The authors of `CITATION.cff` |
| `models/motility_simulation/upstream/` | **MIT**, third party | Max Planck Unit for the Science of Pathogens, 2026 |
| `models/cell_economy/`, including `low_allocation_sweep.py` | **GPL-3.0-only** | The authors of `CITATION.cff` |
| `models/cell_economy/upstream/` | **GPL-3.0-only**, third party | M. Jahn |
| `assets/schematics/salmonella_model.svg` | **GPL-3.0-only**, inherited, third party | M. Jahn |
| `README.md`, `LICENSES.md`, `REFERENCE_RELEASE.md`, `docs/`, `models/gradient/README.md` | **CC-BY-4.0** | The authors of `CITATION.cff` |
| Figure output: `build/panels/`, `build/figures/`, panel SVG, PDF and PNG files | **CC-BY-4.0** | The authors of `CITATION.cff` |
| The data deposit: `data/processed/`, `data/source_data/`, `build/source_data/`, `build/statistics/`, `assets/schematics/competition_design/` | **CC-BY-4.0** | The authors of `CITATION.cff` |
| `data/external/cell_economy_results/` | **GPL-3.0-only**, follows the delivering package | M. Jahn |
| `data/external/promoter_series_proteomics/` | **CC-BY-4.0**, with the data deposit | The authors of `CITATION.cff` |
| `reference/2026-07-09/` (figures and manuscript) | **not redistributed** | The authors of `CITATION.cff` |
| `archive/incoming/` | per delivery, not redistributed | the delivering collaborator |

One row needs a word of care.

`reference/2026-07-09/` holds the frozen July figures and manuscript. All 21
`ref_*` artifacts carry `not_redistributed`, decided on 15 August 2026. They
are the authors' own unpublished work. A public licence is an irrevocable
grant, and the licence of the paper follows the journal agreement, so no
public licence is claimed over them. `reference/` is excluded by `.gitignore`
and is never distributed, so the value states the fact rather than restricting
anything new.

`data/external/cell_economy_results/` holds output of the GPL-3.0-only model rather
than the model itself. Running a GPL-3.0-only program does not by itself place its
output under the GPL. These tables carry `GPL-3.0-only` anyway, because the
delivering package sets their redistribution terms and the conservative reading
costs nothing here.

---

## Verified third-party licences

These are facts read from the vendored files. They do not change with the
licence the collection picks. Both trees are redistributed unchanged, with their
own `LICENSE` file and their `CHECKSUMS.sha256` record beside them.

| Path | Licence | Copyright holder | Source |
|---|---|---|---|
| `models/motility_simulation/upstream/` | **MIT** | Max Planck Unit for the Science of Pathogens, 2026 | `github.com/MPUSP/salmonella-motility-simulation` at commit `96ca0e74` |
| `models/cell_economy/upstream/` | **GPL-3.0-only** | M. Jahn | `github.com/m-jahn/cell-economy-models` at commit `c5e534de` |
| `assets/schematics/salmonella_model.svg` | **GPL-3.0-only**, inherited | M. Jahn | `resources/images/salmonella_model.svg` of the same cell-economy commit |

Both licences permit redistribution. Neither may be removed, relicensed or
overwritten. Do not edit `models/motility_simulation/upstream/LICENSE` or
`models/cell_economy/upstream/LICENSE`.

`config/fetch_manifest.csv` gave the licence of `static_cell_economy_model` and
`gradient_model` as `MIT`. Both come from the same collaborator delivery as
`models/cell_economy/upstream/`, whose own `LICENSE` file is GPL-3.0-only. The
`LICENSE` file wins. Both rows now read `GPL-3.0-only`. No row in that file
reads `MIT` any more; the motility simulation has no row there.

### How the vendored MIT tree sits inside a GPL-3.0-only collection

`models/motility_simulation/corrected/` is the collection's own code, so it is
GPL-3.0-only. It imports the vendored MIT tree through
`src/salmonella_motility_corrected/vendored.py`. MIT is one-way compatible into
GPL-3.0-only: MIT code may be combined into a GPL-3.0-only work, and the
combined work is then distributed under GPL-3.0-only. The MIT tree itself is not
relicensed. It keeps its own `LICENSE` file, its copyright notice and its
`CHECKSUMS.sha256` record, and anyone may still take it from
`models/motility_simulation/upstream/` under MIT.

### Why `models/cell_economy/` was GPL-3.0-only first

`models/cell_economy/low_allocation_sweep.py` inserts the GPL-3.0-only upstream tree
on `sys.path` at lines 123, 235 and 410, and imports
`models.salmonella.dynamic`, `models.salmonella.steadystate` and `models.common`
from it on the lines that follow. A script that imports a GPL-3.0-only module and is
distributed together with it is a combined work in the Free Software
Foundation's reading of the licence. That directory therefore could not carry a
permissive licence, and it was GPL-3.0-only while the rest of the collection was
still MIT. Since 15 August 2026 the whole collection carries the same licence, so
this is a record of how the choice arose rather than an exception to it.

---

## What is not published through git

`data/`, `reference/`, `archive/` and `build/` are excluded by `.gitignore` and
are not part of the public repository. The licences above still say who holds
what. These extra terms apply:

- `reference/` holds the manuscript and the frozen July figures. The manuscript
  is the authors' unpublished work. Do not redistribute it.
- `archive/incoming/` holds untouched collaborator deliveries. Redistribution
  needs the delivering collaborator's permission, per delivery.
- `data/external/cell_economy_results/` holds the collaborator's model output.
  Its redistribution terms follow the cell-economy package, not our code
  licence.
- Everything the journal receives as Source Data follows the journal's terms.

Record the verified licence of every new artifact in `config/artifacts.csv`
before it is released.
