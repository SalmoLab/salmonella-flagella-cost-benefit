from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .registries import EXPECTED_PANEL_IDS, sha256_file

# One fixed timestamp keeps every rebuild byte-identical.
FIXED_TIMESTAMP = datetime(2026, 8, 12, 0, 0, 0)
FIXED_ZIP_TIME = (2026, 8, 12, 0, 0, 0)

# Nature Communications accepts at most 30 MB for one Source Data file.
MAX_SOURCE_DATA_FILE_BYTES = 30_000_000

FIGURE_LABELS: dict[str, str] = {
    "F1": "Figure 1",
    "F2": "Figure 2",
    "F3": "Figure 3",
    "F4": "Figure 4",
    "F5": "Figure 5",
    "F6": "Figure 6",
    "F7": "Figure 7",
    "S1": "Supplementary Figure 1",
    "S2": "Supplementary Figure 2",
    "S3": "Supplementary Figure 3",
    "S4": "Supplementary Figure 4",
    "S5": "Supplementary Figure 5",
}
FIGURE_ORDER: tuple[str, ...] = tuple(FIGURE_LABELS)

RESERVED_SHEETS: tuple[str, ...] = ("README", "INDEX", "DATA_DICTIONARY")

# Excel accepts at most 31 characters in a sheet name.
MAX_SHEET_NAME_CHARS = 31

INDEX_COLUMNS: tuple[str, ...] = (
    "panel_id",
    "sheet",
    "table_name",
    "origin",
    "source_path",
    "rows",
    "columns",
    "sha256",
)
DICTIONARY_COLUMNS: tuple[str, ...] = (
    "panel_id",
    "sheet",
    "column",
    "dtype",
    "unit",
    "source_path",
)

ORIGIN_FILE = "source file"
ORIGIN_DERIVED = "derived in this build"

# ---------------------------------------------------------------------------
# Deposited tables
# ---------------------------------------------------------------------------
# The six Supplementary Figure 4 trajectory tables go to the DOI-bearing
# repository instead of the submitted Source Data. Marc approved this on
# 14 August 2026. They are raw model output rather than measurement, they are
# exactly regenerable from the recorded seeds and parameters, and they made up
# 57.6 % of the Source Data volume. The Source Data file keeps the obstacle
# fields and two summary tables derived from these trajectories.
DEPOSIT_FIGURE = "S4"
DEPOSIT_NAME = "Supplementary_Figure_4_trajectories"
DEPOSITED_TABLE_PATHS: frozenset[str] = frozenset(
    f"data/source_data/supplementary_04/S4_{panel}_simulated_trajectories.csv.gz"
    for panel in "ABCDEF"
)
DEPOSIT_DOI_PLACEHOLDER = "[repository and DOI pending]"

# The simulator's state codes, from models/motility_simulation/upstream/data/config.yml.
SIMULATION_STATE_LABELS: dict[int, str] = {
    0: "run",
    1: "reorient",
    2: "stalled",
    3: "non_motile",
}

UNIT_LEGEND = (
    "um = micrometre; um/s = micrometre per second; um^2/s = micrometre squared "
    "per second; ng/mL = nanogram per millilitre; s = second; min = minute; "
    "1/s = per second; 1/h = per hour; rad = radian; "
    "rad^2/s = radian squared per second; "
    "% = percent; fraction (0-1) = dimensionless fraction."
)

# The column name carries the unit. An exact name wins over a suffix, because
# some names end in a suffix that means something else.
_UNIT_EXACT: dict[str, str] = {
    "_window_start_min": "min",
    "_window_end_min": "min",
    "reorientation_rate_s": "1/s",
    "rotational_diffusion_rad2_s": "rad^2/s",
    "passive_diffusion_um2_s": "um^2/s",
    "turn_angle_sd_rad": "rad",
    "stall_mean_duration_s": "s",
    "track_duration_s": "s",
    "duration_s": "s",
    "dt_s": "s",
}
_UNIT_SUFFIXES: tuple[tuple[str, str], ...] = (
    ("_um_s", "um/s"),
    ("_um2_s", "um^2/s"),
    ("_rad2_s", "rad^2/s"),
    ("_per_h", "1/h"),
    ("_1_h", "1/h"),
    ("_percent", "%"),
    ("_fraction", "fraction (0-1)"),
    ("_rad", "rad"),
    ("_um", "um"),
    ("_ng_per_mL", "ng/mL"),
    ("_s", "s"),
)
_INTERVAL_SUFFIXES: tuple[str, ...] = ("_ci95_high", "_ci95_low")

_TABLE_SUFFIXES: tuple[str, ...] = (".csv.gz", ".csv", ".parquet", ".pq")


@dataclass(frozen=True)
class SourceTable:
    """One table in the Source Data, with everything INDEX needs to describe it."""

    panel_id: str
    name: str
    frame: pd.DataFrame
    source_path: str
    sha256: str
    origin: str = ORIGIN_FILE
    sheet: str = ""

    def with_sheet(self, sheet: str) -> SourceTable:
        return SourceTable(
            self.panel_id,
            self.name,
            self.frame,
            self.source_path,
            self.sha256,
            self.origin,
            sheet,
        )


@dataclass
class TableCollection:
    """The checksum gate's result: what ships, what was dropped, what is deposited."""

    tables: list[SourceTable] = field(default_factory=list)
    superseded: list[dict[str, Any]] = field(default_factory=list)
    deposited: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Names and units
# ---------------------------------------------------------------------------


def _table_stem(path: Path) -> str:
    """Return the file name without any table extension."""
    name = path.name
    for suffix in _TABLE_SUFFIXES:
        if name.lower().endswith(suffix):
            return name[: -len(suffix)]
    return path.stem


def _panel_aliases(panel_id: str) -> tuple[str, ...]:
    """Return the names a file may use for this panel.

    The repository mixes two conventions: ``F7_D_counts`` and
    ``Figure_7D_counts``. Both name the same panel.
    """
    figure, label = panel_id.split("_", 1)
    number = figure[1:]
    if figure.startswith("S"):
        long_forms = (
            f"Supplementary_Figure_{number}{label}",
            f"Supplementary_Figure_{number}_{label}",
            f"Supplementary_{number}{label}",
        )
    else:
        long_forms = (
            f"Figure_{number}{label}",
            f"Figure_{number}_{label}",
            f"Figure_{int(number):02d}{label}",
        )
    return (panel_id, f"{figure}{label}", *long_forms)


def _table_role(panel_id: str, path: Path) -> str:
    """Return the readable role of a table, with the panel name stripped.

    >>> _table_role("F1_C", Path("F1_C_distribution.csv"))
    'distribution'
    >>> _table_role("F7_D", Path("Figure_7D_counts.csv"))
    'counts'
    """
    stem = re.sub(r"[^A-Za-z0-9_]+", "_", _table_stem(path))
    lowered = stem.lower()
    for alias in _panel_aliases(panel_id):
        if lowered == alias.lower():
            return "table"
        prefix = f"{alias.lower()}_"
        if lowered.startswith(prefix):
            return stem[len(prefix) :]
    return stem


def _table_name(panel_id: str, path: Path) -> str:
    """Return the full, untruncated name of a table."""
    return f"{panel_id}_{_table_role(panel_id, path)}"


def _sheet_name(full_name: str, used: set[str]) -> str:
    """Shorten a table name to a unique Excel sheet name.

    The name is shortened on a word boundary, never in the middle of a word.
    INDEX keeps the full name, so nothing is lost.
    """
    words = full_name.split("_")
    for count in range(len(words), 1, -1):
        candidate = "_".join(words[:count])
        if len(candidate) <= MAX_SHEET_NAME_CHARS and candidate not in used:
            used.add(candidate)
            return candidate
    base = "_".join(words[:2])[:MAX_SHEET_NAME_CHARS]
    counter = 2
    candidate = base
    while candidate in used:
        suffix = f"_{counter}"
        candidate = f"{base[: MAX_SHEET_NAME_CHARS - len(suffix)]}{suffix}"
        counter += 1
    used.add(candidate)
    return candidate


def column_unit(column: object) -> str:
    """Return the SI unit that the column name carries, or an empty string.

    The unit is read from the column name. An empty result means the name
    states no unit; it does not mean the quantity is dimensionless.

    >>> column_unit("speed_um_s")
    'um/s'
    >>> column_unit("speed_um_s_ci95_high")
    'um/s'
    >>> column_unit("grid_speed_min")
    ''
    """
    name = str(column)
    if name in _UNIT_EXACT:
        return _UNIT_EXACT[name]
    for suffix in _INTERVAL_SUFFIXES:
        if name.endswith(suffix):
            name = name[: -len(suffix)]
            break
    if name in _UNIT_EXACT:
        return _UNIT_EXACT[name]
    for suffix, unit in _UNIT_SUFFIXES:
        if name.endswith(suffix):
            return unit
    return ""


def figure_of(panel_id: str) -> str:
    """Return the figure key of a panel ID, for example ``F1`` for ``F1_C``."""
    return panel_id.split("_")[0]


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------


def provenance_documents(root: Path) -> dict[str, dict[str, Any]]:
    documents: dict[str, dict[str, Any]] = {}
    for path in sorted((root / "metadata" / "provenance").rglob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        panel_id = str(document["panel_id"])
        if panel_id in documents:
            raise ValueError(f"Duplicate central provenance for {panel_id}")
        documents[panel_id] = document
    return documents


def provenance_paths(root: Path) -> dict[str, str]:
    """Map each panel ID to the repository path of its provenance record."""
    paths: dict[str, str] = {}
    for path in sorted((root / "metadata" / "provenance").rglob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        paths[str(document["panel_id"])] = path.relative_to(root).as_posix()
    return paths


def _load_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv" or path.name.lower().endswith(".csv.gz"):
        return pd.read_csv(path, low_memory=False)
    if path.suffix.lower() in {".parquet", ".pq"}:
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported source-data table: {path}")


# ---------------------------------------------------------------------------
# Collection and the checksum gate
# ---------------------------------------------------------------------------


def _supersedes(current: pd.DataFrame, legacy: pd.DataFrame) -> bool:
    """Report whether ``current`` holds every value that ``legacy`` holds.

    The check is strict: same row count, every legacy column present, and the
    shared columns equal row for row. Only then is the legacy copy redundant.
    """
    if len(current) != len(legacy):
        return False
    shared = list(legacy.columns)
    if not set(shared) <= set(current.columns):
        return False
    left = current.loc[:, shared].reset_index(drop=True)
    right = legacy.reset_index(drop=True)
    return left.equals(right)


def _frame_digest(frame: pd.DataFrame) -> str:
    """Return the sha256 of a derived table's canonical text form."""
    return hashlib.sha256(_tsv_text(frame).encode("utf-8")).hexdigest()


def _median_of(values: pd.Series) -> float | None:
    """Return the median, or nothing when the selection is empty."""
    return float(values.median()) if len(values) else None


def collect_tables(root: Path, documents: dict[str, dict[str, Any]]) -> TableCollection:
    """Load every table whose checksum matches its audited panel provenance.

    A table enters the Source Data only through this gate. The function raises
    if a recorded checksum no longer matches the file on disk.

    Three things then happen:

    1. Some panels carry the same table twice: once under the pre-renumbering
       name in ``data/source_data/`` and once under the current name in
       ``build/source_data/``. The legacy copy is dropped, but only after the
       current copy is proven to hold every value of it.
    2. The tables listed in ``DEPOSITED_TABLE_PATHS`` are routed to the
       repository deposit instead of the Source Data.
    3. Two summary tables are derived from the deposited trajectories, so the
       Source Data still carries the quantities a reader wants to check.
    """
    loaded: list[tuple[str, Path, pd.DataFrame]] = []
    for panel_id, document in sorted(documents.items()):
        if document["status"] not in {"partial_reproduction", "reproduced"}:
            continue
        for artifact in document["outputs"]:
            relative = Path(artifact["relative_path"])
            if relative.parts[:2] not in {
                ("data", "source_data"),
                ("build", "source_data"),
                ("build", "statistics"),
            }:
                continue
            path = root / relative
            if path.suffix.lower() not in {".csv", ".parquet", ".pq", ".gz"}:
                continue
            if sha256_file(path) != artifact["sha256"]:
                raise ValueError(f"Stale provenance checksum for {relative.as_posix()}")
            loaded.append((panel_id, relative, _load_table(path)))

    collection = TableCollection()

    # 1. Drop a legacy duplicate only when the current copy contains it.
    dropped: set[int] = set()
    for position, (panel_id, relative, frame) in enumerate(loaded):
        if relative.parts[:2] != ("data", "source_data"):
            continue
        for other_panel, other_relative, other_frame in loaded:
            if other_panel != panel_id:
                continue
            if other_relative.parts[:2] != ("build", "source_data"):
                continue
            if not _supersedes(other_frame, frame):
                continue
            dropped.add(position)
            collection.superseded.append(
                {
                    "panel_id": panel_id,
                    "dropped_path": relative.as_posix(),
                    "retained_path": other_relative.as_posix(),
                    "rows": len(frame),
                    "dropped_columns": len(frame.columns),
                    "retained_columns": len(other_frame.columns),
                    "bytes_saved": (root / relative).stat().st_size,
                }
            )
            break

    # 2. Split the survivors into deposited tables and Source Data tables.
    deposited_frames: dict[str, pd.DataFrame] = {}
    kept: list[tuple[str, Path, pd.DataFrame]] = []
    for position, (panel_id, relative, frame) in enumerate(loaded):
        if position in dropped:
            continue
        posix = relative.as_posix()
        if posix in DEPOSITED_TABLE_PATHS:
            deposited_frames[panel_id] = frame
            collection.deposited.append(
                {
                    "panel_id": panel_id,
                    "source_path": posix,
                    "rows": len(frame),
                    "columns": len(frame.columns),
                    "bytes": (root / relative).stat().st_size,
                    "sha256": sha256_file(root / relative),
                }
            )
            continue
        kept.append((panel_id, relative, frame))

    records = [
        SourceTable(
            panel_id=panel_id,
            name=_table_name(panel_id, relative),
            frame=frame,
            source_path=relative.as_posix(),
            sha256=sha256_file(root / relative),
        )
        for panel_id, relative, frame in kept
    ]

    # 3. Replace the deposited trajectories with summaries of them.
    if deposited_frames:
        records = _insert_deposit_summaries(records, deposited_frames, documents)

    used_sheets: set[str] = set(RESERVED_SHEETS)
    collection.tables = [
        record.with_sheet(_sheet_name(record.name, used_sheets)) for record in records
    ]
    return collection


# ---------------------------------------------------------------------------
# Summaries of the deposited trajectories
# ---------------------------------------------------------------------------


def _cell_summary(panel_id: str, trajectory: pd.DataFrame) -> pd.DataFrame:
    """Summarize one simulated cell per row.

    The panel draws one track per cell. This table gives the numbers behind each
    track: where it starts, where it ends, how far it gets and how far it moves.
    """
    frame = trajectory.sort_values(["cell_id", "step"], kind="stable").reset_index(
        drop=True
    )
    grouped = frame.groupby("cell_id", sort=True)
    step_length = np.hypot(
        grouped["x_um"].diff().to_numpy(), grouped["y_um"].diff().to_numpy()
    )
    frame["_step_length_um"] = np.nan_to_num(step_length)
    first = grouped.first()
    last = grouped.last()
    start_x = first["x_um"]
    start_y = first["y_um"]
    excursion = np.hypot(
        frame["x_um"].to_numpy() - frame["cell_id"].map(start_x).to_numpy(),
        frame["y_um"].to_numpy() - frame["cell_id"].map(start_y).to_numpy(),
    )
    frame["_excursion_um"] = excursion
    regrouped = frame.groupby("cell_id", sort=True)
    path_length = regrouped["_step_length_um"].sum().to_numpy()
    duration_s = float(frame["time_s"].max())
    net = np.hypot(
        last["x_um"].to_numpy() - start_x.to_numpy(),
        last["y_um"].to_numpy() - start_y.to_numpy(),
    )
    return pd.DataFrame(
        {
            "panel_id": panel_id,
            "phenotype": first["phenotype"].to_numpy(),
            "medium": first["medium"].to_numpy(),
            "seed": first["seed"].to_numpy(),
            "cell_id": first.index.to_numpy(),
            "is_motile": first["is_motile"].to_numpy(),
            "initial_state": first["state"].to_numpy(),
            "final_state": last["state"].to_numpy(),
            "final_state_label": [
                SIMULATION_STATE_LABELS.get(int(state), "unknown")
                for state in last["state"].to_numpy()
            ],
            "steps": regrouped.size().to_numpy(),
            "start_x_um": start_x.to_numpy(),
            "start_y_um": start_y.to_numpy(),
            "end_x_um": last["x_um"].to_numpy(),
            "end_y_um": last["y_um"].to_numpy(),
            "net_displacement_um": net,
            "max_excursion_um": regrouped["_excursion_um"].max().to_numpy(),
            # The track length is the sum of the sampled steps, so it includes
            # diffusive jitter and depends on dt. It is not a swimming speed.
            "track_path_length_um": path_length,
            "mean_track_speed_um_s": path_length / duration_s,
        }
    )


def _condition_summary(
    panel_id: str,
    trajectory: pd.DataFrame,
    cells: pd.DataFrame,
    document: dict[str, Any],
    obstacles: pd.DataFrame | None,
) -> dict[str, Any]:
    """Summarize one panel per row: its model inputs and what the tracks show."""
    parameters = document.get("parameters", {})
    motility = parameters.get("motility_parameters", {})
    seeds = document.get("random_seeds", {})
    obstacle_config = parameters.get("obstacle_config") or {}
    radius_range = obstacle_config.get("radius_range_um") or [None, None]
    box_width = parameters.get("box_width_um")
    box_height = parameters.get("box_height_um")

    obstacle_count = 0 if obstacles is None else len(obstacles)
    area_fraction: float | None = None
    if obstacle_count and box_width and box_height:
        area_fraction = float(
            (np.pi * obstacles["radius_um"].to_numpy() ** 2).sum()
            / (float(box_width) * float(box_height))
        )

    displacement = cells["net_displacement_um"]
    motile_cells = cells[cells["is_motile"].astype(bool)]
    return {
        "panel_id": panel_id,
        "phenotype": parameters.get("phenotype"),
        "medium": parameters.get("medium"),
        "n_cells": int(cells.shape[0]),
        "n_steps": int(trajectory["step"].nunique()),
        "dt_s": parameters.get("dt_s"),
        "track_duration_s": parameters.get("track_duration_s"),
        "box_width_um": box_width,
        "box_height_um": box_height,
        # Model inputs. These are the numbers the figure legend quotes.
        "motile_fraction": motility.get("motile_fraction"),
        "run_speed_um_s": motility.get("run_speed_um_s"),
        "reorientation_rate_s": motility.get("reorientation_rate_s"),
        "rotational_diffusion_rad2_s": motility.get("rotational_diffusion_rad2_s"),
        "turn_angle_sd_rad": motility.get("turn_angle_sd_rad"),
        "passive_diffusion_um2_s": motility.get("passive_diffusion_um2_s"),
        "stall_probability": motility.get("stall_probability"),
        "stall_mean_duration_s": motility.get("stall_mean_duration_s"),
        # Seeds. These regenerate the deposited trajectories exactly.
        "panel_seed": seeds.get("panel_seed"),
        "starting_position_seed": seeds.get("starting_position_seed"),
        "obstacle_seed": seeds.get("obstacle_seed"),
        # Obstacles.
        "obstacle_count": obstacle_count,
        "obstacle_radius_min_um": radius_range[0],
        "obstacle_radius_max_um": radius_range[1],
        "obstacle_clearance_um": obstacle_config.get("clearance_um"),
        "obstacle_area_fraction": area_fraction,
        # What the tracks realize.
        "realized_motile_fraction": float(cells["is_motile"].mean()),
        "n_final_run": int((cells["final_state_label"] == "run").sum()),
        "n_final_reorient": int((cells["final_state_label"] == "reorient").sum()),
        "n_final_stalled": int((cells["final_state_label"] == "stalled").sum()),
        "n_final_non_motile": int((cells["final_state_label"] == "non_motile").sum()),
        "median_net_displacement_um": float(displacement.median()),
        "q25_net_displacement_um": float(displacement.quantile(0.25)),
        "q75_net_displacement_um": float(displacement.quantile(0.75)),
        "mean_net_displacement_um": float(displacement.mean()),
        "median_net_displacement_motile_um": _median_of(motile_cells["net_displacement_um"]),
        "median_track_path_length_um": float(cells["track_path_length_um"].median()),
        "median_track_speed_um_s": float(cells["mean_track_speed_um_s"].median()),
        # Motile cells only. This is the number to compare with run_speed_um_s.
        "median_track_speed_motile_um_s": _median_of(motile_cells["mean_track_speed_um_s"]),
        "track_x_min_um": float(trajectory["x_um"].min()),
        "track_x_max_um": float(trajectory["x_um"].max()),
        "track_y_min_um": float(trajectory["y_um"].min()),
        "track_y_max_um": float(trajectory["y_um"].max()),
    }


def _insert_deposit_summaries(
    records: list[SourceTable],
    deposited_frames: dict[str, pd.DataFrame],
    documents: dict[str, dict[str, Any]],
) -> list[SourceTable]:
    """Put the two derived summary tables at the head of the deposit's figure.

    The trajectories go to the repository deposit. These summaries stay in the
    Source Data, so a reader can check the figure without them.
    """
    obstacles = {
        record.panel_id: record.frame
        for record in records
        if record.name.endswith("_obstacles")
    }
    cell_frames: list[pd.DataFrame] = []
    condition_rows: list[dict[str, Any]] = []
    for panel_id in sorted(deposited_frames):
        cells = _cell_summary(panel_id, deposited_frames[panel_id])
        cell_frames.append(cells)
        condition_rows.append(
            _condition_summary(
                panel_id,
                deposited_frames[panel_id],
                cells,
                documents.get(panel_id, {}),
                obstacles.get(panel_id),
            )
        )
    panels = sorted(deposited_frames)
    span = f"{panels[0]}-{panels[-1]}"
    inputs = "; ".join(sorted(DEPOSITED_TABLE_PATHS))
    condition_frame = pd.DataFrame(condition_rows)
    cell_frame = pd.concat(cell_frames, ignore_index=True)
    derived = [
        SourceTable(
            panel_id=span,
            name=f"{DEPOSIT_FIGURE}_condition_summary",
            frame=condition_frame,
            source_path=inputs,
            sha256=_frame_digest(condition_frame),
            origin=ORIGIN_DERIVED,
        ),
        SourceTable(
            panel_id=span,
            name=f"{DEPOSIT_FIGURE}_cell_summary",
            frame=cell_frame,
            source_path=inputs,
            sha256=_frame_digest(cell_frame),
            origin=ORIGIN_DERIVED,
        ),
    ]
    first = next(
        (
            position
            for position, record in enumerate(records)
            if figure_of(record.panel_id) == DEPOSIT_FIGURE
        ),
        len(records),
    )
    return records[:first] + derived + records[first:]


# ---------------------------------------------------------------------------
# INDEX, DATA_DICTIONARY and README
# ---------------------------------------------------------------------------


def _index_frame(tables: list[SourceTable]) -> pd.DataFrame:
    rows = [
        {
            "panel_id": table.panel_id,
            "sheet": table.sheet,
            "table_name": table.name,
            "origin": table.origin,
            "source_path": table.source_path,
            "rows": len(table.frame),
            "columns": len(table.frame.columns),
            "sha256": table.sha256,
        }
        for table in tables
    ]
    return pd.DataFrame(rows, columns=list(INDEX_COLUMNS))


def _dictionary_frame(tables: list[SourceTable]) -> pd.DataFrame:
    rows = [
        {
            "panel_id": table.panel_id,
            "sheet": table.sheet,
            "column": str(column),
            "dtype": str(table.frame[column].dtype),
            "unit": column_unit(column),
            "source_path": table.source_path,
        }
        for table in tables
        for column in table.frame.columns
    ]
    return pd.DataFrame(rows, columns=list(DICTIONARY_COLUMNS))


def _panel_status_notes(
    figure: str,
    documents: dict[str, dict[str, Any]],
    panels_with_tables: set[str],
) -> list[str]:
    notes: list[str] = []
    for panel_id in sorted(p for p in EXPECTED_PANEL_IDS if figure_of(p) == figure):
        if panel_id in panels_with_tables:
            continue
        status = documents.get(panel_id, {}).get("status", "no_provenance_record")
        notes.append(f"{panel_id} ({status})")
    return notes


def _deposit_readme_rows(
    deposited: list[dict[str, Any]], documents: dict[str, dict[str, Any]]
) -> list[list[Any]]:
    """Rows that tell a reader exactly what was deposited and how to rebuild it."""
    if not deposited:
        return []
    total = sum(entry["bytes"] for entry in deposited)
    rows_total = sum(entry["rows"] for entry in deposited)
    software = documents.get(deposited[0]["panel_id"], {}).get("software", {})
    versions = "; ".join(
        f"{key}={value}"
        for key, value in sorted(software.items())
        if key in {"python", "numpy", "pandas", "upstream_commit"}
    )
    rows: list[list[Any]] = [
        [
            "Deposited, not in this file",
            f"{len(deposited)} simulated-trajectory tables, {rows_total:,} rows, "
            f"{total / 1e6:.1f} MB compressed",
        ],
        [
            "Why deposited",
            "They are raw model output, not measurement, and they are exactly "
            "regenerable from the seeds and parameters recorded here. Keeping "
            "them out holds every Source Data file within the 30 MB limit.",
        ],
        [
            "Where they will live",
            f"The DOI-bearing repository deposit, {DEPOSIT_DOI_PLACEHOLDER}. "
            f"The build writes the same bundle to "
            f"build/source_data/deposit/{DEPOSIT_NAME}/.",
        ],
        [
            "What replaces them here",
            f"{DEPOSIT_FIGURE}_condition_summary gives the model inputs, the "
            f"seeds and the population statistics of every panel. "
            f"{DEPOSIT_FIGURE}_cell_summary gives one row per simulated cell: "
            "start, end, net displacement, path length and mean speed. Together "
            "they carry the numbers behind every track the figure draws.",
        ],
        [
            "How to regenerate them",
            "Run the command in the panel provenance record, for example "
            "'.venv/bin/python3.12 analyses/supplementary_04/build_s4.py "
            "--panel A'. The seeds are in the condition summary "
            "(panel_seed, starting_position_seed, obstacle_seed) and in the "
            "provenance record.",
        ],
        [
            "How to read the track speed",
            "A track path length is the sum of the sampled steps. It therefore "
            "includes diffusive jitter and grows as the time step shrinks. It "
            "is not a swimming speed. Compare run_speed_um_s with "
            "median_track_speed_motile_um_s, which counts motile cells only. "
            "A non-motile cell still shows a track speed; that is Brownian "
            "motion, not swimming.",
        ],
        [
            "Why realized and input fractions differ",
            "realized_motile_fraction counts the motile cells of one finite "
            "population. With n_cells per panel it scatters around the "
            "motile_fraction the model was given.",
        ],
    ]
    if versions:
        rows.append(["Software that produced them", versions])
    for entry in deposited:
        rows.append(
            [
                f"Deposited {entry['panel_id']}",
                f"{entry['source_path']} — {entry['rows']:,} rows, "
                f"{entry['columns']} columns, sha256 {entry['sha256']}",
            ]
        )
    return rows


def _figure_readme(
    figure: str,
    file_name: str,
    file_format: str,
    tables: list[SourceTable],
    documents: dict[str, dict[str, Any]],
    paths: dict[str, str],
    deposited: list[dict[str, Any]],
) -> pd.DataFrame:
    label = FIGURE_LABELS[figure]
    panels_with_tables = {
        panel_id
        for table in tables
        for panel_id in table.panel_id.split("-")
        if panel_id in EXPECTED_PANEL_IDS
    }
    if file_format == "zip":
        layout = (
            "README.txt, INDEX.txt and DATA_DICTIONARY.txt describe the data. "
            "One tab-separated .txt file holds one table."
        )
    else:
        layout = (
            "The README, INDEX and DATA_DICTIONARY sheets describe the data. "
            "One sheet holds one table."
        )
    rows: list[list[Any]] = [
        ["Source Data file", f"Source Data {label}"],
        ["File name", file_name],
        ["Figure", label],
        ["Release status", "PARTIAL — covers the panels that reproduce today"],
        ["Reference manuscript", "2026-07-21 merged coauthor version"],
        ["Figure revision", "2026-08-12; seven main figures"],
        ["Panels in this file", "; ".join(sorted(panels_with_tables))],
        [
            "Panels without tables",
            "; ".join(_panel_status_notes(figure, documents, panels_with_tables))
            or "none",
        ],
        ["Tables in this file", len(tables)],
        ["Layout", layout],
        [
            "Units",
            "The column name carries the unit. DATA_DICTIONARY gives the unit of "
            "every column. " + UNIT_LEGEND,
        ],
        [
            "Table names",
            "A table name carries the current panel ID and the role of the "
            "table. INDEX gives the full name and the source path of every "
            "table.",
        ],
        [
            "Provenance",
            "Each provenance record lists the command, inputs, software versions "
            "and random seeds of its panel.",
        ],
    ]
    for panel_id in sorted(panels_with_tables):
        rows.append([f"Provenance {panel_id}", paths.get(panel_id, "")])
    rows.extend(_deposit_readme_rows(deposited, documents))
    rows.extend(
        [
            [
                "Checksum rule",
                "A table is included only when its sha256 matches the audited "
                "panel provenance. INDEX names the origin of every table: a "
                f"'{ORIGIN_FILE}', or '{ORIGIN_DERIVED}' from the files it lists.",
            ],
            [
                "INDEX",
                "INDEX lists the source path, row count, column count and sha256 "
                "of every table in this file.",
            ],
            [
                "Companion files",
                "One Source Data file exists for each figure: "
                + "; ".join(f"Source Data {FIGURE_LABELS[key]}" for key in FIGURE_ORDER),
            ],
        ]
    )
    return pd.DataFrame(rows, columns=["Field", "Value"])


def _combined_readme(
    documents: dict[str, dict[str, Any]],
    collection: TableCollection,
    panels_without_provenance: list[str],
    panels_without_source_tables: list[str],
    blocked_external: list[str],
    blocked_asset: list[str],
) -> pd.DataFrame:
    rows: list[list[Any]] = [
        ["Release status", "PARTIAL — not suitable as the final submission workbook"],
        ["Reference manuscript", "2026-07-21 merged coauthor version"],
        ["Figure revision", "2026-08-12; seven main figures"],
        ["Included panel records", len(documents)],
        ["Included source/statistics tables", len(collection.tables)],
        ["Panels without central provenance", "; ".join(panels_without_provenance)],
        ["Panels without source-data tables", "; ".join(panels_without_source_tables)],
        ["Externally blocked panels", "; ".join(blocked_external)],
        ["Asset-blocked panels", "; ".join(blocked_asset)],
        [
            "Rule",
            "A table is included only when its checksum matches audited panel provenance.",
        ],
        [
            "Submission files",
            "The per-figure Source Data files carry the same tables. "
            "This workbook is the internal combined copy.",
        ],
        ["Units", UNIT_LEGEND],
        ["Duplicate tables dropped", len(collection.superseded)],
        [
            "Duplicate rule",
            "A pre-renumbering copy under data/source_data/ is dropped only "
            "when the current copy under build/source_data/ holds every one "
            "of its rows and columns.",
        ],
        [
            "Sheet names",
            "A sheet name carries the current panel ID and the role of the "
            "table. INDEX gives the full name and the source path.",
        ],
    ]
    rows.extend(_deposit_readme_rows(collection.deposited, documents))
    return pd.DataFrame(rows, columns=["Field", "Value"])


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------


def _write_workbook(
    destination: Path, title: str, sheets: list[tuple[str, pd.DataFrame]]
) -> None:
    with pd.ExcelWriter(destination, engine="xlsxwriter") as writer:
        writer.book.set_properties(
            {
                "title": title,
                "author": "Marc Erhardt",
                "created": FIXED_TIMESTAMP,
                "modified": FIXED_TIMESTAMP,
                "comments": "Generated from checksum-validated panel provenance.",
            }
        )
        for name, frame in sheets:
            frame.to_excel(writer, sheet_name=name, index=False)
        for worksheet in writer.sheets.values():
            worksheet.freeze_panes(1, 0)
            worksheet.autofilter(
                0,
                0,
                max(0, worksheet.dim_rowmax),
                max(0, worksheet.dim_colmax),
            )


def _write_zip(destination: Path, members: list[tuple[str, str]]) -> None:
    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for name, text in members:
            info = zipfile.ZipInfo(name, date_time=FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o644 << 16
            archive.writestr(info, text.encode("utf-8"))


def _publish(staged: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    destination_staging = output.with_name(f".{output.name}.staging")
    shutil.copyfile(staged, destination_staging)
    destination_staging.replace(output)


def _readme_text(readme: pd.DataFrame) -> str:
    lines = [f"{row.Field}: {row.Value}" for row in readme.itertuples()]
    return "\n".join(lines) + "\n"


def _tsv_text(frame: pd.DataFrame) -> str:
    return frame.to_csv(sep="\t", index=False, lineterminator="\n")


# ---------------------------------------------------------------------------
# Build entry points
# ---------------------------------------------------------------------------


def build_source_workbook(root: Path, output: Path) -> dict[str, Any]:
    """Build the combined workbook that holds every checksum-validated table."""
    root = root.resolve(strict=True)
    output = output if output.is_absolute() else root / output
    documents = provenance_documents(root)
    collection = collect_tables(root, documents)

    panels_without_provenance = sorted(EXPECTED_PANEL_IDS - set(documents))
    panels_with_tables = {
        panel_id
        for table in collection.tables
        for panel_id in table.panel_id.split("-")
        if panel_id in EXPECTED_PANEL_IDS
    }
    panels_without_source_tables = sorted(EXPECTED_PANEL_IDS - panels_with_tables)
    blocked_external = sorted(
        panel_id
        for panel_id, document in documents.items()
        if document["status"] == "blocked_external"
    )
    blocked_asset = sorted(
        panel_id
        for panel_id, document in documents.items()
        if document["status"] == "blocked_asset"
    )
    readme = _combined_readme(
        documents,
        collection,
        panels_without_provenance,
        panels_without_source_tables,
        blocked_external,
        blocked_asset,
    )

    sheets: list[tuple[str, pd.DataFrame]] = [("README", readme)]
    sheets.extend((table.sheet, table.frame) for table in collection.tables)
    sheets.append(("INDEX", _index_frame(collection.tables)))
    sheets.append(("DATA_DICTIONARY", _dictionary_frame(collection.tables)))

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="flagella-source-workbook-") as temporary:
        staged_workbook = Path(temporary) / output.name
        _write_workbook(
            staged_workbook,
            "Flagella manuscript Source Data — partial build",
            sheets,
        )
        _publish(staged_workbook, output)

    return {
        "output": output.relative_to(root).as_posix(),
        "bytes": output.stat().st_size,
        "sha256": sha256_file(output),
        "panel_records": len(documents),
        "tables": len(collection.tables),
        "missing_panels": panels_without_source_tables,
        "panels_without_provenance": panels_without_provenance,
        "blocked_external": blocked_external,
        "blocked_asset": blocked_asset,
        "superseded_duplicates": collection.superseded,
        "deposited_tables": collection.deposited,
        "status": "partial",
    }


def build_deposit(
    root: Path,
    output_dir: Path,
    collection: TableCollection,
    documents: dict[str, dict[str, Any]],
    paths: dict[str, str],
) -> dict[str, Any]:
    """Copy the deposited tables and their record into one bundle directory.

    The files are copied byte for byte, so their checksums still match the
    audited panel provenance. This bundle is what goes to the DOI-bearing
    repository.
    """
    root = root.resolve(strict=True)
    output_dir = output_dir if output_dir.is_absolute() else root / output_dir
    bundle = output_dir / DEPOSIT_NAME
    bundle.mkdir(parents=True, exist_ok=True)

    manifest_rows: list[dict[str, Any]] = []
    for entry in collection.deposited:
        source = root / entry["source_path"]
        _publish(source, bundle / source.name)
        document = documents.get(entry["panel_id"], {})
        seeds = document.get("random_seeds", {})
        manifest_rows.append(
            {
                "panel_id": entry["panel_id"],
                "file": source.name,
                "rows": entry["rows"],
                "columns": entry["columns"],
                "bytes": entry["bytes"],
                "sha256": entry["sha256"],
                "panel_seed": seeds.get("panel_seed"),
                "starting_position_seed": seeds.get("starting_position_seed"),
                "obstacle_seed": seeds.get("obstacle_seed"),
                "regeneration_command": " ".join(document.get("command", [])),
                "provenance_record": paths.get(entry["panel_id"], ""),
            }
        )
    manifest = pd.DataFrame(manifest_rows)
    (bundle / "MANIFEST.tsv").write_text(_tsv_text(manifest), encoding="utf-8")

    software = documents.get(collection.deposited[0]["panel_id"], {}).get("software", {})
    readme = pd.DataFrame(
        [
            ["Bundle", f"Source Data deposit — {FIGURE_LABELS[DEPOSIT_FIGURE]}"],
            [
                "Contents",
                f"{len(collection.deposited)} simulated-trajectory tables, "
                f"{sum(row['rows'] for row in manifest_rows):,} rows in total, "
                "gzip-compressed CSV.",
            ],
            [
                "Why this is separate",
                "These tables are raw model output, not measurement. They are "
                "exactly regenerable from the seeds and parameters recorded "
                "here, and they are too large to submit as Source Data.",
            ],
            [
                "Where it belongs",
                f"The DOI-bearing repository deposit, {DEPOSIT_DOI_PLACEHOLDER}.",
            ],
            [
                "Source Data pointer",
                f"Source Data {FIGURE_LABELS[DEPOSIT_FIGURE]} carries the "
                f"obstacle fields, {DEPOSIT_FIGURE}_condition_summary and "
                f"{DEPOSIT_FIGURE}_cell_summary. The last two are derived from "
                "these tables.",
            ],
            [
                "How to regenerate",
                "MANIFEST.tsv gives the command, the seeds and the provenance "
                "record of every table. The command reproduces the file with "
                "the sha256 listed there.",
            ],
            [
                "Software",
                "; ".join(f"{key}={value}" for key, value in sorted(software.items())),
            ],
            ["Checksums", "MANIFEST.tsv lists the sha256 of every table."],
        ],
        columns=["Field", "Value"],
    )
    (bundle / "README.txt").write_text(_readme_text(readme), encoding="utf-8")

    files = sorted(path for path in bundle.iterdir() if path.is_file())
    return {
        "bundle": bundle.relative_to(root).as_posix(),
        "files": [
            {
                "file": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in files
        ],
        "file_count": len(files),
        "tables": len(collection.deposited),
        "bytes": sum(path.stat().st_size for path in files),
        "doi": DEPOSIT_DOI_PLACEHOLDER,
    }


def build_source_data_files(
    root: Path,
    output_dir: Path,
    max_bytes: int = MAX_SOURCE_DATA_FILE_BYTES,
    deposit_dir: Path | None = None,
) -> dict[str, Any]:
    """Build one Source Data file per figure under ``output_dir``.

    Every file passes the same checksum gate as the combined workbook. A figure
    ships as XLSX when the workbook stays within ``max_bytes``. Otherwise the
    figure ships as a ZIP archive of tab-separated ``.txt`` files, the plain-text
    alternative that Nature Communications permits.

    When ``deposit_dir`` is given, the deposited tables are written there as a
    bundle for the DOI-bearing repository.
    """
    root = root.resolve(strict=True)
    output_dir = output_dir if output_dir.is_absolute() else root / output_dir
    documents = provenance_documents(root)
    paths = provenance_paths(root)
    collection = collect_tables(root, documents)

    grouped: dict[str, list[SourceTable]] = {figure: [] for figure in FIGURE_ORDER}
    for table in collection.tables:
        figure = figure_of(table.panel_id)
        if figure not in grouped:
            raise ValueError(f"Panel {table.panel_id} belongs to no known figure")
        grouped[figure].append(table)

    output_dir.mkdir(parents=True, exist_ok=True)
    files: list[dict[str, Any]] = []
    for figure in FIGURE_ORDER:
        figure_tables = grouped[figure]
        stem = "Source_Data_" + FIGURE_LABELS[figure].replace(" ", "_")
        index_frame = _index_frame(figure_tables)
        dictionary_frame = _dictionary_frame(figure_tables)
        deposited = collection.deposited if figure == DEPOSIT_FIGURE else []

        with tempfile.TemporaryDirectory(prefix="flagella-source-data-") as temporary:
            staged_workbook = Path(temporary) / f"{stem}.xlsx"
            _write_workbook(
                staged_workbook,
                f"Source Data {FIGURE_LABELS[figure]}",
                [
                    (
                        "README",
                        _figure_readme(
                            figure,
                            f"{stem}.xlsx",
                            "xlsx",
                            figure_tables,
                            documents,
                            paths,
                            deposited,
                        ),
                    )
                ]
                + [(table.sheet, table.frame) for table in figure_tables]
                + [("INDEX", index_frame), ("DATA_DICTIONARY", dictionary_frame)],
            )
            workbook_bytes = staged_workbook.stat().st_size
            if workbook_bytes <= max_bytes:
                file_format = "xlsx"
                output = output_dir / f"{stem}.xlsx"
                _publish(staged_workbook, output)
                stale = output_dir / f"{stem}.zip"
            else:
                file_format = "zip"
                output = output_dir / f"{stem}.zip"
                readme = _figure_readme(
                    figure,
                    f"{stem}.zip",
                    "zip",
                    figure_tables,
                    documents,
                    paths,
                    deposited,
                )
                # Every member sits in one folder, so unzipping stays tidy.
                members: list[tuple[str, str]] = [
                    (f"{stem}/README.txt", _readme_text(readme)),
                    (f"{stem}/INDEX.txt", _tsv_text(index_frame)),
                    (f"{stem}/DATA_DICTIONARY.txt", _tsv_text(dictionary_frame)),
                ]
                members.extend(
                    (f"{stem}/{table.sheet}.txt", _tsv_text(table.frame))
                    for table in figure_tables
                )
                staged_archive = Path(temporary) / f"{stem}.zip"
                _write_zip(staged_archive, members)
                _publish(staged_archive, output)
                stale = output_dir / f"{stem}.xlsx"
        if stale.exists():
            stale.unlink()

        files.append(
            {
                "figure": figure,
                "label": FIGURE_LABELS[figure],
                "title": f"Source Data {FIGURE_LABELS[figure]}",
                "file": output.relative_to(root).as_posix(),
                "format": file_format,
                "bytes": output.stat().st_size,
                "workbook_bytes": workbook_bytes,
                "sha256": sha256_file(output),
                "tables": len(figure_tables),
                "panels": sorted({table.panel_id for table in figure_tables}),
                "sheets": [table.sheet for table in figure_tables],
                "source_paths": [table.source_path for table in figure_tables],
            }
        )

    result: dict[str, Any] = {
        "output_dir": output_dir.relative_to(root).as_posix(),
        "max_file_bytes": max_bytes,
        "files": files,
        "file_count": len(files),
        "tables": len(collection.tables),
        "largest_file_bytes": max(entry["bytes"] for entry in files),
        "total_bytes": sum(entry["bytes"] for entry in files),
        "formats": sorted({entry["format"] for entry in files}),
        "superseded_duplicates": collection.superseded,
        "status": "partial",
    }
    if deposit_dir is not None and collection.deposited:
        result["deposit"] = build_deposit(
            root, deposit_dir, collection, documents, paths
        )
    return result
