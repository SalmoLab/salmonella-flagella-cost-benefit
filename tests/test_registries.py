from __future__ import annotations

import csv
from pathlib import Path

from flagella_repro.registries import (
    BLOCKED_PANEL_IDS,
    EXPECTED_PANEL_COUNT,
    EXPECTED_PANEL_IDS,
    load_and_validate_registries,
    validate_relative_path,
)


def test_expected_panel_contract() -> None:
    assert len(EXPECTED_PANEL_IDS) == EXPECTED_PANEL_COUNT == 60
    assert BLOCKED_PANEL_IDS == set()


def test_inventory_accepts_planned_reference_outputs(registry_project: Path) -> None:
    report = load_and_validate_registries(registry_project, strict_files=False)
    assert report.errors == []
    assert report.blockers == []
    assert sum(f.code == "canonical_output_missing" for f in report.warnings) == 60


def test_strict_audit_rejects_reference_only_outputs(registry_project: Path) -> None:
    report = load_and_validate_registries(registry_project, strict_files=True)
    assert sum(f.code == "canonical_output_missing" for f in report.errors) == 60
    assert report.blockers == []


def test_wrong_blocked_panel_set_is_an_error(registry_project: Path) -> None:
    path = registry_project / "config" / "panels.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
        fields = tuple(rows[0])
    row = next(item for item in rows if item["panel_id"] == "F1_A")
    row["status"] = "blocked_external"
    row["canonical_rule"] = "blocked_f1_a"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    report = load_and_validate_registries(registry_project)
    assert any(f.code == "blocked_panel_set" for f in report.errors)


def test_portable_relative_path_contract() -> None:
    assert validate_relative_path("data/raw/file.csv") is None
    assert validate_relative_path("data/raw/files with spaces.csv") is None
    for invalid in (
        "/tmp/file.csv",
        "/mnt/data/file.csv",
        "../outside.csv",
        "~/private.csv",
        "C:\\private\\file.csv",
        "data\\raw\\file.csv",
    ):
        assert validate_relative_path(invalid) is not None
