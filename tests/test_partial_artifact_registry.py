from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from flagella_repro.registries import PANEL_FIELDS
from tools.register_partial_artifacts import _managed_rows


def test_shared_output_gets_one_artifact_and_all_panel_links(tmp_path: Path) -> None:
    root = tmp_path / "collection"
    config = root / "config"
    config.mkdir(parents=True)
    with (config / "panels.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=PANEL_FIELDS)
        writer.writeheader()
        for panel_id in ("S5_A", "S5_B"):
            writer.writerow(
                {
                    "panel_id": panel_id,
                    "canonical_rule": f"plot_{panel_id.lower()}",
                }
            )

    relative = "data/source_data/shared.csv.gz"
    payload = b"compressed-tabular-placeholder"
    output = root / relative
    output.parent.mkdir(parents=True)
    output.write_bytes(payload)
    entry = {
        "relative_path": relative,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
    }
    input_relative = "data/processed/shared.csv"
    input_payload = b"x\n1\n"
    input_path = root / input_relative
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_bytes(input_payload)
    input_entry = {
        "relative_path": input_relative,
        "sha256": hashlib.sha256(input_payload).hexdigest(),
        "bytes": len(input_payload),
    }
    provenance = root / "metadata" / "provenance"
    provenance.mkdir(parents=True)
    for panel_id in ("S5_A", "S5_B"):
        (provenance / f"{panel_id}.json").write_text(
            json.dumps(
                {
                    "panel_id": panel_id,
                    "status": "partial_reproduction",
                    "inputs": [input_entry],
                    "outputs": [entry],
                }
            ),
            encoding="utf-8",
        )

    artifacts, links = _managed_rows(root)

    assert len(artifacts) == 2
    output_artifact = next(row for row in artifacts if row["relative_path"] == relative)
    input_artifact = next(row for row in artifacts if row["relative_path"] == input_relative)
    assert output_artifact["format"] == "csv.gz"
    assert input_artifact["role"] == "partial_processed_input"
    assert {(row["panel_id"], row["artifact_id"], row["usage"]) for row in links} == {
        ("S5_A", output_artifact["artifact_id"], "source_data"),
        ("S5_B", output_artifact["artifact_id"], "source_data"),
        ("S5_A", input_artifact["artifact_id"], "processed_input"),
        ("S5_B", input_artifact["artifact_id"], "processed_input"),
    }
