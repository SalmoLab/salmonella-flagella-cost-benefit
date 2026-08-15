from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from .provenance import validate_provenance_tree
from .registries import (
    EXPECTED_PANEL_IDS,
    RegistryReport,
    available_panels,
    load_and_validate_registries,
)
from .reproduction import ReproductionError, reproduction_inventory


def _root(value: str) -> Path:
    path = Path(value).resolve()
    if not (path / "config").is_dir():
        raise argparse.ArgumentTypeError(f"not a reproducibility project root: {path}")
    return path


def _print_report(report: RegistryReport, *, as_json: bool) -> None:
    if as_json:
        print(report.to_json())
        return
    counts = report.as_dict()["counts"]
    print(
        "Registry inventory: "
        f"{counts['panels']} panels, {counts['artifacts']} artifacts, "
        f"{counts['panel_artifacts']} links"
    )
    print(
        f"Findings: {counts['errors']} errors, {counts['warnings']} warnings, "
        f"{counts['blockers']} external blockers"
    )
    for finding in report.findings:
        location = f" ({finding.location})" if finding.location else ""
        print(f"[{finding.severity.upper()}] {finding.code}: {finding.message}{location}")


def _provenance_findings(root: Path, *, verify_files: bool = True) -> tuple[int, int]:
    documents = validate_provenance_tree(root, verify_files=verify_files)
    error_count = 0
    panel_paths: dict[str, list[Path]] = {}
    for path, errors in documents:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            document = None
        if isinstance(document, dict) and isinstance(document.get("panel_id"), str):
            panel_paths.setdefault(document["panel_id"], []).append(path)
        for error in errors:
            error_count += 1
            print(
                f"[ERROR] provenance_validation: "
                f"{path.relative_to(root)}:{error.path}: {error.message}"
            )
    if len(documents) != len(EXPECTED_PANEL_IDS):
        error_count += 1
        print(
            f"[ERROR] provenance_inventory: expected exactly {len(EXPECTED_PANEL_IDS)} central provenance "
            f"documents, found {len(documents)}"
        )
    missing = sorted(EXPECTED_PANEL_IDS - set(panel_paths))
    if missing:
        error_count += 1
        print("[ERROR] provenance_inventory: missing panel IDs: " + ", ".join(missing))
    duplicates = {panel_id: paths for panel_id, paths in panel_paths.items() if len(paths) > 1}
    for panel_id, paths in sorted(duplicates.items()):
        error_count += 1
        locations = ", ".join(str(path.relative_to(root)) for path in paths)
        print(f"[ERROR] provenance_inventory: duplicate {panel_id}: {locations}")
    print(f"Provenance inventory: {len(documents)} documents, {error_count} validation errors")
    return len(documents), error_count


def command_bootstrap(args: argparse.Namespace) -> int:
    root = args.root
    report = load_and_validate_registries(root, strict_files=False)
    if report.errors:
        _print_report(report, as_json=False)
        return 1
    target = root / "build" / "environment" / "bootstrap.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        python_executable = str(Path(sys.executable).resolve().relative_to(root))
    except ValueError:
        python_executable = Path(sys.executable).name
    payload = {
        "schema_version": "1.0.0",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "python": platform.python_version(),
        "python_executable": python_executable,
        "platform": platform.platform(),
        "panel_count": len(report.panels),
        "blocked_panel_ids": sorted(
            row["panel_id"] for row in report.panels if row["status"] == "blocked_external"
        ),
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Bootstrap metadata written to {target.relative_to(root)}")
    return 0


def command_inventory(args: argparse.Namespace) -> int:
    report = load_and_validate_registries(args.root, strict_files=False)
    _print_report(report, as_json=args.json)
    return 1 if report.errors else 0


def command_audit(args: argparse.Namespace) -> int:
    report = load_and_validate_registries(args.root, strict_files=True)
    _print_report(report, as_json=args.json)
    _, provenance_errors = _provenance_findings(args.root)
    if report.errors or provenance_errors:
        return 1
    if report.blockers:
        print("Audit is incomplete because blocked_external panels remain unresolved.")
        return 2
    return 0


def command_preflight(args: argparse.Namespace) -> int:
    report = load_and_validate_registries(args.root, strict_files=False)
    if report.errors:
        _print_report(report, as_json=False)
        return 1
    try:
        inventory = reproduction_inventory(args.root)
    except ReproductionError as exc:
        print(f"Reproduction preflight failed: {exc}")
        return 1
    blocked = sorted(
        row["panel_id"] for row in report.panels if row["status"] == "blocked_external"
    )
    if args.mode == "strict":
        incomplete = {
            key: inventory[key]
            for key in (
                "blocked_external",
                "blocked_asset",
                "missing_provenance",
                "partial_reproduction",
            )
            if inventory[key]
        }
        if incomplete:
            print("Strict reproduction refused because the collection is incomplete:")
            for status, panel_ids in incomplete.items():
                print(f"  {status}: " + ", ".join(panel_ids))
            return 2
    if args.mode == "available":
        print(
            f"Available-only scope contains {len(available_panels(report))} non-external panels: "
            f"{len(inventory['runnable'])} executable and "
            f"{len(inventory['blocked_asset'])} blocked by missing assets."
        )
        if inventory["missing_provenance"]:
            print(
                "Panels without canonical analysis provenance: "
                + ", ".join(inventory["missing_provenance"])
            )
        if blocked:
            print("Explicitly skipped blocked_external panels: " + ", ".join(blocked))
    return 0


def write_workflow_plan(root: Path, mode: str, output: Path) -> None:
    report = load_and_validate_registries(root, strict_files=False)
    if report.errors:
        raise RuntimeError("registry validation failed; run `make inventory` for details")
    blocked = sorted(
        row["panel_id"] for row in report.panels if row["status"] == "blocked_external"
    )
    if mode == "strict" and blocked:
        raise RuntimeError("strict reproduction is blocked by: " + ", ".join(blocked))
    selected = report.panels if mode == "strict" else available_panels(report)
    payload = {
        "schema_version": "1.0.0",
        "mode": mode,
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "panels": [
            {
                "panel_id": row["panel_id"],
                "status": row["status"],
                "canonical_rule": row["canonical_rule"],
                "final_artifact_id": row["final_artifact_id"],
            }
            for row in selected
        ],
        "blocked_external_skipped": blocked if mode == "available" else [],
        "note": "Panel-selection plan. Execution completeness is recorded separately.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def command_workflow_plan(args: argparse.Namespace) -> int:
    write_workflow_plan(args.root, args.mode, args.output)
    print(f"Inventory-only workflow plan written to {args.output}")
    print("No scientific panel outputs were regenerated in the Wave 1 skeleton.")
    return 0


def _ignore_clean_room(_: str, names: list[str]) -> set[str]:
    excluded = {".venv", ".snakemake", "build", "__pycache__", ".pytest_cache", ".ruff_cache"}
    return {name for name in names if name in excluded or name.endswith(".pyc")}


def command_clean_room(args: argparse.Namespace) -> int:
    source = args.root
    with tempfile.TemporaryDirectory(prefix="flagella-repro-clean-room-") as temporary:
        destination = Path(temporary) / "manuscript_reproducible"
        shutil.copytree(source, destination, ignore=_ignore_clean_room, symlinks=False)
        report = load_and_validate_registries(destination, strict_files=False)
        # Generated build outputs are deliberately absent from the clean-room
        # copy at this stage. Validate provenance shape and exact panel coverage
        # now; file/checksum validation runs after a complete strict build.
        _, provenance_errors = _provenance_findings(destination, verify_files=False)
        _print_report(report, as_json=False)
        if report.errors or provenance_errors:
            print("Clean-room source validation failed before reproduction.")
            return 1
        try:
            inventory = reproduction_inventory(destination)
        except ReproductionError as exc:
            print(f"Clean-room reproduction inventory failed: {exc}")
            return 1
        incomplete = (
            inventory["blocked_external"]
            or inventory["blocked_asset"]
            or inventory["missing_provenance"]
            or inventory["partial_reproduction"]
        )
        if incomplete:
            print(
                "Strict clean-room reproduction is not yet runnable: "
                f"{len(inventory['blocked_external'])} blocked_external, "
                f"{len(inventory['blocked_asset'])} blocked_asset, "
                f"{len(inventory['missing_provenance'])} missing provenance, and "
                f"{len(inventory['partial_reproduction'])} partial-reproduction panels."
            )
            return 2
        bootstrap = subprocess.run(
            [str(destination / "scripts" / "bootstrap_environment.sh")], cwd=destination
        )
        if bootstrap.returncode:
            print(f"Clean-room environment bootstrap failed with exit {bootstrap.returncode}.")
            return 1
        make = subprocess.run(["make", "reproduce"], cwd=destination)
        if make.returncode:
            print(f"Clean-room strict reproduction failed with exit {make.returncode}.")
            return 1
        audit = subprocess.run(["make", "audit"], cwd=destination)
        if audit.returncode:
            print(f"Clean-room audit failed with exit {audit.returncode}.")
            return 1
        print("Clean-room environment bootstrap, strict reproduction, and audit passed.")
    return 0


def command_clean(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    for relative in ("build", ".snakemake"):
        target = (root / relative).resolve()
        if target.parent != root:
            raise RuntimeError(f"refusing unsafe clean target: {target}")
        if target.exists():
            shutil.rmtree(target)
            print(f"Removed generated directory {relative}/")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flagella-repro")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def project_command(name: str, handler: object) -> argparse.ArgumentParser:
        command = subparsers.add_parser(name)
        command.add_argument("--root", type=_root, default=Path.cwd().resolve())
        command.set_defaults(handler=handler)
        return command

    project_command("bootstrap", command_bootstrap)
    inventory = project_command("inventory", command_inventory)
    inventory.add_argument("--json", action="store_true")
    audit = project_command("audit", command_audit)
    audit.add_argument("--json", action="store_true")
    preflight = project_command("preflight", command_preflight)
    preflight.add_argument("--mode", choices=("available", "strict"), required=True)
    workflow = project_command("workflow-plan", command_workflow_plan)
    workflow.add_argument("--mode", choices=("available", "strict"), required=True)
    workflow.add_argument("--output", type=Path, required=True)
    project_command("clean-room", command_clean_room)
    project_command("clean", command_clean)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)
