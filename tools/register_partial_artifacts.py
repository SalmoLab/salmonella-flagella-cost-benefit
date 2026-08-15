#!/usr/bin/env python3
"""Synchronize audited partial-reproduction outputs into the artifact registries."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any

from flagella_repro.registries import (
    ARTIFACT_FIELDS,
    PANEL_ARTIFACT_FIELDS,
    sha256_file,
)

MANAGED_PREFIX = "partial_"


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _usage(path: Path) -> str:
    if path.suffix.lower() in {".svg", ".pdf", ".png"}:
        return "panel_output"
    if "stat" in path.stem.lower():
        return "statistics"
    return "source_data"


def _format(path: Path) -> str:
    """Return a useful compound format for compressed tabular outputs."""
    suffixes = [suffix.lower().lstrip(".") for suffix in path.suffixes]
    if suffixes[-2:] == ["csv", "gz"]:
        return "csv.gz"
    return suffixes[-1] if suffixes else "data"


def _scientific_input_usage(relative: str) -> str | None:
    if relative.startswith(("data/raw/", "data/external/")):
        return "raw_input"
    if relative.startswith(("data/interim/", "data/processed/")):
        return "processed_input"
    if relative.startswith("data/source_data/"):
        return "source_data"
    if relative.startswith("assets/"):
        return "image_asset"
    return None


def _managed_rows(root: Path) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    panel_rows = _read(root / "config" / "panels.csv")
    panel_rules = {row["panel_id"]: row["canonical_rule"] for row in panel_rows}
    artifacts: list[dict[str, str]] = []
    links: list[dict[str, str]] = []
    # A single source-data table may legitimately drive multiple current panels.
    # Keep one artifact row per path, but retain a link for every producing panel.
    seen_paths: dict[str, tuple[str, str, int, str]] = {}
    seen_artifact_ids: dict[str, str] = {}
    documents: list[tuple[str, dict[str, Any]]] = []
    for provenance_path in sorted((root / "metadata" / "provenance").rglob("*.json")):
        document: dict[str, Any] = json.loads(provenance_path.read_text(encoding="utf-8"))
        if document.get("status") not in {"partial_reproduction", "reproduced"}:
            continue
        panel_id = str(document["panel_id"])
        documents.append((panel_id, document))
        for output in document["outputs"]:
            relative = str(output["relative_path"])
            if relative in seen_paths:
                artifact_id, expected_sha, expected_bytes, expected_usage = seen_paths[relative]
                if (
                    str(output["sha256"]) != expected_sha
                    or int(output["bytes"]) != expected_bytes
                ):
                    raise ValueError(
                        f"Conflicting provenance metadata for shared output {relative}"
                    )
                links.append(
                    {
                        "panel_id": panel_id,
                        "artifact_id": artifact_id,
                        "usage": expected_usage,
                    }
                )
                continue
            path = root / relative
            if not path.is_file():
                raise FileNotFoundError(f"Registered provenance output is missing: {relative}")
            actual_sha = sha256_file(path)
            actual_bytes = path.stat().st_size
            if actual_sha != output["sha256"] or actual_bytes != int(output["bytes"]):
                raise ValueError(f"Provenance checksum or size is stale for {relative}")
            usage = _usage(path)
            artifact_id = f"{MANAGED_PREFIX}{panel_id.lower()}_{_slug(path.name)}"
            if artifact_id in seen_artifact_ids:
                raise ValueError(
                    "Generated artifact ID collision for "
                    f"{relative} and {seen_artifact_ids[artifact_id]}: {artifact_id}"
                )
            seen_artifact_ids[artifact_id] = relative
            seen_paths[relative] = (artifact_id, actual_sha, actual_bytes, usage)
            artifacts.append(
                {
                    "artifact_id": artifact_id,
                    "relative_path": relative,
                    "role": f"partial_{usage}",
                    "format": _format(path),
                    "sha256": actual_sha,
                    "bytes": str(actual_bytes),
                    "generated_by_rule": panel_rules[panel_id],
                    "external_accession": "",
                    "license": "internal_pending_release",
                }
            )
            links.append(
                {"panel_id": panel_id, "artifact_id": artifact_id, "usage": usage}
            )

    # Scientific data/assets declared as inputs also belong in the authoritative
    # artifact and panel-link registries. Code and configuration remain checksumed
    # in provenance but are version-controlled files, not data artifacts.
    for panel_id, document in documents:
        for input_artifact in document["inputs"]:
            relative = str(input_artifact["relative_path"])
            usage = _scientific_input_usage(relative)
            if usage is None:
                continue
            if relative in seen_paths:
                artifact_id, expected_sha, expected_bytes, expected_usage = seen_paths[relative]
                if (
                    str(input_artifact["sha256"]) != expected_sha
                    or int(input_artifact["bytes"]) != expected_bytes
                ):
                    raise ValueError(
                        f"Conflicting provenance metadata for shared artifact {relative}"
                    )
                if usage != expected_usage:
                    raise ValueError(
                        f"Conflicting usage for shared artifact {relative}: "
                        f"{expected_usage} versus {usage}"
                    )
                links.append(
                    {"panel_id": panel_id, "artifact_id": artifact_id, "usage": usage}
                )
                continue
            path = root / relative
            if not path.is_file():
                raise FileNotFoundError(f"Registered provenance input is missing: {relative}")
            actual_sha = sha256_file(path)
            actual_bytes = path.stat().st_size
            if (
                actual_sha != input_artifact["sha256"]
                or actual_bytes != int(input_artifact["bytes"])
            ):
                raise ValueError(f"Provenance checksum or size is stale for {relative}")
            artifact_id = f"{MANAGED_PREFIX}{panel_id.lower()}_{_slug(path.name)}"
            if artifact_id in seen_artifact_ids:
                raise ValueError(
                    "Generated artifact ID collision for "
                    f"{relative} and {seen_artifact_ids[artifact_id]}: {artifact_id}"
                )
            seen_artifact_ids[artifact_id] = relative
            seen_paths[relative] = (artifact_id, actual_sha, actual_bytes, usage)
            artifacts.append(
                {
                    "artifact_id": artifact_id,
                    "relative_path": relative,
                    "role": f"partial_{usage}",
                    "format": _format(path),
                    "sha256": actual_sha,
                    "bytes": str(actual_bytes),
                    "generated_by_rule": "",
                    "external_accession": "",
                    "license": "internal_pending_release",
                }
            )
            links.append(
                {"panel_id": panel_id, "artifact_id": artifact_id, "usage": usage}
            )

    links = list(
        {
            (row["panel_id"], row["artifact_id"], row["usage"]): row for row in links
        }.values()
    )
    artifacts.sort(key=lambda row: row["artifact_id"])
    links.sort(key=lambda row: (row["panel_id"], row["usage"], row["artifact_id"]))
    return artifacts, links


def _write(path: Path, fields: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def synchronize(root: Path, *, write: bool) -> tuple[int, int]:
    artifacts_path = root / "config" / "artifacts.csv"
    links_path = root / "config" / "panel_artifacts.csv"
    expected_artifacts, expected_links = _managed_rows(root)
    base_artifacts = [
        row for row in _read(artifacts_path) if not row["artifact_id"].startswith(MANAGED_PREFIX)
    ]
    base_links = [
        row for row in _read(links_path) if not row["artifact_id"].startswith(MANAGED_PREFIX)
    ]
    combined_artifacts = base_artifacts + expected_artifacts
    combined_links = base_links + expected_links
    if write:
        _write(artifacts_path, ARTIFACT_FIELDS, combined_artifacts)
        _write(links_path, PANEL_ARTIFACT_FIELDS, combined_links)
    else:
        if _read(artifacts_path) != combined_artifacts or _read(links_path) != combined_links:
            raise ValueError("Partial artifact registries are stale; review and rerun with --write")
    return len(expected_artifacts), len(expected_links)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    counts = synchronize(args.root.resolve(), write=args.write)
    verb = "registered" if args.write else "verified"
    print(f"{verb} {counts[0]} partial artifacts and {counts[1]} panel links")


if __name__ == "__main__":
    main()
