"""Checksum-backed extraction of current single-cell panel source data."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
from typing import Any

import pandas as pd

CHUNK_SIZE = 50_000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact(path: Path, root: Path, rows: int | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {
        "relative_path": path.relative_to(root).as_posix(),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }
    if rows is not None:
        item["rows"] = rows
    return item


def write_deterministic_gzip(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            with io.TextIOWrapper(zipped, encoding="utf-8", newline="") as text:
                frame.to_csv(text, index=False, lineterminator="\n", float_format="%.12g")


def load_current_rows(source: Path, config: dict[str, Any]) -> pd.DataFrame:
    selected: list[pd.DataFrame] = []
    usecols = config["columns"]
    filters = config["filters"]
    for chunk in pd.read_csv(source, usecols=usecols, chunksize=CHUNK_SIZE):
        mask = pd.Series(True, index=chunk.index)
        for column, accepted in filters.items():
            mask &= chunk[column].isin(accepted)
        if mask.any():
            selected.append(chunk.loc[mask, usecols])
    if not selected:
        raise RuntimeError(f"Extraction returned no rows from {source}")
    frame = pd.concat(selected, ignore_index=True)
    order = [column for column in config["sort_by"] if column in frame]
    return frame.sort_values(order, kind="mergesort").reset_index(drop=True)


def make_replicate_means(frame: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    value = config["value_column"]
    groups = config["replicate_groups"]
    means = (
        frame.groupby(groups, sort=True, dropna=False)[value]
        .agg([("mean", "mean"), ("n_cells", "size")])
        .reset_index()
    )
    return means.rename(columns={"mean": f"mean_{value}"})


def write_outputs(config_path: Path) -> None:
    collection = Path(__file__).resolve().parents[4]
    outer_root = collection.parent
    config = json.loads(config_path.read_text())
    source = outer_root / config["legacy_source"]
    if not source.is_file():
        raise FileNotFoundError(source)

    frame = load_current_rows(source, config)
    expected = int(config["expected_rows"])
    if len(frame) != expected:
        raise RuntimeError(f"Expected {expected} rows; extracted {len(frame)}")
    means = make_replicate_means(frame, config)

    parquet = collection / config["processed_parquet"]
    means_csv = collection / config["replicate_means_csv"]
    source_csv = collection / config["source_data_csv_gz"]
    inventory = collection / config["migration_inventory"]
    for path in (parquet, means_csv, source_csv, inventory):
        path.parent.mkdir(parents=True, exist_ok=True)

    frame.to_parquet(parquet, index=False, compression="zstd")
    means.to_csv(means_csv, index=False, lineterminator="\n", float_format="%.12g")
    write_deterministic_gzip(frame, source_csv)

    source_rows = sum(1 for _ in source.open("rb")) - 1
    document = {
        "schema_version": "1.0.0",
        "panel_id": config["panel_id"],
        "migration_scope": "legacy processed single-cell table to current-panel subset",
        "legacy_input": {
            "relative_to_workspace": config["legacy_source"],
            "sha256": sha256(source),
            "bytes": source.stat().st_size,
            "rows": source_rows,
        },
        "selection": {
            "filters": config["filters"],
            "columns": config["columns"],
            "sort_by": config["sort_by"],
            "expected_rows": expected,
            "chunk_size": CHUNK_SIZE,
        },
        "outputs": [
            artifact(parquet, collection, len(frame)),
            artifact(means_csv, collection, len(means)),
            artifact(source_csv, collection, len(frame)),
        ],
        "raw_tracking_lineage": {
            "status": "absent",
            "detail": (
                "The archived bundle contains a processed per-cell table, but no original "
                "mother-machine tracking files or raw image-to-cell extraction workflow."
            ),
        },
        "large_file_policy": (
            "The legacy CSV remains read-only outside this collection because it exceeds "
            "100 MB. The collection stores a checksum-addressed current-panel extraction."
        ),
    }
    inventory.write_text(json.dumps(document, indent=2) + "\n")
    print(f"{config['panel_id']}: wrote {len(frame)} cells and {len(means)} replicate means")


def verify_outputs(config_path: Path) -> None:
    collection = Path(__file__).resolve().parents[4]
    outer_root = collection.parent
    config = json.loads(config_path.read_text())
    inventory = collection / config["migration_inventory"]
    document = json.loads(inventory.read_text())
    source = outer_root / config["legacy_source"]
    checks = [
        (source, document["legacy_input"]),
        *[(collection / item["relative_path"], item) for item in document["outputs"]],
    ]
    for path, expected in checks:
        if not path.is_file():
            raise FileNotFoundError(path)
        if path.stat().st_size != expected["bytes"] or sha256(path) != expected["sha256"]:
            raise RuntimeError(f"Checksum or size mismatch: {path}")
    frame = pd.read_parquet(collection / config["processed_parquet"])
    if len(frame) != config["expected_rows"]:
        raise RuntimeError("Processed Parquet row count mismatch")
    print(f"{config['panel_id']}: all migration checks passed")


def run(config_path: Path) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true", help="Create the compact extraction")
    args = parser.parse_args()
    if args.write:
        write_outputs(config_path)
    else:
        verify_outputs(config_path)


if __name__ == "__main__":
    run(Path(__file__).resolve().parents[1] / "config" / "config.json")
