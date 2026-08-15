"""Obstacle fields that keep their density when the box grows.

Three things live here.

``scaled_config`` enlarges the simulation box and scales the obstacle count with
the box **area**.  The upstream count, 58 disks in 148 x 96 um, is tuned to that
one box.  Enlarging the box without scaling the count dilutes the mesh, which
would raise every agarose observable and look like a result.

``obstacle_area_fraction`` reports the realised fraction of the box covered by
disks.  It is the check that the scaling worked: it must stay at the value of
the published box whatever the box size.

``ObstacleIndex`` answers the overlap query in constant time instead of scanning
every disk.  The upstream helper is linear in the obstacle count, which is fine
for 58 disks and hopeless for the thousands an enlarged box needs.  The index
returns exactly what the upstream helper returns, including its tie rule; the
test suite asserts that on random points.

Setup:
    PYTHONPATH=models/motility_simulation/corrected/src python -c "..."

Complexity: building the index is O(obstacles); one query is O(disks per grid
cell), which the cell size holds at a small constant.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

import numpy as np

from salmonella_motility_corrected.vendored import ObstacleField

#: Empty candidate list, shared so a query on empty space allocates nothing.
_NO_CANDIDATES = np.empty(0, dtype=np.int64)


def scaled_config(config: dict[str, Any], box_scale: float) -> dict[str, Any]:
    """Return the config with the box enlarged and the obstacle count rescaled.

    The box grows by ``box_scale`` in each direction, so its area grows by
    ``box_scale ** 2`` and the obstacle count grows with it.  Disk radii are
    untouched, so the mesh a cell meets keeps its length scale and its number
    density; only the domain gets bigger.

    Example:
        >>> config = {"simulation": {"box_width_um": 148.0, "box_height_um": 96.0},
        ...           "obstacles": {"count": 58}}
        >>> out = scaled_config(config, 2.0)
        >>> out["simulation"]["box_width_um"], out["obstacles"]["count"]
        (296.0, 232)
    """
    if box_scale <= 0.0:
        raise ValueError(f"box_scale must be positive, got {box_scale}")
    scaled = {key: dict(value) for key, value in config.items()}
    simulation = scaled["simulation"]
    simulation["box_width_um"] = float(config["simulation"]["box_width_um"]) * box_scale
    simulation["box_height_um"] = float(config["simulation"]["box_height_um"]) * box_scale
    scaled["obstacles"]["count"] = int(round(int(config["obstacles"]["count"]) * box_scale**2))
    scaled["box_scale"] = float(box_scale)
    return scaled


def obstacle_area_fraction(
    field: ObstacleField | None, width_um: float, height_um: float
) -> float:
    """Return the fraction of the box covered by obstacle disks.

    Disks never overlap, so the summed disk area is the covered area.  Report
    this against the published-box value whenever the box changes: it is the
    evidence that an enlarged domain did not dilute the mesh.

    Example:
        >>> import numpy as np
        >>> field = ObstacleField(np.array([10.0]), np.array([10.0]), np.array([2.0]))
        >>> round(obstacle_area_fraction(field, 100.0, 100.0), 6)
        0.001257
    """
    if field is None or field.n_obstacles == 0:
        return 0.0
    return float(np.pi * np.square(field.r_um).sum() / (width_um * height_um))


def make_obstacle_field(config: dict[str, Any], seed: int = 0) -> ObstacleField:
    """Generate the same disk field as upstream, without its quadratic cost.

    The upstream generator tests each candidate disk against every disk already
    placed, which is fine for 58 disks and quadratic for the thousands an
    enlarged box needs.  This version keeps placed disks in a uniform grid and
    tests only the neighbourhood a conflict could come from.

    The random stream is consumed in exactly the upstream order -- radius, x, y
    per attempt -- and the acceptance rule is unchanged, so for any seed and any
    config this returns the **identical** field.  ``test_fast_generator_matches
    _upstream`` asserts that.

    Complexity is O(attempts) with a bounded neighbourhood test, against O(n^2)
    upstream.
    """
    box_width_um = float(config["simulation"]["box_width_um"])
    box_height_um = float(config["simulation"]["box_height_um"])
    n_obstacles = int(config["obstacles"]["count"])
    radius_range_um = config["obstacles"]["radius_range_um"]
    clearance_um = float(config["obstacles"]["clearance_um"])

    rng = np.random.default_rng(seed)
    # Any conflicting pair is closer than r + ro + clearance, which is at most
    # twice the largest radius plus the clearance.  A grid on that spacing puts
    # every possible conflict in the 3 x 3 cells around the candidate.
    cell_um = 2.0 * float(max(radius_range_um)) + clearance_um
    # A plain dict with ``get``, not a defaultdict: probing a neighbour must not
    # create an entry, or the grid fills with empty cells as the field grows.
    grid: dict[tuple[int, int], list[tuple[float, float, float]]] = {}
    circles: list[tuple[float, float, float]] = []
    attempts = 0
    max_attempts = n_obstacles * 300

    while len(circles) < n_obstacles and attempts < max_attempts:
        attempts += 1
        radius = float(rng.uniform(*radius_range_um))
        x = float(rng.uniform(radius + 1.8, box_width_um - radius - 1.8))
        y = float(rng.uniform(radius + 1.8, box_height_um - radius - 1.8))
        ix, iy = int(math.floor(x / cell_um)), int(math.floor(y / cell_um))
        clear = True
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for xo, yo, ro in grid.get((ix + dx, iy + dy), ()):
                    if (x - xo) ** 2 + (y - yo) ** 2 < (radius + ro + clearance_um) ** 2:
                        clear = False
                        break
                if not clear:
                    break
            if not clear:
                break
        if clear:
            circles.append((x, y, radius))
            grid.setdefault((ix, iy), []).append((x, y, radius))

    if not circles:
        return ObstacleField(np.empty(0), np.empty(0), np.empty(0))
    arr = np.asarray(circles, dtype=float)
    return ObstacleField(x_um=arr[:, 0], y_um=arr[:, 1], r_um=arr[:, 2])


class ObstacleIndex:
    """Uniform-grid lookup of the overlapping obstacle with deepest penetration.

    The grid cell is the largest disk radius, so any disk that a query point can
    overlap has its centre in the query cell or one of its eight neighbours.
    Candidates are held in ascending global index, so a tie in penetration
    resolves to the lowest index -- the same disk ``numpy.argmax`` picks in the
    upstream linear scan.
    """

    def __init__(self, field: ObstacleField | None, width_um: float, height_um: float) -> None:
        self.field = field
        self.width_um = float(width_um)
        self.height_um = float(height_um)
        self.n_obstacles = 0 if field is None else int(field.n_obstacles)
        self._buckets: dict[tuple[int, int], np.ndarray] = {}
        self._neighbourhoods: dict[tuple[int, int], np.ndarray] = {}
        if self.n_obstacles == 0:
            self._cell_um = 1.0
            return
        assert field is not None
        self._x = np.asarray(field.x_um, dtype=float)
        self._y = np.asarray(field.y_um, dtype=float)
        self._r = np.asarray(field.r_um, dtype=float)
        self._cell_um = float(self._r.max())
        raw: dict[tuple[int, int], list[int]] = defaultdict(list)
        for index in range(self.n_obstacles):
            raw[self._cell_of(self._x[index], self._y[index])].append(index)
        self._buckets = {
            key: np.asarray(sorted(values), dtype=np.int64) for key, values in raw.items()
        }

    def _cell_of(self, x_um: float, y_um: float) -> tuple[int, int]:
        return (int(math.floor(x_um / self._cell_um)), int(math.floor(y_um / self._cell_um)))

    def _candidates(self, x_um: float, y_um: float) -> np.ndarray:
        """Return the disks whose centre lies in the 3 x 3 cells around a point."""
        key = self._cell_of(x_um, y_um)
        cached = self._neighbourhoods.get(key)
        if cached is not None:
            return cached
        ix, iy = key
        parts = [
            bucket
            for dx in (-1, 0, 1)
            for dy in (-1, 0, 1)
            if (bucket := self._buckets.get((ix + dx, iy + dy))) is not None
        ]
        merged = np.sort(np.concatenate(parts)) if parts else _NO_CANDIDATES
        self._neighbourhoods[key] = merged
        return merged

    def nearest_overlapping(self, x_um: float, y_um: float) -> int | None:
        """Return the overlapping disk with the largest penetration, or ``None``.

        Identical in result to
        ``salmonella_motility_simulation.simulation.nearest_overlapping_obstacle``.
        """
        if self.n_obstacles == 0:
            return None
        candidates = self._candidates(x_um, y_um)
        if candidates.size == 0:
            return None
        dx = x_um - self._x[candidates]
        dy = y_um - self._y[candidates]
        penetration = self._r[candidates] - np.sqrt(dx * dx + dy * dy)
        best = int(np.argmax(penetration))
        if penetration[best] <= 0.0:
            return None
        return int(candidates[best])

    def centre_distance(self, x_um: float, y_um: float, index: int) -> float:
        """Return the distance from a point to the centre of one disk."""
        return math.hypot(x_um - self._x[index], y_um - self._y[index])

    def radius(self, index: int) -> float:
        """Return the radius of one disk."""
        return float(self._r[index])

    def centre(self, index: int) -> tuple[float, float]:
        """Return the centre of one disk."""
        return float(self._x[index]), float(self._y[index])
