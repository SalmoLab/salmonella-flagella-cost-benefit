from __future__ import annotations

import csv
import gzip
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .registries import EXPECTED_PANEL_IDS, sha256_file, validate_relative_path

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_KEYS = {
    "schema_version",
    "panel_id",
    "status",
    "generated_at_utc",
    "command",
    "inputs",
    "outputs",
    "software",
    "parameters",
    "random_seeds",
}


@dataclass(frozen=True)
class ProvenanceError:
    path: str
    message: str


def _validate_artifact_entries(entries: Any, key: str, errors: list[ProvenanceError]) -> None:
    if not isinstance(entries, list):
        errors.append(ProvenanceError(key, "must be an array"))
        return
    for index, entry in enumerate(entries):
        location = f"{key}[{index}]"
        if not isinstance(entry, Mapping):
            errors.append(ProvenanceError(location, "must be an object"))
            continue
        relative = entry.get("relative_path")
        if not isinstance(relative, str) or not relative:
            errors.append(ProvenanceError(f"{location}.relative_path", "is required"))
        else:
            path_error = validate_relative_path(relative)
            if path_error:
                errors.append(ProvenanceError(f"{location}.relative_path", path_error))
        sha = entry.get("sha256")
        if not isinstance(sha, str) or not _SHA256_RE.fullmatch(sha):
            errors.append(ProvenanceError(f"{location}.sha256", "must be a lowercase SHA-256"))
        size = entry.get("bytes")
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            errors.append(ProvenanceError(f"{location}.bytes", "must be a non-negative integer"))
        if "rows" in entry and (
            not isinstance(entry["rows"], int)
            or isinstance(entry["rows"], bool)
            or entry["rows"] < 0
        ):
            errors.append(ProvenanceError(f"{location}.rows", "must be a non-negative integer"))


def validate_provenance(document: Mapping[str, Any]) -> list[ProvenanceError]:
    errors: list[ProvenanceError] = []
    missing = sorted(REQUIRED_KEYS - set(document))
    for key in missing:
        errors.append(ProvenanceError(key, "required key is missing"))
    if missing:
        return errors
    if document["schema_version"] != "1.0.0":
        errors.append(ProvenanceError("schema_version", "must equal '1.0.0'"))
    if document["panel_id"] not in EXPECTED_PANEL_IDS:
        errors.append(ProvenanceError("panel_id", "must identify one of the 63 current panels"))
    status = document["status"]
    if status not in {
        "reproduced",
        "partial_reproduction",
        "blocked_external",
        "blocked_asset",
        "failed",
    }:
        errors.append(ProvenanceError("status", "unsupported provenance status"))
    try:
        timestamp = str(document["generated_at_utc"])
        if not timestamp.endswith("Z"):
            raise ValueError
        datetime.fromisoformat(timestamp[:-1] + "+00:00")
    except ValueError:
        errors.append(
            ProvenanceError("generated_at_utc", "must be an ISO-8601 UTC timestamp ending in Z")
        )
    if not isinstance(document["command"], list) or not all(
        isinstance(item, str) and item for item in document["command"]
    ):
        errors.append(ProvenanceError("command", "must be a non-empty argv array"))
    _validate_artifact_entries(document["inputs"], "inputs", errors)
    _validate_artifact_entries(document["outputs"], "outputs", errors)
    for key in ("software", "parameters", "random_seeds"):
        if not isinstance(document[key], Mapping):
            errors.append(ProvenanceError(key, "must be an object"))
    if status in {"reproduced", "partial_reproduction"} and not document["outputs"]:
        errors.append(
            ProvenanceError("outputs", f"{status} panels require at least one output")
        )
    if status == "partial_reproduction":
        limitations = document.get("limitations")
        if not isinstance(limitations, list) or not limitations or not all(
            isinstance(item, str) and item for item in limitations
        ):
            errors.append(
                ProvenanceError(
                    "limitations", "partial_reproduction requires a non-empty string array"
                )
            )
    if status in {"blocked_external", "blocked_asset"}:
        blocker = document.get("blocker")
        if not isinstance(blocker, Mapping):
            errors.append(ProvenanceError("blocker", f"{status} requires a blocker object"))
        elif not blocker.get("reason") or not isinstance(blocker.get("required_assets"), list):
            errors.append(ProvenanceError("blocker", "requires reason and required_assets"))
    return errors


def _tabular_row_count(path: Path) -> int:
    name = path.name.lower()
    if name.endswith(".csv.gz"):
        with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
            return max(0, sum(1 for _ in csv.reader(handle)) - 1)
    if name.endswith(".csv"):
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return max(0, sum(1 for _ in csv.reader(handle)) - 1)
    if name.endswith(".parquet"):
        import pyarrow.parquet as parquet

        return parquet.ParquetFile(path).metadata.num_rows
    raise ValueError("rows can only be verified for CSV, CSV.GZ, or Parquet files")


def validate_provenance_files(
    root: Path, document: Mapping[str, Any]
) -> list[ProvenanceError]:
    """Verify every declared input/output checksum, size, and optional row count."""
    errors: list[ProvenanceError] = []
    root = root.resolve()
    for key in ("inputs", "outputs"):
        entries = document.get(key)
        if not isinstance(entries, list):
            continue
        for index, entry in enumerate(entries):
            if not isinstance(entry, Mapping):
                continue
            location = f"{key}[{index}]"
            relative = entry.get("relative_path")
            if not isinstance(relative, str) or validate_relative_path(relative):
                continue
            path = root / relative
            if not path.is_file():
                errors.append(ProvenanceError(f"{location}.relative_path", "file is missing"))
                continue
            try:
                resolved = path.resolve()
                resolved.relative_to(root)
            except (OSError, ValueError):
                errors.append(
                    ProvenanceError(
                        f"{location}.relative_path", "resolved file is outside the collection"
                    )
                )
                continue
            expected_bytes = entry.get("bytes")
            if isinstance(expected_bytes, int) and path.stat().st_size != expected_bytes:
                errors.append(
                    ProvenanceError(
                        f"{location}.bytes",
                        f"recorded {expected_bytes}, found {path.stat().st_size}",
                    )
                )
            expected_sha = entry.get("sha256")
            if isinstance(expected_sha, str) and _SHA256_RE.fullmatch(expected_sha):
                actual_sha = sha256_file(path)
                if actual_sha != expected_sha:
                    errors.append(
                        ProvenanceError(
                            f"{location}.sha256",
                            f"checksum mismatch for {relative}",
                        )
                    )
            if "rows" in entry and isinstance(entry.get("rows"), int):
                try:
                    actual_rows = _tabular_row_count(path)
                except (OSError, ValueError) as exc:
                    errors.append(ProvenanceError(f"{location}.rows", str(exc)))
                else:
                    if actual_rows != entry["rows"]:
                        errors.append(
                            ProvenanceError(
                                f"{location}.rows",
                                f"recorded {entry['rows']}, found {actual_rows}",
                            )
                        )
    return errors


def validate_provenance_tree(
    root: Path, *, verify_files: bool = True
) -> list[tuple[Path, list[ProvenanceError]]]:
    base = root / "metadata" / "provenance"
    results: list[tuple[Path, list[ProvenanceError]]] = []
    if not base.exists():
        return results
    for path in sorted(base.rglob("*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            results.append((path, [ProvenanceError("$", f"invalid JSON: {exc}")]))
            continue
        if not isinstance(document, Mapping):
            results.append((path, [ProvenanceError("$", "document must be an object")]))
            continue
        errors = validate_provenance(document)
        if verify_files and not errors:
            errors.extend(validate_provenance_files(root, document))
        results.append((path, errors))
    return results
