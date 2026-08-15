Three fixes that make the simulated dynamics independent of the integration
step, with tests. Everything is behind config flags, so you can take one fix
and leave the others.

To see the problem and the fix:

```
git checkout fix/step-independent-dynamics
pixi run tests
```

Three tests fail on `main` and pass here.

## 1. The reorientation dwell is not in the calibration

A running cell that draws a turn enters the `reorient` state, stops advancing,
and diffuses weakly for `reorientation_duration_s`. But the turning parameters
are fitted through

```
tau = 1 / (D_theta + lambda * (1 - exp(-sigma^2 / 2)))
```

which has no duration term — it describes a walker that turns instantly and
swims the whole time. The parameters are fitted through one model and simulated
in another.

The cost is large. A motile cell in liquid swims only 74.7 % to 79.3 % of the
time, and effective diffusivity scales as the square of that fraction. Measured
against the model's own implied `v² tau / 2`, liquid delivers 65 % to 69 %.
With the fix it delivers 98 % to 100 %. Agarose moves from 42–44 % to 78–83 %.

The heading kick now lands at the transition and the cell keeps swimming.
`reorientation_duration_s` is then not a parameter of the model at all. It is
also worth noting that its value in `data/motility_summary_parameters.csv` is
0.05 s in every row, which was the old default time step.

## 2. The stall test fires per time step, not per contact

On every step where a proposed move overlaps an obstacle, the loop draws
against `stall_probability`. A sliding or stalled cell overlaps on consecutive
steps, so it is drawn against repeatedly, and the number of draws per encounter
scales as 1/dt.

Measured on this branch with your own parameter table, agarose, stalls per
encounter:

| dt (s) | 0.02 | 0.01 | 0.005 | 0.0025 |
|---|---|---|---|---|
| stalls per encounter | 0.94 | 1.15 | 1.64 | 2.12 |

against a nominal `stall_probability` of 0.277. More than one stall per
encounter is the clearest statement of the problem. Nothing involving obstacles
converges as the step shrinks.

The draw now happens once, when a cell first overlaps a disk it was not already
touching, with 0.1 µm of hysteresis so a cell resting on a surface does not
leave and re-enter contact every step. `stall_probability` then means the
chance that one encounter ends in a stall — which is also what the experimental
literature measures.

## 3. The obstacle count does not scale with the box

The field of 58 disks is tuned to the 148 × 96 µm box. Enlarging the box
without scaling the count thins the mesh and raises every agarose result. The
count now scales with box area, and the realised area fraction is recorded per
run. `simulation.box_scale` defaults to 1.0, which is a no-op.

## Compatibility

Two flags in `data/config.yml`, both defaulting to the corrected behaviour:

```yaml
dynamics:
  instantaneous_reorientation: true
  stall_draw_per_contact: true
```

Set both to `false` and you get release 1.0.0 exactly. That is not a claim but
a test: `tests/reference_release_1_0_0.py` holds a frozen copy of the original
loop, and `test_legacy_flags_reproduce_release_1_0_0` asserts bit-identical
`history` and `state_history` in both media across three seeds. Preserving that
constrained the refactor to keep the RNG call order unchanged.

If you would rather the corrected behaviour be opt-in, flipping the two
defaults is a one-line change.

## What this changes in the output

Results move. At your released settings, mean net displacement over 30 seeds:

| | liquid | agarose |
|---|---|---|
| ratio, new / old | 1.04–1.10 | 1.09–2.46 |

The agarose numbers move most, which is expected: that is where the stall rule
applied.

## Tests

17 tests, about 35 seconds, no framework required (`pytest tests` also works).
They cover both dynamics paths, that `stall_entries <= contact_events`, that
the realised per-encounter stall rate reproduces `stall_probability` at every
step, that the grid obstacle index matches a linear scan over 20 000 random
points, and that box scaling holds the obstacle area fraction.

The three that fail on `main`:

- `test_stall_occupancy_does_not_grow_as_the_time_step_shrinks`
- `test_net_displacement_is_step_independent`
- `test_liquid_diffusivity_matches_the_persistence_relation`

## What we did not change

`plotting.py` and `io_utils.py` are untouched. We did not regenerate
`docs/ppro_tracks.html`, which will change visibly — happy to do that if you
want it in the same PR.

We also recalibrated the turning parameters for our own figures, because the
delivered values gave persistence times 0.80× to 6.16× our measured ones. That
is a separate change to the parameter table and is not in this PR.
