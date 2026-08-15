"""Core simulation logic for Salmonella motility."""

import math
from typing import Any
import numpy as np
from salmonella_motility_simulation import classes

# ---------------------------------------------------------------------------
# Obstacle generation
# ---------------------------------------------------------------------------


def make_obstacle_field(
    config: dict[str, Any],
    seed: int = 0,
) -> classes.ObstacleField:
    """Generate a reproducible non-overlapping disk field."""

    box_width_um: float = config["simulation"]["box_width_um"]
    box_height_um: float = config["simulation"]["box_height_um"]
    n_obstacles: int = config["obstacles"]["count"]
    radius_range_um: tuple[float, float] = config["obstacles"]["radius_range_um"]
    obstacle_clearance_um: float = config["obstacles"]["clearance_um"]

    rng = np.random.default_rng(seed)
    circles: list[tuple[float, float, float]] = []
    attempts = 0
    max_attempts = n_obstacles * 300

    while len(circles) < n_obstacles and attempts < max_attempts:
        attempts += 1
        radius = float(rng.uniform(*radius_range_um))
        x = float(rng.uniform(radius + 1.8, box_width_um - radius - 1.8))
        y = float(rng.uniform(radius + 1.8, box_height_um - radius - 1.8))
        if all(
            (x - xo) ** 2 + (y - yo) ** 2 >= (radius + ro + obstacle_clearance_um) ** 2
            for xo, yo, ro in circles
        ):
            circles.append((x, y, radius))

    if not circles:
        return classes.ObstacleField(np.empty(0), np.empty(0), np.empty(0))

    arr = np.asarray(circles, dtype=float)
    return classes.ObstacleField(x_um=arr[:, 0], y_um=arr[:, 1], r_um=arr[:, 2])


def sample_free_positions(
    n_cells: int,
    width_um: float,
    height_um: float,
    obstacles: classes.ObstacleField | None,
    seed: int,
) -> np.ndarray:
    """Sample initial positions while avoiding obstacle interiors."""
    rng = np.random.default_rng(seed)
    pts: list[tuple[float, float]] = []
    attempts = 0
    while len(pts) < n_cells and attempts < 20000:
        attempts += 1
        x = float(rng.uniform(1.0, width_um - 1.0))
        y = float(rng.uniform(1.0, height_um - 1.0))
        if obstacles is None or obstacles.n_obstacles == 0:
            pts.append((x, y))
            continue
        dx = x - obstacles.x_um
        dy = y - obstacles.y_um
        if np.all(dx * dx + dy * dy >= (obstacles.r_um + 0.7) ** 2):
            pts.append((x, y))
    if len(pts) != n_cells:
        raise RuntimeError("Could not place all cells outside obstacles.")
    return np.asarray(pts, dtype=float)


# ---------------------------------------------------------------------------
# Collision helpers
# ---------------------------------------------------------------------------


def nearest_overlapping_obstacle(
    x_um: float, y_um: float, obstacles: classes.ObstacleField
) -> int | None:
    """Return the overlapping obstacle with the largest penetration depth."""
    if obstacles.n_obstacles == 0:
        return None
    dx = x_um - obstacles.x_um
    dy = y_um - obstacles.y_um
    dist = np.sqrt(dx * dx + dy * dy)
    penetration = obstacles.r_um - dist
    if not np.any(penetration > 0.0):
        return None
    return int(np.argmax(np.where(penetration > 0.0, penetration, -np.inf)))


def project_to_surface(
    x_um: float,
    y_um: float,
    center_x_um: float,
    center_y_um: float,
    radius_um: float,
    fallback_normal: tuple[float, float] = (1.0, 0.0),
) -> tuple[float, float]:
    """Project an overlapping point onto the obstacle surface."""
    dx = x_um - center_x_um
    dy = y_um - center_y_um
    dist = math.hypot(dx, dy)
    if dist < 1.0e-12:
        nx, ny = fallback_normal
        norm = math.hypot(nx, ny)
        nx /= norm
        ny /= norm
        return center_x_um + nx * (radius_um + 1.0e-6), center_y_um + ny * (
            radius_um + 1.0e-6
        )
    scale = (radius_um + 1.0e-6) / dist
    return center_x_um + dx * scale, center_y_um + dy * scale


def reflect_in_box(
    x_um: float, y_um: float, theta_rad: float, width_um: float, height_um: float
) -> tuple[float, float, float]:
    """Apply reflecting boundary conditions to a proposed position."""
    x_new = x_um
    y_new = y_um
    theta_new = theta_rad
    if x_new < 0.0 or x_new > width_um:
        theta_new = math.pi - theta_new
        x_new = float(np.clip(x_new, 0.0, width_um))
    if y_new < 0.0 or y_new > height_um:
        theta_new = -theta_new
        y_new = float(np.clip(y_new, 0.0, height_um))
    return x_new, y_new, theta_new


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------


def simulate_population(
    config: dict[str, Any],
    params: classes.MotilityParameters,
    obstacles: classes.ObstacleField | None,
    seed: int,
) -> dict[str, Any]:
    """Simulate one phenotype in one environment."""

    state_run: int = config["states"]["run"]
    state_reorient: int = config["states"]["reorient"]
    state_stalled: int = config["states"]["stalled"]
    state_nonmotile: int = config["states"]["non_motile"]
    run_translation_noise_scale: float = config["noise"]["run_translational_scale"]
    reorientation_diffusion_scale: float = config["noise"][
        "reorientation_diffusion_scale"
    ]
    stall_slide_fraction: float = config["noise"]["stall_slide_fraction"]
    stall_rotational_diffusion_scale: float = config["noise"][
        "stall_rotational_diffusion_scale"
    ]

    dt_s: float = config["simulation"]["dt_s"]
    duration_s: float = config["simulation"]["track_duration_s"]
    n_cells: int = config["simulation"]["n_cells"]
    box_width_um: float = config["simulation"]["box_width_um"]
    box_height_um: float = config["simulation"]["box_height_um"]

    rng = np.random.default_rng(seed)
    n_steps = int(round(duration_s / dt_s))

    pos = sample_free_positions(
        n_cells, box_width_um, box_height_um, obstacles, seed=seed + 1
    )
    theta = rng.uniform(-math.pi, math.pi, size=n_cells)
    is_motile = rng.random(n_cells) < params.motile_fraction
    state = np.where(is_motile, state_run, state_nonmotile).astype(np.int8)
    timer = np.zeros(n_cells, dtype=float)
    history = np.zeros((n_steps + 1, n_cells, 2), dtype=float)
    state_history = np.zeros((n_steps + 1, n_cells), dtype=np.int8)
    history[0] = pos
    state_history[0] = state

    passive_sigma = math.sqrt(2.0 * params.passive_diffusion_um2_s * dt_s)
    run_sigma = math.sqrt(
        2.0 * params.passive_diffusion_um2_s * run_translation_noise_scale * dt_s
    )
    reorient_sigma = math.sqrt(
        2.0 * params.passive_diffusion_um2_s * reorientation_diffusion_scale * dt_s
    )
    stall_sigma = math.sqrt(2.0 * params.passive_diffusion_um2_s * 0.20 * dt_s)

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
                theta_i += (
                    math.sqrt(2.0 * params.rotational_diffusion_rad2_s * dt_s)
                    * rng.normal()
                )
                if rng.random() < min(params.reorientation_rate_s * dt_s, 1.0):
                    state_i = state_reorient
                    timer[i] = rng.exponential(params.reorientation_duration_s)
                    new_x += rng.normal(0.0, reorient_sigma)
                    new_y += rng.normal(0.0, reorient_sigma)
                else:
                    new_x += params.run_speed_um_s * dt_s * math.cos(
                        theta_i
                    ) + rng.normal(0.0, run_sigma)
                    new_y += params.run_speed_um_s * dt_s * math.sin(
                        theta_i
                    ) + rng.normal(0.0, run_sigma)

            elif state_i == state_reorient:
                timer[i] -= dt_s
                new_x += rng.normal(0.0, reorient_sigma)
                new_y += rng.normal(0.0, reorient_sigma)
                if timer[i] <= 0.0:
                    theta_i += rng.normal(0.0, params.turn_angle_sd_rad)
                    state_i = state_run
                    timer[i] = 0.0

            elif state_i == state_stalled:
                timer[i] -= dt_s
                theta_i += (
                    math.sqrt(
                        2.0
                        * params.rotational_diffusion_rad2_s
                        * stall_rotational_diffusion_scale
                        * dt_s
                    )
                    * rng.normal()
                )
                new_x += rng.normal(0.0, stall_sigma)
                new_y += rng.normal(0.0, stall_sigma)
                if timer[i] <= 0.0:
                    theta_i += rng.normal(0.0, params.turn_angle_sd_rad)
                    state_i = state_run
                    timer[i] = 0.0

            if obstacles is not None and state_i in (
                state_run,
                state_reorient,
                state_stalled,
            ):
                overlap = nearest_overlapping_obstacle(new_x, new_y, obstacles)
                if overlap is not None:
                    cx = float(obstacles.x_um[overlap])
                    cy = float(obstacles.y_um[overlap])
                    radius = float(obstacles.r_um[overlap])
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
                            params.run_speed_um_s
                            * dt_s
                            * (1.0 if rng.random() < 0.5 else -1.0)
                        )

                    if rng.random() < params.stall_probability:
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
                        second_overlap = nearest_overlapping_obstacle(
                            new_x, new_y, obstacles
                        )
                        if second_overlap is not None:
                            new_x, new_y = project_to_surface(
                                new_x,
                                new_y,
                                float(obstacles.x_um[second_overlap]),
                                float(obstacles.y_um[second_overlap]),
                                float(obstacles.r_um[second_overlap]),
                                fallback_normal=(normal_x, normal_y),
                            )

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
    }
