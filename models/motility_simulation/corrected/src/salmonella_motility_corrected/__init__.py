"""Corrected dynamics of the vendored Salmonella motility simulation.

The vendored upstream in ``models/motility_simulation/upstream`` is immutable
provenance and is never edited.  This package overrides exactly one upstream
function, ``simulation.simulate_population``, and adds the obstacle machinery an
enlarged domain needs.  Three defects are fixed; see ``../README.md`` for the
full argument and ``simulation.py`` for the inline reasoning.

1. Reorientation is instantaneous, matching the persistence relation the
   parameters are fitted through.  ``reorientation_duration_s`` is gone.
2. The stall test fires once per contact event, not once per time step of
   continued overlap, so stall occupancy converges and ``stall_probability``
   means a per-encounter probability.
3. Obstacle count scales with box area and the realised area fraction is
   reported, so an enlarged domain keeps the published mesh density.
"""

from __future__ import annotations

from salmonella_motility_corrected.classes import MotilityParameters
from salmonella_motility_corrected.io import (
    REQUIRED_COLUMNS,
    RETIRED_COLUMNS,
    ignored_columns,
    load_parameter_table,
)
from salmonella_motility_corrected.obstacles import (
    ObstacleIndex,
    make_obstacle_field,
    obstacle_area_fraction,
    scaled_config,
)
from salmonella_motility_corrected.simulation import (
    CONTACT_RELEASE_UM,
    STALL_TRANSLATIONAL_SCALE,
    simulate_population,
)
from salmonella_motility_corrected.vendored import ObstacleField, upstream_root

__all__ = [
    "CONTACT_RELEASE_UM",
    "STALL_TRANSLATIONAL_SCALE",
    "REQUIRED_COLUMNS",
    "RETIRED_COLUMNS",
    "MotilityParameters",
    "ObstacleField",
    "ObstacleIndex",
    "ignored_columns",
    "load_parameter_table",
    "make_obstacle_field",
    "obstacle_area_fraction",
    "scaled_config",
    "simulate_population",
    "upstream_root",
]
