"""Serialization helpers for simulation outputs.

The export format is panel-oriented so simulation runs can be persisted once and
loaded later for plotting without recomputing trajectories.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from salmonella_motility_simulation import classes

SCHEMA_VERSION = 1


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _prefix_path(prefix: Path, suffix: str) -> Path:
    return prefix.parent / f"{prefix.name}_{suffix}"


def save_bundle_tsv(panels: list[dict[str, Any]], out_prefix: Path) -> dict[str, Path]:
    """Write panel simulations as TSV tables plus a JSON metadata sidecar."""
    tracks_rows: list[dict[str, Any]] = []
    obstacle_rows: list[dict[str, Any]] = []
    metadata_panels: list[dict[str, Any]] = []

    for panel_index, panel in enumerate(panels):
        sim = panel["sim"]
        history = sim["history"]
        state_history = sim["state_history"]
        is_motile = sim["is_motile"].astype(bool)
        n_steps, n_cells = state_history.shape

        step_idx = np.repeat(np.arange(n_steps), n_cells)
        cell_idx = np.tile(np.arange(n_cells), n_steps)
        x_flat = history[:, :, 0].reshape(-1)
        y_flat = history[:, :, 1].reshape(-1)
        state_flat = state_history.reshape(-1)
        t_flat = step_idx * float(panel["dt_s"])
        motile_flat = is_motile[cell_idx]

        for row_i in range(step_idx.size):
            tracks_rows.append(
                {
                    "panel_index": panel_index,
                    "phenotype": panel["phenotype"],
                    "medium": panel["medium"],
                    "seed": int(panel["seed"]),
                    "cell_index": int(cell_idx[row_i]),
                    "step": int(step_idx[row_i]),
                    "t_s": float(t_flat[row_i]),
                    "x_um": float(x_flat[row_i]),
                    "y_um": float(y_flat[row_i]),
                    "state": int(state_flat[row_i]),
                    "is_motile": bool(motile_flat[row_i]),
                }
            )

        obstacles = sim["obstacles"]
        if obstacles is not None and obstacles.n_obstacles > 0:
            for obstacle_index, (x, y, r) in enumerate(
                zip(obstacles.x_um, obstacles.y_um, obstacles.r_um)
            ):
                obstacle_rows.append(
                    {
                        "panel_index": panel_index,
                        "phenotype": panel["phenotype"],
                        "medium": panel["medium"],
                        "seed": int(panel["seed"]),
                        "obstacle_index": obstacle_index,
                        "x_um": float(x),
                        "y_um": float(y),
                        "r_um": float(r),
                    }
                )

        metadata_panels.append(
            {
                "panel_index": panel_index,
                "phenotype": panel["phenotype"],
                "medium": panel["medium"],
                "seed": int(panel["seed"]),
                "dt_s": float(panel["dt_s"]),
                "duration_s": float(panel["duration_s"]),
                "box_width_um": float(sim["box_width_um"]),
                "box_height_um": float(sim["box_height_um"]),
                "params": asdict(sim["params"]),
            }
        )

    tracks_df = pd.DataFrame.from_records(tracks_rows)
    obstacles_df = pd.DataFrame.from_records(obstacle_rows)

    tracks_path = _prefix_path(out_prefix, "tracks.tsv")
    obstacles_path = _prefix_path(out_prefix, "obstacles.tsv")
    meta_path = _prefix_path(out_prefix, "meta.json")

    _ensure_parent(tracks_path)
    tracks_df.to_csv(tracks_path, sep="\t", index=False)

    _ensure_parent(obstacles_path)
    if obstacles_df.empty:
        obstacles_df = pd.DataFrame(
            columns=[
                "panel_index",
                "phenotype",
                "medium",
                "seed",
                "obstacle_index",
                "x_um",
                "y_um",
                "r_um",
            ]
        )
    obstacles_df.to_csv(obstacles_path, sep="\t", index=False)

    metadata = {
        "schema_version": SCHEMA_VERSION,
        "panels": metadata_panels,
    }
    _ensure_parent(meta_path)
    meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    return {
        "tracks": tracks_path,
        "obstacles": obstacles_path,
        "meta": meta_path,
    }


def load_bundle_tsv(prefix: Path) -> list[dict[str, Any]]:
    """Load panel simulations from TSV tables and metadata sidecar."""
    tracks_path = _prefix_path(prefix, "tracks.tsv")
    obstacles_path = _prefix_path(prefix, "obstacles.tsv")
    meta_path = _prefix_path(prefix, "meta.json")

    tracks = pd.read_csv(tracks_path, sep="\t")
    obstacles = pd.read_csv(obstacles_path, sep="\t")
    metadata = json.loads(meta_path.read_text(encoding="utf-8"))

    version = int(metadata.get("schema_version", 0))
    if version != SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported simulation bundle schema_version={version}; expected {SCHEMA_VERSION}."
        )

    panel_results: list[dict[str, Any]] = []
    for panel_meta in metadata["panels"]:
        panel_index = int(panel_meta["panel_index"])
        panel_tracks = tracks[tracks["panel_index"] == panel_index].copy()
        if panel_tracks.empty:
            raise ValueError(
                f"Missing rows for panel_index={panel_index} in tracks TSV"
            )

        panel_tracks = panel_tracks.sort_values(["step", "cell_index"])
        n_steps = int(panel_tracks["step"].max()) + 1
        n_cells = int(panel_tracks["cell_index"].max()) + 1
        expected_rows = n_steps * n_cells
        if len(panel_tracks) != expected_rows:
            raise ValueError(
                f"Expected {expected_rows} rows for panel_index={panel_index}, found {len(panel_tracks)}"
            )

        x_vals = panel_tracks["x_um"].to_numpy(dtype=float).reshape(n_steps, n_cells)
        y_vals = panel_tracks["y_um"].to_numpy(dtype=float).reshape(n_steps, n_cells)
        history = np.stack([x_vals, y_vals], axis=2)
        state_history = (
            panel_tracks["state"].to_numpy(dtype=np.int8).reshape(n_steps, n_cells)
        )

        first_step = panel_tracks[panel_tracks["step"] == 0].sort_values("cell_index")
        is_motile = first_step["is_motile"].to_numpy(dtype=bool)

        panel_obstacles = obstacles[obstacles["panel_index"] == panel_index].copy()
        if panel_obstacles.empty:
            obstacle_field: classes.ObstacleField | None = None
        else:
            panel_obstacles = panel_obstacles.sort_values("obstacle_index")
            obstacle_field = classes.ObstacleField(
                x_um=panel_obstacles["x_um"].to_numpy(dtype=float),
                y_um=panel_obstacles["y_um"].to_numpy(dtype=float),
                r_um=panel_obstacles["r_um"].to_numpy(dtype=float),
            )

        sim = {
            "history": history,
            "state_history": state_history,
            "is_motile": is_motile,
            "params": classes.MotilityParameters(**panel_meta["params"]),
            "obstacles": obstacle_field,
            "box_width_um": float(panel_meta["box_width_um"]),
            "box_height_um": float(panel_meta["box_height_um"]),
        }
        panel_results.append(
            {
                "phenotype": str(panel_meta["phenotype"]),
                "medium": str(panel_meta["medium"]),
                "seed": int(panel_meta["seed"]),
                "dt_s": float(panel_meta["dt_s"]),
                "duration_s": float(panel_meta["duration_s"]),
                "sim": sim,
            }
        )

    return panel_results
