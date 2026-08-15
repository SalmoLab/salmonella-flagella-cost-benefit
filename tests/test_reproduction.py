from __future__ import annotations

import hashlib
import json
from pathlib import Path

from flagella_repro.registries import EXPECTED_PANEL_IDS
from flagella_repro.reproduction import reproduce_available_panels


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def test_available_runner_executes_declared_panel_and_reports_gaps(
    registry_project: Path,
) -> None:
    registry_project.joinpath("uv.lock").write_text("fixture lock\n", encoding="utf-8")
    input_payload = b"input\n"
    output_payload = b"output\n"
    input_path = registry_project / "data/processed/F1_A.csv"
    output_path = registry_project / "build/panels/F1_A.txt"
    script_path = registry_project / "analyses/fixture.py"
    provenance_path = (
        registry_project / "analyses/figure_01/panel_a/metadata/provenance.json"
    )
    input_path.parent.mkdir(parents=True)
    input_path.write_bytes(input_payload)
    script_path.parent.mkdir(parents=True)
    script_path.write_text(
        "from pathlib import Path\n"
        "p=Path('build/panels/F1_A.txt')\n"
        "p.parent.mkdir(parents=True, exist_ok=True)\n"
        "p.write_bytes(b'output\\n')\n",
        encoding="utf-8",
    )
    provenance_path.parent.mkdir(parents=True)
    provenance_path.write_text(
        json.dumps(
            {
                "schema_version": "1.0.0",
                "panel_id": "F1_A",
                "status": "partial_reproduction",
                "generated_at_utc": "2026-08-11T00:00:00Z",
                "command": ["python", "analyses/fixture.py"],
                "inputs": [
                    {
                        "relative_path": "data/processed/F1_A.csv",
                        "sha256": _sha(input_payload),
                        "bytes": len(input_payload),
                    }
                ],
                "outputs": [
                    {
                        "relative_path": "build/panels/F1_A.txt",
                        "sha256": _sha(output_payload),
                        "bytes": len(output_payload),
                    }
                ],
                "software": {"python": "3.12"},
                "parameters": {},
                "random_seeds": {},
                "limitations": ["fixture starts from a processed input"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = registry_project / "build/workflow/available_reproduction.json"
    result = reproduce_available_panels(registry_project, manifest)
    assert result["executed_panel_count"] == 1
    assert result["executed_panels"][0]["panel_id"] == "F1_A"
    assert len(result["missing_analysis_provenance_panels"]) == len(EXPECTED_PANEL_IDS) - 1
    assert result["blocked_external_panels"] == []
    assert result["complete"] is False
    assert output_path.read_bytes() == output_payload
    assert json.loads(manifest.read_text(encoding="utf-8"))["executed_panel_count"] == 1
