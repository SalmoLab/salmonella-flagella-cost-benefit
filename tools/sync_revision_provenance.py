#!/usr/bin/env python3
"""Synchronize current canonical analysis provenance into the central audit tree."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from flagella_repro.provenance import validate_provenance
from flagella_repro.registries import EXPECTED_PANEL_IDS

ROOT = Path(__file__).resolve().parents[1]


def excluded_prefixes() -> set[str]:
    path = ROOT / "config" / "pre_revision_analysis_exclusions.txt"
    return {
        line.strip().rstrip("/")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def figure_folder(panel_id: str) -> str:
    prefix = panel_id.split("_", 1)[0]
    if prefix.startswith("F"):
        return f"figure_{int(prefix[1:]):02d}"
    return f"supplementary_{int(prefix[1:]):02d}"


def main() -> None:
    excluded = excluded_prefixes()
    documents: dict[str, tuple[Path, dict[str, object]]] = {}
    for path in sorted((ROOT / "analyses").glob("**/metadata/provenance.json")):
        relative = path.relative_to(ROOT).as_posix()
        if any(relative == prefix or relative.startswith(prefix + "/") for prefix in excluded):
            continue
        document = json.loads(path.read_text(encoding="utf-8"))
        panel_id = str(document.get("panel_id", ""))
        if panel_id not in EXPECTED_PANEL_IDS:
            continue
        errors = validate_provenance(document)
        if errors:
            rendered = "; ".join(f"{error.path}: {error.message}" for error in errors)
            raise ValueError(f"invalid provenance {relative}: {rendered}")
        if panel_id in documents:
            raise ValueError(
                f"duplicate canonical provenance for {panel_id}: "
                f"{documents[panel_id][0].relative_to(ROOT)} and {relative}"
            )
        documents[panel_id] = (path, document)

    missing = sorted(EXPECTED_PANEL_IDS - set(documents))
    if missing:
        raise ValueError("missing current canonical provenance: " + ", ".join(missing))

    central = ROOT / "metadata" / "provenance"
    for number in range(1, 8):
        target = central / f"figure_{number:02d}"
        if target.exists():
            shutil.rmtree(target)
    for panel_id, (source, _) in sorted(documents.items()):
        target = central / figure_folder(panel_id) / f"{panel_id}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    print(f"synchronized {len(documents)} current provenance documents")


if __name__ == "__main__":
    main()
