#!/usr/bin/env python3
"""Create the canonical generated-output tree and truthful status manifests."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

import yaml

FIGURE_FOLDERS = {
    "Figure1": "Figure_1",
    "Figure2": "Figure_2",
    "Figure3": "Figure_3",
    "Figure4": "Figure_4",
    "Figure5": "Figure_5",
    "Figure6": "Figure_6",
    "Figure7": "Figure_7",
    "Supplementary1": "Supplementary_Figure_1",
    "Supplementary2": "Supplementary_Figure_2",
    "Supplementary3": "Supplementary_Figure_3",
    "Supplementary4": "Supplementary_Figure_4",
    "Supplementary5": "Supplementary_Figure_5",
}

# The analysis directories were renamed on 15 August 2026 to match the figures
# they build, so this map is now one to one. It stays because a status manifest
# must name the directory that produced the panel, and that link should be
# declared rather than inferred from the figure ID.
ANALYSIS_DIRS = {
    "Supplementary1": "supplementary_01",
    "Supplementary2": "supplementary_02",
    "Supplementary3": "supplementary_03",
    "Supplementary4": "supplementary_04",
    "Supplementary5": "supplementary_05",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_provenance(root: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    records: dict[str, tuple[Path, dict[str, Any]]] = {}
    for path in sorted((root / "metadata" / "provenance").rglob("*.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        panel_id = document.get("panel_id")
        if panel_id:
            records[str(panel_id)] = (path, document)
    return records


def analysis_path(root: Path, figure_id: str, label: str) -> Path:
    if figure_id.startswith("Figure"):
        number = int(figure_id.removeprefix("Figure"))
        revision = root / "analyses" / f"figure_{number:02d}_revision"
        base = revision if revision.is_dir() else root / "analyses" / f"figure_{number:02d}"
    else:
        base = root / "analyses" / ANALYSIS_DIRS[figure_id]
    lower = base / f"panel_{label.lower()}"
    upper = base / f"panel_{label.upper()}"
    return lower if lower.is_dir() else upper


def reference_record(
    manifest_rows: list[dict[str, str]], figure_id: str, reference_source_id: str
) -> dict[str, str]:
    figure_id = reference_source_id
    filename = (
        f"Figure_{figure_id.removeprefix('Figure')}.svg"
        if figure_id.startswith("Figure")
        else f"Supplemental-figure_{figure_id.removeprefix('Supplementary')}.svg"
    )
    relative = f"reference/2026-07-09/figures/{filename}"
    row = next(item for item in manifest_rows if item["relative_path"] == relative)
    return {"relative_path": relative, "sha256": row["sha256"]}


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def organize(root: Path) -> dict[str, int]:
    with (root / "config" / "panels.csv").open(newline="", encoding="utf-8") as handle:
        panels = list(csv.DictReader(handle))
    figures = yaml.safe_load((root / "config" / "figures.yaml").read_text(encoding="utf-8"))
    with (root / "reference_manifest.csv").open(newline="", encoding="utf-8") as handle:
        reference_rows = list(csv.DictReader(handle))
    provenance = load_provenance(root)
    reference_sources = {
        row["id"]: row.get("reference_source_id", row["id"]) for row in figures["figures"]
    }

    panel_statuses: dict[str, str] = {}
    for row in panels:
        panel_id = row["panel_id"]
        if panel_id not in provenance:
            raise ValueError(f"No central provenance record for {panel_id}")
        provenance_path, document = provenance[panel_id]
        status = str(document["status"])
        panel_statuses[panel_id] = status
        outputs = []
        for artifact in document.get("outputs", []):
            path = root / artifact["relative_path"]
            if path.is_file():
                outputs.append(
                    {
                        "relative_path": artifact["relative_path"],
                        "sha256": sha256_file(path),
                        "bytes": path.stat().st_size,
                    }
                )
        ref = reference_record(
            reference_rows, row["figure_id"], reference_sources[row["figure_id"]]
        )
        folder = FIGURE_FOLDERS[row["figure_id"]]
        panel_dir = root / "build" / "panels" / folder / row["panel_label"]
        panel_dir.mkdir(parents=True, exist_ok=True)
        declared_graphics = {
            (root / output["relative_path"]).name
            for output in outputs
            if (root / output["relative_path"]).suffix.lower()
            in {".svg", ".pdf", ".png", ".tif", ".tiff"}
        }
        for existing in panel_dir.iterdir():
            if (
                existing.is_file()
                and existing.suffix.lower() in {".svg", ".pdf", ".png", ".tif", ".tiff"}
                and existing.name not in declared_graphics
            ):
                existing.unlink()
        organized_outputs = []
        for output in outputs:
            source = root / output["relative_path"]
            if source.suffix.lower() in {".svg", ".pdf", ".png", ".tif", ".tiff"}:
                target = panel_dir / source.name
                if source.resolve() != target.resolve():
                    shutil.copy2(source, target)
                organized_outputs.append(
                    {
                        "relative_path": target.relative_to(root).as_posix(),
                        "sha256": sha256_file(target),
                        "bytes": target.stat().st_size,
                    }
                )
        shutil.copy2(provenance_path, panel_dir / "provenance.json")
        provenance_out = root / "build" / "provenance" / folder / f"{row['panel_label']}.json"
        provenance_out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(provenance_path, provenance_out)
        write_json(
            panel_dir / "artifacts.json",
            {
                "panel_id": panel_id,
                "declared_outputs": outputs,
                "organized_graphics": organized_outputs,
            },
        )
        status_document: dict[str, Any] = {
            "schema_version": "1.0.0",
            "panel_id": panel_id,
            "figure_id": row["figure_id"],
            "panel_label": row["panel_label"],
            "title": row["title"],
            "status": status,
            "analysis_directory": analysis_path(root, row["figure_id"], row["panel_label"])
            .relative_to(root)
            .as_posix(),
            "provenance": provenance_path.relative_to(root).as_posix(),
            "reference_target": ref,
            "outputs": outputs,
            "invented_outputs": False,
        }
        if "blocker" in document:
            status_document["blocker"] = document["blocker"]
        write_json(panel_dir / "status.json", status_document)

    for figure in figures["figures"]:
        figure_id = figure["id"]
        folder = FIGURE_FOLDERS[figure_id]
        statuses = {panel_id: panel_statuses[panel_id] for panel_id in figure["panels"]}
        if any(value in {"partial_reproduction", "reproduced"} for value in statuses.values()):
            figure_status = "partial_reproduction"
        elif all(value == "blocked_external" for value in statuses.values()):
            figure_status = "blocked_external"
        else:
            figure_status = "blocked_asset"
        figure_dir = root / "build" / "figures" / folder
        manifests = []
        for path in sorted(figure_dir.glob("*.manifest.json")):
            manifests.append(
                {
                    "relative_path": path.relative_to(root).as_posix(),
                    "sha256": sha256_file(path),
                }
            )
        write_json(
            figure_dir / "status.json",
            {
                "schema_version": "1.0.0",
                "figure_id": figure_id,
                "output_directory": figure_dir.relative_to(root).as_posix(),
                "status": figure_status,
                "panels": statuses,
                "reference_target": reference_record(
                    reference_rows, figure_id, reference_sources[figure_id]
                ),
                "assembly_manifests": manifests,
                "complete_final_figure_available": False,
                "invented_outputs": False,
            },
        )

    report_source = root / "docs" / "revision_2026-08-12"
    report_target = root / "build" / "reports" / "revision_2026-08-12"
    if report_source.is_dir():
        report_target.mkdir(parents=True, exist_ok=True)
        for source in sorted(report_source.iterdir()):
            if source.is_file():
                shutil.copy2(source, report_target / source.name)

    return {"panels": len(panels), "figures": len(figures["figures"])}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    counts = organize(args.root.resolve())
    print(
        f"organized {counts['panels']} panel directories and {counts['figures']} figure directories"
    )


if __name__ == "__main__":
    main()
