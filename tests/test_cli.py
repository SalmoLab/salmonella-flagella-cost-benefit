from __future__ import annotations

import json
from pathlib import Path

from flagella_repro.cli import main, write_workflow_plan


def test_bootstrap_metadata_does_not_record_author_path(registry_project: Path) -> None:
    assert main(["bootstrap", "--root", str(registry_project)]) == 0
    output = registry_project / "build" / "environment" / "bootstrap.json"
    document = json.loads(output.read_text(encoding="utf-8"))
    assert not document["python_executable"].startswith("/")


def test_available_preflight_skips_blockers(registry_project: Path) -> None:
    assert main(["preflight", "--root", str(registry_project), "--mode", "available"]) == 0


def test_strict_preflight_refuses_blockers(registry_project: Path) -> None:
    assert main(["preflight", "--root", str(registry_project), "--mode", "strict"]) == 2


def test_workflow_plan_contains_only_available_panels(registry_project: Path) -> None:
    output = registry_project / "build" / "workflow" / "available.json"
    write_workflow_plan(registry_project, "available", output)
    document = json.loads(output.read_text(encoding="utf-8"))
    assert len(document["panels"]) == 60
    assert document["blocked_external_skipped"] == []
    assert all(row["status"] != "blocked_external" for row in document["panels"])
