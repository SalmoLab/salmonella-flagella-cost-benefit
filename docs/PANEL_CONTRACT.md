# Canonical panel contract

Every formal manuscript panel has exactly one row in `config/panels.csv` and
exactly one canonical workflow producer. A legacy plot or copied final image is
evidence for migration, not a reproduced panel.

## Required panel bundle

```text
analyses/figure_XX/panel_Y/
├── README.md
├── scripts/
├── config/
├── expected/
└── metadata/
```

The README must document:

- the scientific question and current manuscript panel;
- raw and processed inputs, including units and checksums;
- biological and technical replicate definitions;
- preprocessing, filtering, transformations and exclusions;
- center, spread/interval, statistical test and multiplicity correction;
- exact reproduction command;
- generated statistics, source-data and figure artifacts;
- image-integrity information for microscopy;
- model parameters, seeds and solver settings for simulations;
- legacy identifiers and any intentional difference from the July reference.

## Completion states

- `ready_migration`: canonical legacy inputs exist but have not yet passed the
  new build and regression checks.
- `needs_asset_migration`: a schematic, microscopy asset, selection record or
  deterministic assembly step is missing.
- `blocked_external`: the final scientific source package is absent. No guessed
  code or values may be substituted.

A panel may be promoted to a completed status only after its canonical source
data, statistics, panel output and provenance artifacts are registered and pass
the strict audit.
