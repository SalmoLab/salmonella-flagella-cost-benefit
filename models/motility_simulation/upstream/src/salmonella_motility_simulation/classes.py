# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
from dataclasses import dataclass
import numpy as np  # pyright: ignore[reportMissingImports]


@dataclass(frozen=True)
class MotilityParameters:
    """Phenotype- and medium-specific model parameters loaded from CSV."""

    phenotype: str
    medium: str
    color: str
    motile_fraction: float
    run_speed_um_s: float
    rotational_diffusion_rad2_s: float
    reorientation_rate_s: float
    reorientation_duration_s: float
    turn_angle_sd_rad: float
    passive_diffusion_um2_s: float
    stall_probability: float
    stall_mean_duration_s: float


@dataclass(frozen=True)
class ObstacleField:
    """Simple non-overlapping disk field used for the agarose-like mesh."""

    x_um: np.ndarray
    y_um: np.ndarray
    r_um: np.ndarray

    @property
    def n_obstacles(self) -> int:
        return int(self.x_um.size)
