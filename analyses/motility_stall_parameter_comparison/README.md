# Stall-parameter comparison

Puts the last two unsourced strain-differing motility parameters on a defensible
footing: `stall_probability` and `stall_mean_duration_s`, both agarose only.

The written recommendation is in
`docs/revision_2026-08-12/stall_parameter_comparison.md`.

## The problem

| | PproA | WT | PproB |
| --- | --- | --- | --- |
| mean hooks per cell | 2.09 | 2.67 | 4.43 |
| `stall_probability` | 0.1456 | 0.2774 | 0.0870 |
| `stall_mean_duration_s` | 1.8131 | 0.7354 | 0.2983 |

`docs/revision_2026-08-12/motility_parameter_sources.md`, sections 6 and 7,
records that neither column has a source. The durations fall with flagella
number. The probabilities do not: WT carries the highest value, which no
mechanism explains.

## Two scripts

### 1. `double_counting_check.py` — does the agarose model represent the mesh twice?

The measured persistence time comes from cells tracked **in agarose**, so it
already carries the hindering effect of the mesh. It is also not independent:
`analyses/figure_07_revision/build_figure_07_revision.py` derives it as
`tau = 2 * D_eff / v^2` from the measured agarose diffusivity and the measured
agarose speed. A free run-and-tumble walker with the measured speed and the
measured `tau` therefore carries the measured agarose `D_eff` by construction.

The simulation imposes that measured `tau`, then adds 58 disks, then adds
stalling. The script runs the same 100 seeds through a ladder that switches each
layer on in turn, plus a Brownian reference walker carrying the measured `D_eff`
through the same 148 x 96 µm box with the same reflecting boundary.

### 2. `compare_stall_variants.py` — seven ways to distribute the two parameters

| variant | probability | duration |
| --- | --- | --- |
| A baseline | per strain, as delivered | per strain, as delivered |
| B | global mean | global mean |
| C | global mean | `~ 1/N` |
| D | global mean | `~ 1/sqrt(N)` |
| E | `~ 1/N` | `~ 1/N` |
| F | global mean (no source) | 2.07 s, Datta et al. 2025 |
| G | `~ N^-0.70`, Grognot strength | global mean |

`N` is the mean hook count per cell, read from
`data/processed/figure_07_revision/hook_count_per_cell.csv`, never typed in.

**Normalisation.** Every scaled column is renormalised so its arithmetic mean
over the three strains equals the mean of the three current values:

    x_s = x_mean * N_s^-a / mean_s(N_s^-a)

So a variant changes how the effect is **distributed** between strains, not how
large it is overall. Variant F breaks that rule deliberately, because its
duration comes from a publication rather than from the current table.

**Variant G is an addition to the requested grid.** The task listed A to F.
Checking the anchor showed that Grognot et al. 2023 measured the flagella effect
on the stall **frequency**, not on the stall duration, so no variant in A to F
tested what the literature actually supports. G does.

## Literature anchors, as checked

Both were read from the source, not from memory. Retrieved through PubMed.

**Grognot M, Nam JW, Elson LE, Taute KM (2023)** PNAS 120:e2301873120,
doi 10.1073/pnas.2301873120, PMID 37579142. *Vibrio alginolyticus*, polar (P)
against polar plus lateral (PL) flagella. Verified from the full text:

> "on average, lateral flagella decrease the chance of stalling by a factor
> 1.7 ± 0.2 (mean ± SD) in 0.25% agar"

> "While we observed increased stall durations in the P compared to the PL
> phenotype above 0.12% agar, the difference was statistically significant only
> at 0.16% and not at 0.25% agar"

> "Thus, both the duration and the temporal frequency of stalls are decreased in
> the presence of lateral flagella."

**The anchor survives, and it constrains the probability more than the
duration.** More flagella lower the stall frequency by 1.7 ± 0.2 and this is the
significant effect. More flagella also shorten stalls, in the same direction as
the current table, but that difference is not significant at 0.25 % agar. The
source review in `docs/revision_2026-08-12/flagella_number_literature.md` quoted
only the frequency sentence; the duration sentence is added here.

Mapping 1.7 onto our hook range gives the exponent used by variant G:

    a = ln(1.7) / ln(4.432 / 2.085) = 0.704

The two requested duration scalings bracket that strength: `1/sqrt(N)` spans
1.46-fold across our strains, `1/N` spans 2.13-fold, and Grognot's 1.7 sits
between them.

**Datta A, Beier S, Pfeifer V, Großmann R, Beta C (2025)** Sci Rep 15:20320,
doi 10.1038/s41598-025-02741-1, PMID 40579453. *P. putida* in 0.25 % and 0.30 %
agar; mean dwell times 2.07 s and 3.63 s. Variant F uses 2.07 s. The numeral
could not be re-read from the PubMed Central rendering, which strips inline
numbers; it is carried from the source review in
`docs/revision_2026-08-12/motility_parameter_sources.md`, section 7, which
records it as read from the source.

**Bhattacharjee T, Datta SS (2019)** Nat Commun 10:2075,
doi 10.1038/s41467-019-10115-1, PMID 31061418. Trapping durations 0.4 to 40 s,
power-law distributed, *E. coli* in a jammed hydrogel packing. Used as an
order-of-magnitude constraint only.

**No source defines a stall probability.** It is a per-time-step quantity of
this model, not an observable of any experiment. Variant F therefore anchors the
duration and leaves the probability at the global mean, which is stated in the
outputs rather than hidden.

## Stall occupancy does not converge

The simulator draws against `stall_probability` once per time step in which the
proposed step overlaps a disk. Halving the time step roughly doubles the number
of draws per contact. Stall occupancy and stall entry rate are therefore
reported only as diagnostics at `dt = 0.0025 s`. They are never a model output
and never comparable with a published fraction of time spent stalling.

## Inputs

| Path | Role |
| --- | --- |
| `data/processed/motility_turn_angle_comparison/motility_summary_parameters_global_turn_angle.csv` | The global-turn-angle stage, which is variant A of this grid. Read, never written. The adopted table is variant G of it, derived by `analyses/motility_adopted_parameters/derive_adopted_parameters.py`. |
| `data/processed/figure_07_revision/paired_experimental_unit_measurements.csv` | Measured speed, tau and D_eff per unit. |
| `data/processed/figure_07_revision/hook_count_per_cell.csv` | Mean hook count per strain. |
| `data/processed/figure_05_revision/active_particle_100_seed_summary.csv` | Read only, to assert the seed plan matches the built figure. |
| `models/motility_simulation/upstream/src/.../simulation.py` | Frozen simulator. Never modified. |
| `models/motility_simulation/upstream/data/config.yml` | Frozen config. Never modified. |

## Outputs

All under `build/diagnostics/stall_parameter_comparison`.

| Path | Role |
| --- | --- |
| `measured_reference.csv` | Measured speed, tau, D_eff and the identity `D = v^2 tau / 2`. |
| `double_counting_summary.csv` | Every observable of every ladder rung. |
| `double_counting_hindrance.csv` | What each agarose layer removes, against the measured-tau-only model. |
| `double_counting_strain_ratios.csv` | Strain ratios along the ladder. |
| `double_counting_ladder.png` | The ladder against the measured `D_eff`. |
| `variant_parameters.csv` | The two stall columns under each variant. |
| `variant_net_displacement.csv` | Mean net displacement, seed interval, paired difference from the baseline. |
| `variant_strain_ratios.csv` | Strain ratios and their paired shift from the baseline. |
| `variant_ordering.csv` | Whether PproA < WT < PproB survives and is resolved. |
| `variant_stall_diagnostics.csv` | Stall occupancy and entry rate at `dt = 0.0025 s`. Not converged. |
| `variant_*.png` | The four decision figures. |
| `parameter_tables/*.csv` | One full parameter table per variant. |
| `runs_*.csv` | One row per simulation, cached and checksum-keyed. |
| `metadata/*.json` | Provenance records. |

Nothing here is a manuscript panel. No manuscript figure, panel, config, theme
or palette is touched.

## Run

    PYTHONPATH=$PWD/src MPLBACKEND=Agg .venv/bin/python \
        analyses/motility_stall_parameter_comparison/double_counting_check.py

    PYTHONPATH=$PWD/src MPLBACKEND=Agg .venv/bin/python \
        analyses/motility_stall_parameter_comparison/compare_stall_variants.py

Together about 20 min on seven cores. Each condition is cached and keyed to the
checksum of its parameter table, so a rerun without a parameter change costs
seconds. Pass `--force` to rerun anyway.
