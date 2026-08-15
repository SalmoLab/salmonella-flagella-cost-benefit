"""Parameter container of the corrected model.

The only difference from ``salmonella_motility_simulation.classes`` is that
``reorientation_duration_s`` is **gone**.  The corrected model reorients
instantaneously, so a reorientation duration has nothing to control.  The field
is removed rather than set to zero, so a table that still carries a duration
cannot silently reach the dynamics.

See ``models/motility_simulation/corrected/README.md`` for the reasoning.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MotilityParameters:
    """Phenotype- and medium-specific parameters of the corrected model.

    Every field carries the unit of its suffix: ``_um_s`` is micrometres per
    second, ``_rad2_s`` is radians squared per second, ``_um2_s`` is micrometres
    squared per second.

    ``stall_probability`` is a **per-contact-event** probability: the chance that
    one encounter with one obstacle ends in a stall.  In the upstream model the
    same name meant a per-time-step probability, which made stall occupancy grow
    without limit as the step shrank.  See the README.
    """

    phenotype: str
    medium: str
    color: str
    motile_fraction: float
    run_speed_um_s: float
    rotational_diffusion_rad2_s: float
    reorientation_rate_s: float
    turn_angle_sd_rad: float
    passive_diffusion_um2_s: float
    stall_probability: float
    stall_mean_duration_s: float
