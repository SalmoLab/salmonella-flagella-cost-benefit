"""Parameter-table loader of the corrected model.

Same contract as ``salmonella_motility_simulation.__main__.load_parameter_table``
with one difference: ``reorientation_duration_s`` is not a required column and is
not read.  The corrected model reorients instantaneously, so the value has
nothing to control.

A table that still carries the column loads, and the column is ignored: the
frozen delivered table is immutable provenance and must stay loadable for the
diagnostic run.  :func:`ignored_columns` reports what was dropped, so a
provenance record can state it rather than leave it implicit.  Because
:class:`~salmonella_motility_corrected.classes.MotilityParameters` has no such
field, an ignored value cannot reach the dynamics by any route.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from salmonella_motility_corrected.classes import MotilityParameters

#: Columns the corrected model needs.
REQUIRED_COLUMNS = frozenset(
    {
        "phenotype",
        "medium",
        "color",
        "motile_fraction",
        "run_speed_um_s",
        "rotational_diffusion_rad2_s",
        "reorientation_rate_s",
        "turn_angle_sd_rad",
        "passive_diffusion_um2_s",
        "stall_probability",
        "stall_mean_duration_s",
    }
)

#: Columns of the upstream table that the corrected model deliberately drops.
RETIRED_COLUMNS = frozenset({"reorientation_duration_s"})


def ignored_columns(csv_path: Path) -> list[str]:
    """Return the retired columns a table still carries.

    An empty list means the table is already free of retired parameters.
    """
    header = pd.read_csv(csv_path, nrows=0)
    return sorted(RETIRED_COLUMNS.intersection(header.columns))


def load_parameter_table(csv_path: Path) -> dict[tuple[str, str], MotilityParameters]:
    """Load and validate phenotype-by-medium parameters for the corrected model.

    Values are clipped exactly as upstream clips them, so a table that loads
    under both loaders gives the same numbers to the shared fields.
    """
    frame = pd.read_csv(csv_path)
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns in {csv_path}: {sorted(missing)}")

    table: dict[tuple[str, str], MotilityParameters] = {}
    for row in frame.to_dict(orient="records"):
        key = (str(row["phenotype"]), str(row["medium"]))
        table[key] = MotilityParameters(
            phenotype=str(row["phenotype"]),
            medium=str(row["medium"]),
            color=str(row["color"]),
            motile_fraction=float(np.clip(row["motile_fraction"], 0.0, 1.0)),
            run_speed_um_s=float(max(row["run_speed_um_s"], 0.0)),
            rotational_diffusion_rad2_s=float(max(row["rotational_diffusion_rad2_s"], 0.0)),
            reorientation_rate_s=float(max(row["reorientation_rate_s"], 0.0)),
            turn_angle_sd_rad=float(max(row["turn_angle_sd_rad"], 1.0e-6)),
            passive_diffusion_um2_s=float(max(row["passive_diffusion_um2_s"], 0.0)),
            stall_probability=float(np.clip(row["stall_probability"], 0.0, 1.0)),
            stall_mean_duration_s=float(max(row["stall_mean_duration_s"], 1.0e-6)),
        )
    return table
