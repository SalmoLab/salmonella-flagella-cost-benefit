from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import pytest

from flagella_repro.external_intake import freeze_delivery


def _project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "config").mkdir(parents=True)
    (root / "archive" / "incoming").mkdir(parents=True)
    (root / "config" / "external_sources.csv").write_text(
        "source_id,panel_ids,status,description,required_material,validation_gate\n"
        "final_gradient_model,F3_E,awaiting_collaborator,x,x,x\n",
        encoding="utf-8",
    )
    return root


def test_freeze_delivery_is_byte_exact_and_refuses_overwrite(tmp_path: Path) -> None:
    root = _project(tmp_path)
    payload = tmp_path / "model.zip"
    payload.write_bytes(b"not opened, just frozen\n")
    expected_hash = hashlib.sha256(payload.read_bytes()).hexdigest()

    delivery = freeze_delivery(
        project_root=root,
        source=payload,
        source_id="final_gradient_model",
        received_date=date(2026, 8, 10),
    )
    copied = delivery / "payload" / payload.name
    manifest = json.loads((delivery / "intake_manifest.json").read_text())
    assert copied.read_bytes() == payload.read_bytes()
    assert manifest["sha256"] == expected_hash
    assert manifest["inspection_status"] == "not_inspected"
    assert (delivery / "checksums.sha256").read_text().startswith(expected_hash)

    with pytest.raises(FileExistsError):
        freeze_delivery(
            project_root=root,
            source=payload,
            source_id="final_gradient_model",
            received_date=date(2026, 8, 10),
        )


def test_freeze_delivery_rejects_unknown_source(tmp_path: Path) -> None:
    root = _project(tmp_path)
    payload = tmp_path / "model.zip"
    payload.write_bytes(b"payload")
    with pytest.raises(ValueError, match="Unknown external source_id"):
        freeze_delivery(
            project_root=root,
            source=payload,
            source_id="not_registered",
            received_date=date(2026, 8, 10),
        )


def test_freeze_directory_delivery_records_every_file(tmp_path: Path) -> None:
    root = _project(tmp_path)
    payload = tmp_path / "model_folder"
    (payload / "code").mkdir(parents=True)
    (payload / "README.md").write_text("model\n", encoding="utf-8")
    (payload / "code" / "run.py").write_text("print('ok')\n", encoding="utf-8")

    delivery = freeze_delivery(
        project_root=root,
        source=payload,
        source_id="final_gradient_model",
        received_date=date(2026, 8, 11),
    )
    manifest = json.loads((delivery / "intake_manifest.json").read_text())
    checksum_lines = (delivery / "checksums.sha256").read_text().splitlines()
    assert manifest["payload_kind"] == "directory"
    assert manifest["file_count"] == 2
    assert len(checksum_lines) == 2
    assert (delivery / "payload" / "model_folder" / "code" / "run.py").is_file()
