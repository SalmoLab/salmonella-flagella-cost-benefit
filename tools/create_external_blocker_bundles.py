#!/usr/bin/env python3
"""Create deterministic PANEL_CONTRACT bundles for externally blocked panels."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import yaml


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _panel_dir(root: Path, panel_id: str) -> Path:
    figure, label = panel_id.split("_")
    if figure.startswith("F"):
        return root / "analyses" / f"figure_{int(figure[1:]):02d}" / f"panel_{label.lower()}"
    return (
        root
        / "analyses"
        / f"supplementary_{int(figure[1:]):02d}"
        / f"panel_{label.lower()}"
    )


def _expected_documents(root: Path) -> dict[Path, str]:
    panels = {row["panel_id"]: row for row in _read_csv(root / "config" / "panels.csv")}
    artifacts = {
        row["artifact_id"]: row for row in _read_csv(root / "config" / "artifacts.csv")
    }
    sources = _read_csv(root / "config" / "external_sources.csv")
    panel_to_source: dict[str, dict[str, str]] = {}
    for source in sources:
        for panel_id in source["panel_ids"].split(";"):
            panel_to_source[panel_id] = source

    documents: dict[Path, str] = {}
    for panel_id, panel in sorted(panels.items()):
        if panel["status"] != "blocked_external":
            continue
        source = panel_to_source[panel_id]
        bundle = _panel_dir(root, panel_id)
        reference = artifacts[panel["final_artifact_id"]]
        required_assets = [item.strip() for item in source["required_material"].split(";")]
        readme = f"""# {panel_id} — {panel['title']}

Status: `blocked_external`.

This panel cannot be reconstructed from the local legacy material. It requires
the registered external package `{source['source_id']}`. No preliminary local
notebook, copied plotted value or inferred parameter may substitute for that
package.

Required material: {source['required_material']}.

Validation gate: {source['validation_gate']}.

When received, freeze the untouched delivery with
`tools/intake_external_package.py`, verify its checksum, and migrate the accepted
logic into deterministic Python scripts in this bundle.
`docs/SCIENTIFIC_SOURCE_INTAKE_2026-08-12.md` records what each delivery
contained, what was accepted and what is still absent. The registered
requirement for this panel is the row `{source['source_id']}` of
`config/external_sources.csv`.
"""
        documents[bundle / "README.md"] = readme
        documents[bundle / "scripts" / "README.md"] = (
            "No canonical entry script exists. Creating one before the final source package "
            "is received would fabricate provenance.\n"
        )
        documents[bundle / "expected" / "README.md"] = (
            "The frozen July figure is a visual/numerical target only. Expected canonical "
            "outputs will be added after the external package passes its validation gate.\n"
        )
        requirement = {
            "panel_id": panel_id,
            "source_id": source["source_id"],
            "status": "awaiting_collaborator",
            "required_assets": required_assets,
            "validation_gate": source["validation_gate"],
            "forbidden_substitutes": [
                "preliminary local proteomics dataset",
                "early 2024 model summaries",
                "values digitized from the final figure",
                "inferred code or parameters",
            ],
        }
        documents[bundle / "config" / "required_assets.yaml"] = yaml.safe_dump(
            requirement, sort_keys=False, allow_unicode=True
        )
        provenance = {
            "schema_version": "1.0.0",
            "panel_id": panel_id,
            "status": "blocked_external",
            "generated_at_utc": "2026-08-11T00:00:00Z",
            "command": ["blocked_external", source["source_id"]],
            "inputs": [
                {
                    "relative_path": reference["relative_path"],
                    "sha256": reference["sha256"],
                    "bytes": int(reference["bytes"]),
                }
            ],
            "outputs": [],
            "software": {},
            "parameters": {},
            "random_seeds": {},
            "blocker": {
                "reason": source["description"],
                "required_assets": required_assets,
                "source_id": source["source_id"],
                "validation_gate": source["validation_gate"],
            },
        }
        text = json.dumps(provenance, indent=2, sort_keys=True) + "\n"
        documents[bundle / "metadata" / "provenance.json"] = text
        central = root / "metadata" / "provenance" / "external_blockers" / f"{panel_id}.json"
        documents[central] = text
    return documents


def synchronize(root: Path, *, write: bool) -> int:
    expected = _expected_documents(root)
    stale: list[str] = []
    for path, text in expected.items():
        if write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        elif not path.is_file() or path.read_text(encoding="utf-8") != text:
            stale.append(path.relative_to(root).as_posix())
    if stale:
        raise ValueError("External blocker bundles are stale: " + ", ".join(stale))
    return len(expected)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    count = synchronize(args.root.resolve(), write=args.write)
    print(f"{'wrote' if args.write else 'verified'} {count} blocker-bundle files")


if __name__ == "__main__":
    main()
