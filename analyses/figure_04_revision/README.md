# Revised Figure 4 — proteome allocation

This Python 3.12 workflow produces the five revised panels and two analysis-only
diagnostics from the checksum-frozen promoter-series proteomics and cell-economy
outputs.

Run:

```text
.venv/bin/python analyses/figure_04_revision/build.py --all
```

Panel contract:

- A: editable cellular-economy schematic from the collaborator repository.
- B: experimental and model sector changes relative to their respective no-flagella
  references, for the seven response sectors.
- C: top-protein composition with deterministic external label repulsion.
- D: measured mean sector composition per strain.
- E: model-predicted sector allocation over 0–5% flagellar allocation.
- F: growth versus ribosomal and flagellar allocation.

The raw model/measurement overlay is retained as a diagnostic rather than used as the
main comparison. `A1_sector_regressions.csv` and `A5_chemotaxis_scaling.csv` record the
additional analyses requested by coauthors. The chemotaxis analysis is descriptive and
is not interpreted as a functional chemotaxis test.

## Sector overrides

`config/protein_sector_overrides.csv` records every protein whose sector differs from
the delivered KEGG mapping, with one reason per protein. `sector_overrides.py` applies
that table at the protein level, and every sector total is re-summed from the overridden
protein table. `analyses/collaborator_science/build_panels.py` reads the same module, so
Figure 4 and Supplementary Figure 2 cannot disagree about a protein's sector.

## Statistics and labels

For A1, flagellar allocation is the predictor and is therefore not tested as its own
response. Benjamini–Hochberg correction is applied to the seven scientifically valid
non-Fla response-sector tests; including the tautological Fla-on-Fla identity would make
the nominal eight-test family anticonservative. Panel B draws the same seven response
sectors: the flagellar sub-axes plotted the predictor against itself, and the model
imposes `a["Fla"] == a_fla`, so both its marks and its line were identities.

Panel C names a protein when it carries at least `ABSOLUTE_FLOOR` (6.0e-4, that is 0.06%
of total protein mass) in one condition and, in addition, either reaches
`LABEL_THRESHOLD` (15%) of the top-10 subtotal in a condition where it also clears the
floor, or ranks among the `ABUNDANCE_LEADER_RANK` (3) most abundant proteins of its
sector. FliC is named regardless. The floor stops a protein from being named for a large
share of a nearly empty bar; the rank rule names a sector's leading proteins where one
protein takes most of the bar. The complete audit, with one reason per candidate, is
written beside panel C.
