from __future__ import annotations

import csv
import hashlib
from pathlib import Path

import pytest

from flagella_repro.registries import (
    ARTIFACT_FIELDS,
    BLOCKED_PANEL_IDS,
    EXPECTED_PANEL_IDS,
    PANEL_ARTIFACT_FIELDS,
    PANEL_FIELDS,
)


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


@pytest.fixture
def registry_project(tmp_path: Path) -> Path:
    root = tmp_path / "collection"
    figures = sorted({panel.split("_")[0] for panel in EXPECTED_PANEL_IDS})
    artifacts: list[dict[str, str]] = []
    for figure in figures:
        relative = f"reference/{figure}.svg"
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = f"<svg><title>{figure}</title></svg>\n".encode()
        target.write_bytes(payload)
        artifacts.append(
            {
                "artifact_id": f"ref_{figure}",
                "relative_path": relative,
                "role": "frozen_reference",
                "format": "svg",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": str(len(payload)),
                "generated_by_rule": "",
                "external_accession": "",
                "license": "internal_reference",
            }
        )

    panels: list[dict[str, str]] = []
    links: list[dict[str, str]] = []
    for panel_id in sorted(EXPECTED_PANEL_IDS):
        figure, label = panel_id.split("_")
        blocked = panel_id in BLOCKED_PANEL_IDS
        artifact_id = f"ref_{figure}"
        panels.append(
            {
                "panel_id": panel_id,
                "figure_id": figure,
                "panel_label": label,
                "title": panel_id,
                "panel_type": "model" if blocked else "quantitative",
                "status": "blocked_external" if blocked else "ready_migration",
                "canonical_rule": f"blocked_{panel_id.lower()}"
                if blocked
                else f"plot_{panel_id.lower()}",
                "final_artifact_id": artifact_id,
                "legacy_panel_ids": "",
                "notes": "",
            }
        )
        links.append({"panel_id": panel_id, "artifact_id": artifact_id, "usage": "final_output"})

    _write_csv(root / "config" / "panels.csv", PANEL_FIELDS, panels)
    _write_csv(root / "config" / "artifacts.csv", ARTIFACT_FIELDS, artifacts)
    _write_csv(root / "config" / "panel_artifacts.csv", PANEL_ARTIFACT_FIELDS, links)
    return root
