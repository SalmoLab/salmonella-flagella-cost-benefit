"""The one place where the corrected model reaches into the vendored upstream.

Everything re-exported here is used **unchanged**.  Collecting the imports in one
module makes the boundary explicit: what this file lists is upstream behaviour
the correction keeps, and anything not listed is either reimplemented in
``simulation.py`` or deliberately dropped.

``models/motility_simulation/upstream`` is immutable provenance, checksummed at
commit ``96ca0e74``.  Nothing here writes to it.
"""

from __future__ import annotations

import sys
from pathlib import Path

#: Root of the vendored upstream package, four levels above this file:
#: corrected/src/salmonella_motility_corrected/vendored.py -> models/motility_simulation
_MOTILITY_ROOT = Path(__file__).resolve().parents[3]
_UPSTREAM_SRC = _MOTILITY_ROOT / "upstream/src"
if str(_UPSTREAM_SRC) not in sys.path:
    sys.path.insert(0, str(_UPSTREAM_SRC))

from salmonella_motility_simulation.classes import ObstacleField  # noqa: E402
from salmonella_motility_simulation.simulation import (  # noqa: E402
    make_obstacle_field,
    nearest_overlapping_obstacle,
    project_to_surface,
    reflect_in_box,
    sample_free_positions,
)

__all__ = [
    "ObstacleField",
    "make_obstacle_field",
    "nearest_overlapping_obstacle",
    "project_to_surface",
    "reflect_in_box",
    "sample_free_positions",
    "upstream_root",
]


def upstream_root() -> Path:
    """Return the vendored upstream directory."""
    return _MOTILITY_ROOT / "upstream"
