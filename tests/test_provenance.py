from __future__ import annotations

import hashlib
from pathlib import Path

from flagella_repro.provenance import validate_provenance, validate_provenance_files


def _artifact(path: str = "figures/panels/F1_C.svg") -> dict[str, object]:
    return {"relative_path": path, "sha256": "a" * 64, "bytes": 10, "rows": 0}


def test_reproduced_provenance_contract() -> None:
    document = {
        "schema_version": "1.0.0",
        "panel_id": "F1_C",
        "status": "reproduced",
        "generated_at_utc": "2026-08-10T08:00:00Z",
        "command": ["flagella-repro", "reproduce-panel", "F1_C"],
        "inputs": [_artifact("data/raw/F1_C.csv")],
        "outputs": [_artifact()],
        "software": {"python": "3.12.11"},
        "parameters": {},
        "random_seeds": {},
    }
    assert validate_provenance(document) == []


def test_blocked_provenance_requires_actionable_blocker() -> None:
    document = {
        "schema_version": "1.0.0",
        "panel_id": "F3_A",
        "status": "blocked_external",
        "generated_at_utc": "2026-08-10T08:00:00Z",
        "command": ["flagella-repro", "reproduce-panel", "F3_A"],
        "inputs": [],
        "outputs": [],
        "software": {},
        "parameters": {},
        "random_seeds": {},
    }
    errors = validate_provenance(document)
    assert any(error.path == "blocker" for error in errors)


def test_partial_reproduction_requires_limitations() -> None:
    document = {
        "schema_version": "1.0.0",
        "panel_id": "F1_C",
        "status": "partial_reproduction",
        "generated_at_utc": "2026-08-10T08:00:00Z",
        "command": ["flagella-repro"],
        "inputs": [_artifact("data/processed/F1_C.csv")],
        "outputs": [_artifact()],
        "software": {},
        "parameters": {},
        "random_seeds": {},
    }
    assert any(error.path == "limitations" for error in validate_provenance(document))


def test_provenance_rejects_external_paths() -> None:
    document = {
        "schema_version": "1.0.0",
        "panel_id": "F1_C",
        "status": "reproduced",
        "generated_at_utc": "2026-08-10T08:00:00Z",
        "command": ["flagella-repro"],
        "inputs": [_artifact("/tmp/input.csv")],
        "outputs": [_artifact()],
        "software": {},
        "parameters": {},
        "random_seeds": {},
    }
    assert any(error.path == "inputs[0].relative_path" for error in validate_provenance(document))


def test_provenance_files_verify_checksum_size_and_rows(tmp_path: Path) -> None:
    table = tmp_path / "data" / "points.csv"
    table.parent.mkdir()
    payload = b"x,y\n1,2\n3,4\n"
    table.write_bytes(payload)
    document = {
        "inputs": [
            {
                "relative_path": "data/points.csv",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": len(payload),
                "rows": 2,
            }
        ],
        "outputs": [],
    }

    assert validate_provenance_files(tmp_path, document) == []

    table.write_bytes(payload + b"5,6\n")
    errors = validate_provenance_files(tmp_path, document)
    assert {error.path for error in errors} == {
        "inputs[0].bytes",
        "inputs[0].sha256",
        "inputs[0].rows",
    }
