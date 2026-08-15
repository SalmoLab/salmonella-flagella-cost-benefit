# Supplementary Figure 4 — updated collaborator simulation

This directory builds Supplementary Figure 4. It was named `supplementary_05`
until 15 August 2026: the supplementary figures were renumbered on 12 August,
when the old Supplementary Figure 3 was withdrawn, and the directories kept
their old names for three days. Directory and figure now agree.

S4_A-F are generated from the exact source at commit `96ca0e741c8c4990b1cfa59b2daafee59d74cb7b` of `MPUSP/salmonella-motility-simulation`, supplied on 12 August 2026. The model simulates run, stalled and permanently non-motile states, with explicit obstacle interactions in agarose. Reorientation is instantaneous: the corrected model turns a cell within one step and holds no reorientation state, because the persistence relation the turning parameters are fitted through carries no duration term. No track therefore shows a stationary reorientation pause. The current manuscript order is retained: PproA, WT and PproB in liquid (A-C), followed by the same strains in agarose (D-F). The additional upstream `WT_slow` demonstration is intentionally excluded.

Each panel uses 26 cells, 20 s duration and 0.0025 s steps in a 148 × 96 µm box. Agarose panels generate 58 non-overlapping obstacles using the upstream panel-specific seed. These maps keep the published box because a small field is what makes individual tracks legible, and they report no number. Figure 5D and 5E measure, so they run in a domain enlarged twelvefold in each direction, 1776 × 1152 µm with 8352 disks, where the reflecting walls no longer compress the strain ratios. The obstacle count scales with the box area, so both domains hold the same mesh density. Every simulated cell position/state and every obstacle is exported under `data/source_data/supplementary_04/`; PNG/SVG/PDF outputs live under `build/panels/Supplementary_Figure_4/<panel>/`. Exact inputs, outputs, parameters, runtime and seeds are checksum-recorded in panel-local and central provenance.

The panels read the adopted parameter table,
`data/processed/motility_adopted_parameters/motility_summary_parameters_adopted.csv`,
the same file Figure 5D and 5E read, through the single accessor
`adopted_parameter_table_path()`. It gives every strain-by-medium row the same
reorientation angle spread, 1.2468 rad, set so the mean turn magnitude equals the 57 deg
measured by Taute et al. 2015 (Nat Commun 6:8776, PMID 26522289). In the three agarose rows
it scales `stall_probability` with the mean hook number as `N^-0.704` (PproA 0.2099, WT
0.1766, PproB 0.1235), at the strength Grognot et al. 2023 measured for the stall frequency
in 0.25 % agar (PNAS 120:e2301873120, PMID 37579142), and sets `stall_mean_duration_s` to
one value, 0.9489 s. `stall_probability` is a per-contact-event probability. The model
draws it once, when a cell first meets a disk it was not already touching, and not once per
time step of overlap. A cell counts as still touching a disk until its centre passes 0.1 µm
beyond the surface. The table is derived at build time by
`analyses/motility_adopted_parameters/derive_adopted_parameters.py`; see
`docs/revision_2026-08-12/turn_angle_model_comparison.md` and
`docs/revision_2026-08-12/stall_parameter_comparison.md`.

The upstream `config.yml` declares a 0.05 s step. That file is immutable provenance and was not edited. The builder imports `SIMULATION_DT_S` from `analyses/figure_05_revision/build.py` and overrides the step, so these maps depict the same simulation as Figure 5D and 5E. A convergence check covers the value: every step of the tested ladder passes the 5 % rule, and 0.0025 s carries the smallest deviation over the six strain-by-medium groups, 1.99 %. See `analyses/figure_05_revision/README.md`. The refined step multiplies the exported trajectory rows by 20, from 10,426 to 208,026 per panel.

Status remains `partial_reproduction` because the supplied parameter table contains experimentally informed summaries but not the raw trajectory-to-parameter fitting chain. The 9 July figure is retained as a frozen historical target; these panels intentionally reflect the updated model.

Run all panels: `.venv/bin/python3.12 analyses/supplementary_04/build_s4.py --panel all`.
