from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .provenance import validate_provenance
from .registries import available_panels, load_and_validate_registries, sha256_file

_MODULE_RE = re.compile(r"^analyses(?:\.[A-Za-z_][A-Za-z0-9_]*)+$")
_RUNNABLE_STATUSES = frozenset({"partial_reproduction", "reproduced"})


class ReproductionError(RuntimeError):
    pass


def _provenance_documents(root: Path) -> dict[str, tuple[Path, dict[str, Any]]]:
    documents: dict[str, tuple[Path, dict[str, Any]]] = {}
    exclusions_path = root / "config" / "pre_revision_analysis_exclusions.txt"
    excluded = {
        line.strip().rstrip("/")
        for line in exclusions_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    } if exclusions_path.is_file() else set()
    for path in sorted((root / "analyses").glob("**/metadata/provenance.json")):
        relative = path.relative_to(root).as_posix()
        if any(relative == prefix or relative.startswith(prefix + "/") for prefix in excluded):
            continue
        document = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ReproductionError(f"provenance document is not an object: {path}")
        errors = validate_provenance(document)
        if errors:
            rendered = "; ".join(f"{item.path}: {item.message}" for item in errors)
            raise ReproductionError(f"invalid provenance {path.relative_to(root)}: {rendered}")
        panel_id = str(document["panel_id"])
        if panel_id in documents:
            other = documents[panel_id][0].relative_to(root)
            raise ReproductionError(
                f"more than one canonical analysis provenance for {panel_id}: "
                f"{other}, {path.relative_to(root)}"
            )
        documents[panel_id] = (path, document)
    return documents


def _verify_artifacts(root: Path, entries: Sequence[Mapping[str, Any]], label: str) -> None:
    for entry in entries:
        relative = str(entry["relative_path"])
        path = root / relative
        if not path.is_file():
            raise ReproductionError(f"{label} is missing: {relative}")
        expected_bytes = int(entry["bytes"])
        if path.stat().st_size != expected_bytes:
            raise ReproductionError(
                f"{label} byte count differs for {relative}: "
                f"expected {expected_bytes}, found {path.stat().st_size}"
            )
        actual_sha = sha256_file(path)
        if actual_sha != entry["sha256"]:
            raise ReproductionError(
                f"{label} checksum differs for {relative}: "
                f"expected {entry['sha256']}, found {actual_sha}"
            )


def _portable_command(root: Path, command: Sequence[str]) -> list[str]:
    if not command:
        raise ReproductionError("empty reproduction command")
    executable = Path(command[0]).name
    if executable not in {"python", "python3", "python3.12"}:
        raise ReproductionError(f"unsupported reproduction executable: {command[0]!r}")
    normalized = [sys.executable, *command[1:]]
    if len(normalized) >= 3 and normalized[1] == "-m":
        if not _MODULE_RE.fullmatch(normalized[2]):
            raise ReproductionError(
                f"module is outside canonical analyses namespace: {normalized[2]}"
            )
        return normalized
    if len(normalized) < 2:
        raise ReproductionError("Python reproduction command does not name a script or module")
    script = Path(normalized[1])
    if (
        script.is_absolute()
        or ".." in script.parts
        or not script.parts
        or script.parts[0] != "analyses"
    ):
        raise ReproductionError(f"script is outside canonical analyses tree: {normalized[1]}")
    if not (root / script).is_file():
        raise ReproductionError(f"reproduction script is missing: {normalized[1]}")
    return normalized


def reproduction_inventory(root: Path) -> dict[str, list[str]]:
    root = root.resolve()
    report = load_and_validate_registries(root, strict_files=False)
    if report.errors:
        raise ReproductionError("registry validation failed; run `make inventory` for details")
    registry_available = {row["panel_id"] for row in available_panels(report)}
    documents = _provenance_documents(root)
    runnable = {
        panel_id
        for panel_id, (_, document) in documents.items()
        if document["status"] in _RUNNABLE_STATUSES
    }
    return {
        "runnable": sorted(runnable),
        "partial_reproduction": sorted(
            panel_id
            for panel_id, (_, document) in documents.items()
            if document["status"] == "partial_reproduction"
        ),
        "reproduced": sorted(
            panel_id
            for panel_id, (_, document) in documents.items()
            if document["status"] == "reproduced"
        ),
        "blocked_asset": sorted(
            panel_id
            for panel_id, (_, document) in documents.items()
            if document["status"] == "blocked_asset"
        ),
        "blocked_external": sorted(
            row["panel_id"] for row in report.panels if row["status"] == "blocked_external"
        ),
        "missing_provenance": sorted(registry_available - set(documents)),
    }


def reproduce_available_panels(root: Path, output: Path, *, strict: bool = False) -> dict[str, Any]:
    root = root.resolve()
    report = load_and_validate_registries(root, strict_files=False)
    if report.errors:
        raise ReproductionError("registry validation failed; run `make inventory` for details")

    documents = _provenance_documents(root)
    unknown = sorted(set(documents) - {row["panel_id"] for row in report.panels})
    if unknown:
        raise ReproductionError("provenance has unknown panel IDs: " + ", ".join(unknown))

    runnable_documents = {
        panel_id: value
        for panel_id, value in documents.items()
        if value[1]["status"] in _RUNNABLE_STATUSES
    }
    inventory = reproduction_inventory(root)
    external_blockers = inventory["blocked_external"]
    blocked_assets = inventory["blocked_asset"]
    missing_provenance = inventory["missing_provenance"]
    partial_panels = inventory["partial_reproduction"]
    if strict:
        problems: list[str] = []
        if external_blockers:
            problems.append("blocked_external=" + ",".join(external_blockers))
        if blocked_assets:
            problems.append("blocked_asset=" + ",".join(blocked_assets))
        if missing_provenance:
            problems.append("missing_provenance=" + ",".join(missing_provenance))
        if partial_panels:
            problems.append("partial_reproduction=" + ",".join(partial_panels))
        if problems:
            raise ReproductionError("strict reproduction is incomplete: " + "; ".join(problems))

    deterministic_env = os.environ.copy()
    deterministic_env.update(
        {
            "TZ": "UTC",
            "PYTHONHASHSEED": "0",
            "MPLBACKEND": "Agg",
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
        }
    )
    executed: list[dict[str, Any]] = []
    for panel_id in sorted(runnable_documents):
        provenance_path, before = runnable_documents[panel_id]
        _verify_artifacts(root, before["inputs"], f"{panel_id} input")
        command = _portable_command(root, before["command"])
        completed = subprocess.run(command, cwd=root, env=deterministic_env, check=False)
        if completed.returncode:
            raise ReproductionError(
                f"{panel_id} command failed with exit {completed.returncode}: {command!r}"
            )
        after = json.loads(provenance_path.read_text(encoding="utf-8"))
        if after.get("panel_id") != panel_id or after.get("status") not in _RUNNABLE_STATUSES:
            raise ReproductionError(
                f"{panel_id} rewrote provenance with an invalid identity/status"
            )
        errors = validate_provenance(after)
        if errors:
            rendered = "; ".join(f"{item.path}: {item.message}" for item in errors)
            raise ReproductionError(f"{panel_id} rewrote invalid provenance: {rendered}")
        _verify_artifacts(root, after["outputs"], f"{panel_id} output")
        executed.append(
            {
                "panel_id": panel_id,
                "status": after["status"],
                "command": ["python", *command[1:]],
                "provenance": provenance_path.relative_to(root).as_posix(),
                "outputs": [entry["relative_path"] for entry in after["outputs"]],
            }
        )

    lock_path = root / "uv.lock"
    payload: dict[str, Any] = {
        "schema_version": "1.0.0",
        "mode": "strict" if strict else "available",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "environment_lock": {
            "relative_path": "uv.lock",
            "sha256": hashlib.sha256(lock_path.read_bytes()).hexdigest(),
        },
        "executed_panel_count": len(executed),
        "executed_panels": executed,
        "blocked_external_panels": external_blockers,
        "blocked_asset_panels": blocked_assets,
        "missing_analysis_provenance_panels": missing_provenance,
        "complete": not (
            external_blockers or blocked_assets or missing_provenance or partial_panels
        ),
        "limitations": (
            []
            if strict
            else [
                "Only panels with validated canonical analysis provenance were executed.",
                "Partial reproduction begins from migrated processed inputs where "
                "provenance says so.",
                "Blocked and not-yet-migrated panels are reported explicitly and are "
                "not fabricated.",
            ]
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload
