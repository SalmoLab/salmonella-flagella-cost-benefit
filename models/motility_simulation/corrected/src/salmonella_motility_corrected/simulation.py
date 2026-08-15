"""Corrected dynamics of the active-particle motility model.

This module replaces one upstream function,
``salmonella_motility_simulation.simulation.simulate_population``.  Every helper
it does not replace is imported from the vendored upstream and used unchanged.

Two corrections, and what each one fixes
----------------------------------------

**1. Reorientation is instantaneous.**  The parameters are fitted through the
model's own persistence relation,

    tau = 1 / (D_theta + lambda * (1 - exp(-sigma^2 / 2)))

which has no duration term.  It describes a walker that turns instantaneously
and swims the whole time.  The upstream loop instead parked the cell in a
non-advancing ``reorient`` state for ``reorientation_duration_s`` and applied the
heading kick when that timer expired.  Parameters were therefore fitted with one
model and simulated with another.  A cell swam only 60 % to 80 % of the time, and
the effective diffusivity of a run-and-tumble walker scales as the square of that
ballistic fraction, which predicts 0.36 to 0.64 of the measured value.

The correction applies the heading kick at the transition and removes the dwell.
``reorientation_duration_s`` is then not a parameter of the model at all, so it
is absent from :class:`~salmonella_motility_corrected.classes.MotilityParameters`
rather than set to zero.  Its upstream value, 0.05 s, was exactly the upstream
time step, which is evidence it was never a measured duration.  The ``reorient``
state id stays in the config for file compatibility but is never occupied.

**2. The stall test fires once per contact event.**  The upstream loop drew
against ``stall_probability`` at *every* time step in which the proposed step
overlapped an obstacle.  A sliding or stalled cell was re-drawn each step and its
stall timer reset, so stall occupancy rose without limit as the step shrank: the
observable did not converge.  The correction draws once, on the step where the
cell first overlaps an obstacle it was not already touching.  ``stall_probability``
then means the chance that one encounter ends in a stall -- which is what Grognot
et al. 2023 measured (stall frequency, ratio 1.7 +/- 0.2), so the parameter
finally means what its literature anchor means.

A cell counts as still touching the same disk until its centre is farther than
:data:`CONTACT_RELEASE_UM` beyond the disk surface.  A bare overlap test would
not do: a stalled cell is parked one part in a million outside the surface, so it
would leave and re-enter contact on almost every step and the re-draw would come
back.

What is **not** changed
-----------------------
Run kinematics, rotational diffusion, the translational noise scales, the
projection and sliding geometry, the reflecting box and the obstacle generator
are upstream behaviour, imported and called unchanged.

One noise scale is renamed, not revalued.  Upstream wrote the stalled-cell
translational noise scale as a bare ``0.20`` inside the loop.  It is now
:data:`STALL_TRANSLATIONAL_SCALE` and is read from the config when a caller
supplies ``noise.stall_translational_scale``.  The number is identical, so the
dynamics are unchanged; only its visibility is.

The four noise scales -- ``run_translational_scale`` 0.12,
``stall_translational_scale`` 0.20, ``stall_slide_fraction`` 0.28 and
``stall_rotational_diffusion_scale`` 1.8 -- have no source.  They also order
translational noise the wrong way round: a running cell gets 0.12 of the passive
diffusion coefficient, a stalled cell 0.20 and a non-motile cell 1.00, so a
swimming cell diffuses about eight times less than a stopped one.  The size of
that defect is measured, not assumed; see
docs/revision_2026-08-12/motility_parameter_sources.md.

Setup:
    PYTHONPATH=models/motility_simulation/corrected/src:$PWD/src \\
        .venv/bin/python -c "from salmonella_motility_corrected import simulate_population"

Complexity is O(steps * cells) with the obstacle query held at a constant by the
grid index, so an enlarged box costs no more per step than the published one.
Pitfall: a different time step consumes the random stream differently, so the
same seed is a different realisation; compare group means, never single seeds.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from salmonella_motility_corrected.classes import MotilityParameters
from salmonella_motility_corrected.obstacles import (
    ObstacleIndex,
    obstacle_area_fraction,
)
from salmonella_motility_corrected.vendored import (
    ObstacleField,
    project_to_surface,
    reflect_in_box,
    sample_free_positions,
)

#: How far beyond a disk surface a cell must travel before the contact counts as
#: over, in micrometres.  It is far larger than the 1e-6 um projection offset and
#: than one step of stall noise, and far smaller than the 2.5 um smallest disk
#: radius, so it separates "still touching" from "left and came back" without
#: merging two genuinely different encounters.
CONTACT_RELEASE_UM = 0.1

#: Translational-noise scale of a stalled cell, as a multiple of the passive
#: diffusion coefficient.  Upstream wrote this number as a bare literal inside
#: the integration loop, so it appeared in no config file and no parameter
#: table.  It is named here and read from
#: ``config["noise"]["stall_translational_scale"]`` when a caller supplies that
#: key, so the value can be declared and varied instead of being invisible.
#: The upstream ``config.yml`` is immutable provenance and does not carry the
#: key; the builders inject it.  The value itself has no source.  It is one of
#: four nominal noise scales listed in Supplementary Table X; see
#: docs/revision_2026-08-12/motility_parameter_sources.md for what is known
#: about them and for the measured size of their effect.
STALL_TRANSLATIONAL_SCALE = 0.20


def simulate_population(
    config: dict[str, Any],
    params: MotilityParameters,
    obstacles: ObstacleField | None,
    seed: int,
) -> dict[str, Any]:
    """Simulate one phenotype in one environment under the corrected dynamics.

    Returns the upstream result keys plus contact diagnostics.  ``history`` has
    shape ``(steps + 1, cells, 2)`` in micrometres and ``state_history`` has
    shape ``(steps + 1, cells)``.

    ``contact_events`` counts every first overlap with a disk the cell was not
    already touching, and ``stall_entries`` counts how many of those ended in a
    stall.  Their ratio estimates the realised per-encounter stall probability
    and must not drift with the time step.
    """
    state_run: int = config["states"]["run"]
    state_stalled: int = config["states"]["stalled"]
    state_nonmotile: int = config["states"]["non_motile"]
    run_translation_noise_scale: float = config["noise"]["run_translational_scale"]
    stall_slide_fraction: float = config["noise"]["stall_slide_fraction"]
    stall_rotational_diffusion_scale: float = config["noise"]["stall_rotational_diffusion_scale"]
    stall_translation_noise_scale: float = float(
        config["noise"].get("stall_translational_scale", STALL_TRANSLATIONAL_SCALE)
    )

    dt_s: float = config["simulation"]["dt_s"]
    duration_s: float = config["simulation"]["track_duration_s"]
    n_cells: int = config["simulation"]["n_cells"]
    box_width_um: float = config["simulation"]["box_width_um"]
    box_height_um: float = config["simulation"]["box_height_um"]

    rng = np.random.default_rng(seed)
    n_steps = int(round(duration_s / dt_s))

    pos = sample_free_positions(n_cells, box_width_um, box_height_um, obstacles, seed=seed + 1)
    theta = rng.uniform(-math.pi, math.pi, size=n_cells)
    is_motile = rng.random(n_cells) < params.motile_fraction
    state = np.where(is_motile, state_run, state_nonmotile).astype(np.int8)
    timer = np.zeros(n_cells, dtype=float)
    # Index of the disk each cell is currently touching; -1 means free.
    contact = np.full(n_cells, -1, dtype=np.int64)
    history = np.zeros((n_steps + 1, n_cells, 2), dtype=float)
    state_history = np.zeros((n_steps + 1, n_cells), dtype=np.int8)
    history[0] = pos
    state_history[0] = state

    index = ObstacleIndex(obstacles, box_width_um, box_height_um)
    passive_sigma = math.sqrt(2.0 * params.passive_diffusion_um2_s * dt_s)
    run_sigma = math.sqrt(
        2.0 * params.passive_diffusion_um2_s * run_translation_noise_scale * dt_s
    )
    stall_sigma = math.sqrt(
        2.0 * params.passive_diffusion_um2_s * stall_translation_noise_scale * dt_s
    )
    turn_probability = min(params.reorientation_rate_s * dt_s, 1.0)
    run_theta_sigma = math.sqrt(2.0 * params.rotational_diffusion_rad2_s * dt_s)
    stall_theta_sigma = math.sqrt(
        2.0 * params.rotational_diffusion_rad2_s * stall_rotational_diffusion_scale * dt_s
    )

    contact_events = 0
    stall_entries = 0
    reorientations = 0

    for step in range(1, n_steps + 1):
        for i in range(n_cells):
            x_old, y_old = pos[i]
            theta_i = theta[i]
            state_i = int(state[i])
            new_x, new_y = x_old, y_old

            if state_i == state_nonmotile:
                new_x += rng.normal(0.0, passive_sigma)
                new_y += rng.normal(0.0, passive_sigma)

            elif state_i == state_run:
                theta_i += run_theta_sigma * rng.normal()
                # Correction 1.  The turn is instantaneous: the heading kick is
                # applied here, at the transition, and the cell keeps swimming on
                # this same step.  There is no non-advancing dwell.
                if rng.random() < turn_probability:
                    theta_i += rng.normal(0.0, params.turn_angle_sd_rad)
                    reorientations += 1
                new_x += params.run_speed_um_s * dt_s * math.cos(theta_i) + rng.normal(
                    0.0, run_sigma
                )
                new_y += params.run_speed_um_s * dt_s * math.sin(theta_i) + rng.normal(
                    0.0, run_sigma
                )

            elif state_i == state_stalled:
                timer[i] -= dt_s
                theta_i += stall_theta_sigma * rng.normal()
                new_x += rng.normal(0.0, stall_sigma)
                new_y += rng.normal(0.0, stall_sigma)
                if timer[i] <= 0.0:
                    theta_i += rng.normal(0.0, params.turn_angle_sd_rad)
                    state_i = state_run
                    timer[i] = 0.0

            if index.n_obstacles and state_i in (state_run, state_stalled):
                overlap = index.nearest_overlapping(new_x, new_y)
                if overlap is None:
                    # Correction 2 bookkeeping.  The contact ends only once the
                    # cell is clearly clear of the disk, not on the first step
                    # its centre sits a rounding error outside the surface.
                    previous = int(contact[i])
                    if previous >= 0 and index.centre_distance(
                        new_x, new_y, previous
                    ) > index.radius(previous) + CONTACT_RELEASE_UM:
                        contact[i] = -1
                else:
                    cx, cy = index.centre(overlap)
                    radius = index.radius(overlap)
                    surface_x, surface_y = project_to_surface(
                        new_x,
                        new_y,
                        cx,
                        cy,
                        radius,
                        fallback_normal=(math.cos(theta_i), math.sin(theta_i)),
                    )
                    normal_x = surface_x - cx
                    normal_y = surface_y - cy
                    norm = math.hypot(normal_x, normal_y)
                    normal_x /= norm
                    normal_y /= norm
                    tangent_x = -normal_y
                    tangent_y = normal_x
                    step_x = new_x - x_old
                    step_y = new_y - y_old
                    tangent_component = step_x * tangent_x + step_y * tangent_y
                    if abs(tangent_component) < 1.0e-9:
                        tangent_component = (
                            params.run_speed_um_s * dt_s * (1.0 if rng.random() < 0.5 else -1.0)
                        )

                    # Correction 2.  One draw per encounter.  ``and`` short
                    # circuits, so a continued contact consumes no random number
                    # and can neither stall again nor reset a running timer.
                    is_new_contact = int(contact[i]) != overlap
                    if is_new_contact:
                        contact_events += 1
                    if is_new_contact and rng.random() < params.stall_probability:
                        stall_entries += 1
                        state_i = state_stalled
                        timer[i] = rng.exponential(params.stall_mean_duration_s)
                        new_x, new_y = surface_x, surface_y
                    else:
                        slide_dx = tangent_x * tangent_component * stall_slide_fraction
                        slide_dy = tangent_y * tangent_component * stall_slide_fraction
                        new_x = surface_x + slide_dx
                        new_y = surface_y + slide_dy
                        theta_i = math.atan2(tangent_y, tangent_x)
                        if tangent_component < 0.0:
                            theta_i += math.pi
                        second_overlap = index.nearest_overlapping(new_x, new_y)
                        if second_overlap is not None:
                            second_x, second_y = index.centre(second_overlap)
                            new_x, new_y = project_to_surface(
                                new_x,
                                new_y,
                                second_x,
                                second_y,
                                index.radius(second_overlap),
                                fallback_normal=(normal_x, normal_y),
                            )
                    contact[i] = overlap

            new_x, new_y, theta_i = reflect_in_box(
                new_x, new_y, theta_i, box_width_um, box_height_um
            )
            pos[i] = (new_x, new_y)
            theta[i] = theta_i
            state[i] = state_i

        history[step] = pos
        state_history[step] = state

    return {
        "history": history,
        "state_history": state_history,
        "is_motile": is_motile,
        "params": params,
        "obstacles": obstacles,
        "box_width_um": box_width_um,
        "box_height_um": box_height_um,
        "obstacle_area_fraction": obstacle_area_fraction(
            obstacles, box_width_um, box_height_um
        ),
        "contact_events": int(contact_events),
        "stall_entries": int(stall_entries),
        "reorientations": int(reorientations),
    }
