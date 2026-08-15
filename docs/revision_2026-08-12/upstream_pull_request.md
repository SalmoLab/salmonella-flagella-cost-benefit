# Pull request to `MPUSP/salmonella-motility-simulation`

This file holds the text of the pull request. Marc opens the pull request; the
branch is prepared and tested but not pushed.

- Upstream: <https://github.com/MPUSP/salmonella-motility-simulation>, MIT.
- Base commit: `96ca0e741c8c4990b1cfa59b2daafee59d74cb7b` (`main`).
- Branch: `fix/step-independent-dynamics`, three commits.
- Invitation: Michael Jahn, 13 August 2026.

Everything below the rule is the pull-request body. Every number in it is
verified; the sources are listed in the last section.

---

## Make the simulated dynamics independent of the integration step

Thank you for the invitation to send this back as a pull request. We ran your
simulation through a convergence check while preparing the manuscript figures,
and found two rules in the integration loop that do not match the model the
motility parameters are fitted to. One of them makes every obstacle result
depend on the size of the time step. This branch corrects both, keeps your
released behaviour behind two switches, and adds a test for each defect.

The corrections are ours to justify, not yours to defend: they sit in code that
came to you already written, and the second one is a case of the loop not doing
what your own `README.md` says it does.

### The result, in one command

```bash
git checkout fix/step-independent-dynamics
pixi run tests
```

`test_net_displacement_is_step_independent` runs WT in agarose at four time
steps, 0.02 s down to 0.0025 s, over 480 tracks per step. The test requires
every step to stay within 6 % of the finest; the measured worst case is 2.4 %.

We run a larger version of the same check for the manuscript: 100 seeds, six
strain-by-medium groups, the full ladder from 0.05 s down to 0.000625 s, our own
parameter table and an enlarged box. There the largest deviation of any group
mean from the mean of the two finest steps is **3.96 %**, and every step on the
ladder passes a 5 % rule.

`test_stall_occupancy_does_not_grow_as_the_time_step_shrinks` is the sharper
test, and it is the one that fails on `main`. It is described under defect 2.

### Defect 1. The reorientation dwell is not in the calibration

**What the loop does.** A running cell that draws a turn enters the `reorient`
state, stops advancing, and diffuses weakly for `reorientation_duration_s`. The
heading kick lands when that timer expires.

**Why it matters.** The turning parameters are fitted through the persistence
relation

```
tau = 1 / (D_theta + lambda * (1 - exp(-sigma^2 / 2)))
```

That relation carries no duration term. It describes a walker that turns
instantly and swims the whole time. So the parameters were fitted through one
model and simulated in another.

The cost is measurable. The figures in this paragraph come from our own
recalibrated parameter table, over 100 seeds, and are lag-corrected; the
direction and the size of the effect do not depend on the table.

A motile cell in liquid swam only **74.7 % to 79.3 %**
of the time. The effective diffusivity of a run-and-tumble walker scales as the
square of that ballistic fraction. Measured against the model's own implied
`v² tau / 2`, the liquid model delivered **65 % to 69 %**. After the correction
it delivers **98 % to 100 %**. In agarose the same ratio moves from 42–44 % to
78–83 %; the remaining agarose gap has a separate cause, noted at the end.

One more sign that the dwell was never a measured quantity: its value in
`data/motility_summary_parameters.csv` is 0.05 s for every strain and medium,
which is exactly the released `dt_s`.

**What changes.** The heading kick is applied at the transition and the cell
keeps swimming on the same step. There is no dwell. The `reorient` state id
stays in `config.yml` for file compatibility and is never occupied.

`reorientation_duration_s` becomes a legacy parameter. It is optional in the
CSV, and only the legacy path reads it. We did not substitute a literature
tumble duration. The measured value for *E. coli* AW405 is 0.19 s over 2551
cells (Taute et al. 2015), and at the fitted reorientation rates that would put
cells in a non-swimming state 49 % to 71 % of the time. A model with a real tumble duration needs the persistence
relation refitted with a duration term. That is a modelling change, not a
parameter change, and this branch does not attempt it.

### Defect 2. The stall test fires once per time step, not once per contact

**What the loop does.** On every time step where a proposed step overlaps an
obstacle, the cell draws against `stall_probability`. A sliding cell is
re-drawn each step. A stalled cell sits on the surface, still overlaps, is
re-drawn, and its stall timer is reset.

**Why it matters.** The number of draws per encounter is proportional to
`1 / dt`, so stall occupancy has no limit as the step shrinks. No obstacle
observable converges, and `stall_probability` is not a probability of anything
observable.

The added test measures it on your own parameter table. WT in agarose, four
time steps, 480 tracks per step:

| `dt_s` | stalls per contact, released loop | stalls per contact, this branch |
| --- | --- | --- |
| 0.02 | 0.94 | 0.264 |
| 0.01 | 1.15 | 0.278 |
| 0.005 | 1.64 | 0.280 |
| 0.0025 | 2.12 | 0.276 |

`stall_probability` for WT in agarose is 0.277. The released loop produces more
than one stall per encounter, and the count keeps rising as the step falls. The
corrected loop reproduces the parameter at every step. Stall occupancy moves the
same way: 0.128 to 0.226 on the released loop across that ladder, against 0.134
to 0.153 here.

**What changes.** The draw is made once, on the step where a cell first overlaps
a disk it was not already touching. A cell counts as still touching the same
disk until its centre is more than `CONTACT_RELEASE_UM` (0.1 µm) beyond the
surface. A bare overlap test would not work: a stalled cell is parked one part
in a million outside the surface, so it would leave and re-enter contact on
almost every step and the re-draw would come back.

`stall_probability` now means the chance that one encounter ends in a stall.
That is what your `README.md` already says it means, and it is also what the
experimental literature measures. Grognot et al. 2023 (PNAS 120:e2301873120,
PMID 37579142) report a stall **frequency** ratio of 1.7 ± 0.2 with flagella
number, at the agar concentration that matches this condition.

### Defect 3, or rather a caveat. The mesh dilutes if the box grows

The field of 58 disks is tuned to the 148 x 96 µm box. Enlarging the box
without scaling the count thins the mesh and raises every agarose observable,
which looks like a result. We needed a larger box, because the reflecting walls
turn a fast strain back sooner than a slow one and compress the strain ratios a
quantitative panel reports.

`simulation.box_scale` multiplies both box dimensions and scales the obstacle
count with the box **area**, so the number density, the disk-size distribution
and the covered area fraction stay where they are. The default, 1.0, changes
nothing. Every run now reports the realised `obstacle_area_fraction`, so the
density is checked rather than assumed. At the released settings it reads 0.185
to 0.194 across the panels.

Two supporting changes carry no result with them:

- `make_obstacle_field` tests a candidate disk against a grid neighbourhood
  instead of against every disk already placed. It consumes the random stream in
  the same order and applies the same acceptance rule, so it returns the
  identical field, disk for disk.
- `ObstacleIndex` answers the overlap query from a uniform grid instead of
  scanning every disk once per cell per time step. It returns exactly what
  `nearest_overlapping_obstacle` returns, including its tie rule.

Both equivalences are asserted by tests. Without them a large box is not
affordable; with them the cost per step does not grow with the box.

### Backward compatibility is your call, and it is a switch

Both dynamics rules are flags in `data/config.yml`:

```yaml
dynamics:
  instantaneous_reorientation: true
  stall_draw_per_contact: true
```

**We set both to `true`**, so a fresh clone runs the corrected model. Our
reasoning: the released rules contradict the calibration and do not converge, so
a new user should not have to know that in order to get a defensible number. The
flags are independent, so you can adopt one correction and reject the other.

Set both to `false` and the loop reproduces release 1.0.0 **exactly** — step for
step and random number for random number. That is not a claim, it is a test.
`tests/test_dynamics.py::test_legacy_flags_reproduce_release_1_0_0` compares
trajectories and state histories against `tests/reference_release_1_0_0.py`, a
frozen copy of your loop and your obstacle generator, in both media and over
several seeds. Your published figures, your TSV bundles and the rendered web
page all stay reproducible from this branch.

If you would rather default to the released behaviour and let users opt in,
change the two defaults in `config.yml` and nothing else needs to move.

### What this costs you: the outputs change

They change a lot in agarose. Mean net displacement at the released settings —
`dt_s` 0.05 s, 20 s, 26 cells, 30 seeds, shipped parameter table:

| group | release 1.0.0 | this branch | ratio |
| --- | --- | --- | --- |
| PproA / liquid | 30.89 µm | 34.11 µm | 1.10 |
| WT / liquid | 47.92 µm | 50.43 µm | 1.05 |
| PproB / liquid | 52.84 µm | 54.73 µm | 1.04 |
| PproA / agarose | 5.86 µm | 11.07 µm | 1.89 |
| WT / agarose | 8.77 µm | 21.56 µm | 2.46 |
| PproB / agarose | 43.45 µm | 47.48 µm | 1.09 |

Cells swim further, because they no longer spend a fifth to a quarter of their
time parked, and because they no longer stall several times per obstacle. The
strain ordering PproA < WT < PproB is unchanged in both media. The rendered
figure and the web page will look different from the ones on the site, so the
example output in `docs/` will need regenerating if you merge this.

If you re-run with both flags set to `false`, you get the old numbers back
exactly.

### What we did not change

- `plotting.py` and `io_utils.py` are untouched. The figure code still reads a
  `reorient` state that is now never occupied; that is harmless, and we did not
  want to touch your figure in the same pull request.
- Run kinematics, rotational diffusion, the translational noise scales, the
  projection and sliding geometry on contact, the reflecting box and the
  obstacle acceptance rule are all yours, unchanged.
- One number moved from the code into the config without changing value: the
  stalled-cell translational noise scale, 0.20, was a literal inside the loop.
  It is now `noise.stall_translational_scale`. It, and the three other noise
  scales, have no source that we could find. They also order the translational
  noise the other way round from what one would expect: a running cell gets 0.12
  of the passive diffusion coefficient, a stalled cell 0.20 and a non-motile
  cell 1.00, so a swimming cell diffuses about eight times less than a stopped
  one. We measured the effect of that ordering rather than change it, and left
  it alone here.
- The agarose effective diffusivity still falls short of the measurement by
  17 % to 22 %, and we think that is a double count rather than a bug: the
  measured agarose `tau` is derived as `2 D_eff / v²` from tracks recorded in
  agarose, so it already contains the mesh, and the model then adds obstacles
  and stalls on top of it. That is a modelling question, not a code question.

### Tests

`tests/test_dynamics.py` needs no test framework. It runs on the packages the
simulation already depends on, through a new `pixi run tests` task that the
testing workflow now calls. It takes about 35 seconds. `pytest tests` also works
if you prefer it.

Seventeen tests. Three of them fail on `main`:

- `test_stall_occupancy_does_not_grow_as_the_time_step_shrinks`
- `test_net_displacement_is_step_independent`
- `test_liquid_diffusivity_matches_the_persistence_relation`

The rest pin the behaviour that must not move: the legacy path reproduces
release 1.0.0 exactly and still shows its step dependence; the grid index and
the grid generator return exactly what the linear versions returned; box scaling
holds the obstacle area fraction; a continued contact never draws a second
stall; `stall_probability` is reproduced per encounter at every step.

### How to check any of this yourself

```bash
git checkout fix/step-independent-dynamics
pixi run tests          # 17 tests, about 35 s
pixi run simulation     # the CLI, now printing obstacle_area_fraction
pixi run formatting     # unchanged
```

To see the released behaviour, set both `dynamics` flags to `false` in
`data/config.yml` and run `pixi run simulation` again.

### Sources for every number above

| Number | File |
| --- | --- |
| Largest group deviation of net displacement per step: 2.20, 2.20, 1.99, 3.22, 3.88, **3.96 %** | `build/diagnostics/Figure_5/timestep_convergence.csv` (100 seeds, six groups) |
| Path length does not converge: WT agarose 325 µm at 0.05 s to 595 µm at 0.000625 s, still rising | same file |
| Path-length ratio PproA/WT agarose crosses 1: 0.535 at 0.05 s, 1.099 at 0.000625 s; the net-displacement ratio holds at 0.403 and 0.413 | `build/diagnostics/Figure_5/timestep_convergence_ratios.csv` |
| Liquid `D_eff` against implied `v² tau / 2`: 65–69 % before, 98–100 % after; agarose 42–44 % before, 78–83 % after | `build/diagnostics/effective_diffusivity_check/effective_diffusivity_comparison.csv` (100 seeds, lag-corrected) |
| Ballistic fraction in liquid 74.7–79.3 % before, 100 % after; `reorient` occupancy up to 0.329 before, 0.000 after | same file |
| Agarose stall occupancy 0.179–0.259 before, 0.101–0.135 after | same file |
| Agarose double count removes a further 17–22 % of `D_eff` | `docs/revision_2026-08-12/change_log.md` |
| Realised obstacle area fraction 0.1851 to 0.1874 from box scale 1 to 12 | `docs/revision_2026-08-12/change_log.md` |
| Tumble duration 0.19 s, *E. coli* AW405, n = 2551 cells, Taute et al. 2015; a 0.19 s tumble would idle cells 49–71 % of the time | `docs/revision_2026-08-12/motility_parameter_sources.md`, section 4 |
| Grognot et al. 2023 stall frequency ratio 1.7 ± 0.2 | `docs/revision_2026-08-12/stall_parameter_comparison.md` |

Two tables in the pull request are measured on the branch itself, with the
upstream parameter table and the upstream config, not on manuscript data. They
are the stalls-per-contact ladder and the net-displacement comparison. Both are
reproducible from the branch: the ladder is what
`tests/test_dynamics.py::time_step_ladder` computes, and the comparison is the
shipped config run with the `dynamics` flags on and off.

The manuscript figures are produced by an equivalent module in our own tree.
This branch reproduces that module bit for bit: identical trajectories, identical
state histories and identical contact counters, in both media, for the same
config and seeds.
