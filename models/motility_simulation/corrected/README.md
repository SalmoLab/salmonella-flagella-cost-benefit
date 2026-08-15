# Corrected dynamics for the Salmonella motility simulation

This directory holds a project-local variant of the vendored simulator in
`../upstream`. It overrides one upstream function and adds the obstacle
machinery an enlarged domain needs. Nothing in `../upstream` is edited: that tree
is immutable provenance, checksummed at commit
`96ca0e741c8c4990b1cfa59b2daafee59d74cb7b`, and its checksums still verify.

Michael Jahn has invited a pull request. This variant is written so it can be
offered upstream as it stands: each correction is separable, each is documented
against the behaviour it replaces, and each is covered by a test in
`tests/test_corrected_motility_dynamics.py`.

## Why a variant and not an edit

Three defects change what the model means, not only what it prints. Two of them
had already reached reported numbers. Keeping the upstream tree byte-identical
lets the repository show both the delivered model and the corrected one, and lets
a reader see exactly what moved.

## Correction 1. Reorientation is instantaneous

**What upstream does.** A running cell that draws a turn enters a `reorient`
state, stops advancing, and diffuses weakly for `reorientation_duration_s`. The
heading kick is applied when that timer expires.

**Why that is wrong.** The parameters are fitted through the model's own
persistence relation,

    tau = 1 / (D_theta + lambda * (1 - exp(-sigma^2 / 2)))

This relation has no duration term. It describes a walker that turns
instantaneously and swims the whole time. The simulation therefore ran a
different model from the one the parameters were fitted to.

The cost is quantitative. A cell swam only 60 % to 80 % of the time. The
effective diffusivity of a run-and-tumble walker scales as the square of that
ballistic fraction, which predicts 0.36 to 0.64 of the measured value. The
observed shortfall was 0.49 to 0.58. The duty cycle accounted for nearly all of
it.

**What the variant does.** The heading kick is applied at the transition and the
cell keeps swimming on the same step. There is no dwell.

`reorientation_duration_s` is then not a parameter of the model. It is **removed**
from `MotilityParameters` rather than set to zero, so a table that still carries
a duration cannot silently reach the dynamics. Its upstream value, 0.05 s, was
exactly the upstream time step, which is evidence it was never a measured
duration. The `reorient` state id stays in `config.yml` for file compatibility
and is never occupied.

The measured tumble duration of *E. coli* is 0.19 s (Taute et al. 2015). It
cannot simply be substituted: at the fitted turn rates it would put cells in a
non-swimming state 49 % to 71 % of the time and remove most directed motion. A
model with a real tumble duration needs the persistence relation refitted with a
duration term. That is a modelling change, not a parameter change, and this
variant does not attempt it.

## Correction 2. The stall test fires once per contact event

**What upstream does.** At every time step in which the proposed step overlaps an
obstacle, the cell draws against `stall_probability`. A sliding or stalled cell
is re-drawn each step, and a successful draw resets its stall timer.

**Why that is wrong.** The number of draws per encounter is proportional to
`1 / dt`. Stall occupancy therefore rises without limit as the step shrinks: it
does not converge. Measured under the adopted parameters, WT in agarose, six
seeds in the published 148 x 96 um box:

| dt (s)   | upstream stall occupancy | corrected stall occupancy |
|----------|--------------------------|---------------------------|
| 0.01     | 0.178                    | 0.128                     |
| 0.005    | 0.207                    | 0.120                     |
| 0.0025   | 0.264                    | 0.135                     |
| 0.00125  | 0.288                    | 0.146                     |
| 0.000625 | 0.317                    | 0.135                     |

**What the variant does.** The draw is made once, on the step where the cell
first overlaps a disk it was not already touching. A cell counts as still
touching the same disk until its centre is farther than `CONTACT_RELEASE_UM`
(0.1 um) beyond the surface. A bare overlap test would not do: a stalled cell is
parked one part in a million outside the surface, so it would leave and re-enter
contact on almost every step and the re-draw would come back.

`stall_probability` now means the chance that one encounter ends in a stall.
That is what Grognot et al. 2023 measured (stall frequency, ratio 1.7 +/- 0.2),
so the parameter finally means what its literature anchor means. Only the ratio
between strains is anchored; the absolute probability still has no source.

## Correction 3. The domain scales without diluting the mesh

**What upstream does.** A 148 x 96 um box with reflecting walls and a fixed 58
obstacles.

**Why that matters.** A wall turns a cell back, so it shortens a fast strain more
than a slow one and compresses the strain ratios a quantitative panel reports.
The obstacle count, though, is tuned to that one box. Enlarging the box without
scaling the count would dilute the mesh and inflate every agarose number, which
would look like a result.

**What the variant does.** `scaled_config` enlarges the box and scales the
obstacle count with the box **area**, so the number density, the disk-size
distribution and the area fraction are the published ones at any box size.
`obstacle_area_fraction` reports the realised value, and every run records it, so
the density is checked rather than assumed.

Two supporting pieces make the larger domain affordable, and neither changes any
result:

- `ObstacleIndex` answers the overlap query from a uniform grid instead of
  scanning every disk. It returns exactly what the upstream linear scan returns,
  including its tie rule.
- `make_obstacle_field` tests a candidate disk against a grid neighbourhood
  instead of every placed disk, which removes the upstream quadratic cost. It
  consumes the random stream in the upstream order and applies the upstream
  acceptance rule, so for any seed and config it returns the **identical** field.

Both equivalences are asserted by tests.

This repository uses the two domains for two purposes, and says so in the
methods: Figure 5D and 5E measure, and run in a box enlarged eightfold in each
direction; Supplementary Figure 4 shows trajectory maps, and keeps the published
148 x 96 um box, where a small field is what makes tracks legible.

## What is not changed

Run kinematics, rotational diffusion, the translational noise scales, the
projection and sliding geometry on contact, the reflecting box and the obstacle
acceptance rule are upstream behaviour, imported from `vendored.py` and used
unchanged.

## Layout

| File | Contents |
|------|----------|
| `vendored.py` | The single boundary to the upstream package. What it re-exports is upstream behaviour the correction keeps. |
| `classes.py` | `MotilityParameters`, without `reorientation_duration_s`. |
| `io.py` | Parameter-table loader. Reports retired columns instead of reading them. |
| `obstacles.py` | Area-scaled configs, the realised area fraction, the grid index and the fast generator. |
| `simulation.py` | `simulate_population` with corrections 1 and 2. |

## Running it

```bash
PYTHONPATH=models/motility_simulation/corrected/src .venv/bin/python - <<'PY'
import yaml
from pathlib import Path
import salmonella_motility_corrected as smc

config = yaml.safe_load(Path("models/motility_simulation/upstream/data/config.yml").read_text())
config["simulation"]["dt_s"] = 0.0025
config = smc.scaled_config(config, 8)          # enlarge, and scale the mesh with area
params = smc.load_parameter_table(Path(
    "data/processed/motility_adopted_parameters/motility_summary_parameters_adopted.csv"))
field = smc.make_obstacle_field(config, seed=1300)
result = smc.simulate_population(config, params[("WT", "agarose")], field, 1000)
print(result["obstacle_area_fraction"], result["contact_events"], result["stall_entries"])
PY
```

## Tests

`tests/test_corrected_motility_dynamics.py` covers: the retired parameter is
gone from the model and from the adopted table; the `reorient` state is never
occupied; liquid `D_eff` reproduces `v^2 tau / 2`; the obstacle count scales with
area and holds the area fraction; the grid index and the fast generator match
upstream exactly; the realised per-encounter stall rate matches the nominal
probability and does not drift with the step; a continued contact never draws a
second stall; and the upstream checksums still verify.
