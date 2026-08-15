from __future__ import annotations

import csv
import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath

PANEL_FIELDS = (
    "panel_id",
    "figure_id",
    "panel_label",
    "title",
    "panel_type",
    "status",
    "canonical_rule",
    "final_artifact_id",
    "legacy_panel_ids",
    "notes",
)
ARTIFACT_FIELDS = (
    "artifact_id",
    "relative_path",
    "role",
    "format",
    "sha256",
    "bytes",
    "generated_by_rule",
    "external_accession",
    "license",
)
PANEL_ARTIFACT_FIELDS = ("panel_id", "artifact_id", "usage")

PANEL_STATUSES = frozenset({"ready_migration", "needs_asset_migration", "blocked_external"})
ARTIFACT_USAGES = frozenset(
    {
        "raw_input",
        "processed_input",
        "statistics",
        "source_data",
        "image_asset",
        "panel_output",
        "final_output",
    }
)


def _panel_range(prefix: str, labels: str) -> set[str]:
    return {f"{prefix}_{label}" for label in labels}


# The 12 August 2026 structural revision withdrew the old Supplementary Figure 3
# and the effective-diffusivity row of the old Supplementary Figure 4, renumbered
# the remaining supplements 4-6 to 3-5, and restored the measured sector
# composition as Figure 4D.
EXPECTED_PANEL_IDS = frozenset(
    _panel_range("F1", "ABCDEFGH")
    | _panel_range("F2", "ABC")
    | _panel_range("F3", "ABCDE")
    | _panel_range("F4", "ABCDEF")
    | _panel_range("F5", "ABCDE")
    | _panel_range("F6", "ABCDE")
    | _panel_range("F7", "ABCDEFG")
    | _panel_range("S1", "AB")
    | {"S2_A"}
    | _panel_range("S3", "ABCDEFGHI")
    | _panel_range("S4", "ABCDEF")
    | _panel_range("S5", "ABC")
)
EXPECTED_PANEL_COUNT = 60
BLOCKED_PANEL_IDS = frozenset()

_RULE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[/\\]")


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    message: str
    location: str = ""


@dataclass
class RegistryReport:
    root: Path
    panels: list[dict[str, str]] = field(default_factory=list)
    artifacts: list[dict[str, str]] = field(default_factory=list)
    panel_artifacts: list[dict[str, str]] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    @property
    def errors(self) -> list[Finding]:
        return [finding for finding in self.findings if finding.severity == "error"]

    @property
    def warnings(self) -> list[Finding]:
        return [finding for finding in self.findings if finding.severity == "warning"]

    @property
    def blockers(self) -> list[Finding]:
        return [finding for finding in self.findings if finding.severity == "blocker"]

    def as_dict(self) -> dict[str, object]:
        return {
            "root": str(self.root),
            "counts": {
                "panels": len(self.panels),
                "artifacts": len(self.artifacts),
                "panel_artifacts": len(self.panel_artifacts),
                "errors": len(self.errors),
                "warnings": len(self.warnings),
                "blockers": len(self.blockers),
            },
            "blocked_panel_ids": sorted(
                row["panel_id"] for row in self.panels if row.get("status") == "blocked_external"
            ),
            "findings": [asdict(finding) for finding in self.findings],
        }

    def to_json(self) -> str:
        return json.dumps(self.as_dict(), indent=2, sort_keys=True)

    def add(self, severity: str, code: str, message: str, location: str = "") -> None:
        self.findings.append(Finding(severity, code, message, location))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_relative_path(value: str) -> str | None:
    if not value:
        return None
    if "\\" in value:
        return "must use POSIX separators"
    if value.startswith("~") or _WINDOWS_ABSOLUTE_RE.match(value):
        return "must not use a user-home or absolute path"
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        return "must be project-relative and must not contain '..'"
    if any(part in {"tmp", "mnt"} for part in path.parts[:1]):
        return "must not target temporary or mounted external storage"
    return None


def _read_csv(
    path: Path,
    expected_fields: tuple[str, ...],
    report: RegistryReport,
) -> list[dict[str, str]]:
    if not path.is_file():
        report.add("error", "registry_missing", "required registry is missing", str(path))
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        actual_fields = tuple(reader.fieldnames or ())
        if actual_fields != expected_fields:
            report.add(
                "error",
                "registry_header",
                f"expected header {expected_fields!r}, found {actual_fields!r}",
                str(path),
            )
            return []
        return [
            {key: (value or "").strip() for key, value in row.items()}
            for row in reader
            if any((value or "").strip() for value in row.values())
        ]


def _duplicates(rows: Iterable[Mapping[str, str]], key: str) -> set[str]:
    seen: set[str] = set()
    duplicate: set[str] = set()
    for row in rows:
        value = row.get(key, "")
        if value in seen:
            duplicate.add(value)
        seen.add(value)
    return duplicate


def load_and_validate_registries(root: Path, *, strict_files: bool = False) -> RegistryReport:
    root = root.resolve()
    report = RegistryReport(root=root)
    config = root / "config"
    report.panels = _read_csv(config / "panels.csv", PANEL_FIELDS, report)
    report.artifacts = _read_csv(config / "artifacts.csv", ARTIFACT_FIELDS, report)
    report.panel_artifacts = _read_csv(
        config / "panel_artifacts.csv", PANEL_ARTIFACT_FIELDS, report
    )
    _validate_panels(report)
    _validate_artifacts(report, strict_files=strict_files)
    _validate_links(report, strict_files=strict_files)
    return report


def _validate_panels(report: RegistryReport) -> None:
    panel_ids = {row.get("panel_id", "") for row in report.panels}
    if len(report.panels) != EXPECTED_PANEL_COUNT:
        report.add(
            "error",
            "panel_count",
            f"panels.csv must contain exactly {EXPECTED_PANEL_COUNT} rows; "
            f"found {len(report.panels)}",
        )
    missing = sorted(EXPECTED_PANEL_IDS - panel_ids)
    extra = sorted(panel_ids - EXPECTED_PANEL_IDS)
    if missing:
        report.add("error", "panel_ids_missing", f"missing panel IDs: {', '.join(missing)}")
    if extra:
        report.add("error", "panel_ids_extra", f"unexpected panel IDs: {', '.join(extra)}")
    for value in sorted(_duplicates(report.panels, "panel_id")):
        report.add("error", "panel_id_duplicate", f"duplicate panel ID {value!r}")

    rule_to_panel: dict[str, str] = {}
    blocked_actual: set[str] = set()
    for index, row in enumerate(report.panels, start=2):
        location = f"config/panels.csv:{index}"
        panel_id = row["panel_id"]
        status = row["status"]
        rule = row["canonical_rule"]
        if status not in PANEL_STATUSES:
            report.add("error", "panel_status", f"unsupported status {status!r}", location)
            continue
        if status == "blocked_external":
            blocked_actual.add(panel_id)
            report.add(
                "blocker",
                "blocked_external",
                f"{panel_id} requires external scientific assets",
                location,
            )
            if rule and not rule.startswith("blocked_"):
                report.add(
                    "error",
                    "blocked_rule",
                    "blocked panels need an empty canonical_rule or a 'blocked_' rule",
                    location,
                )
        else:
            if not rule:
                report.add(
                    "error", "canonical_rule_missing", "canonical_rule is required", location
                )
            elif not _RULE_RE.fullmatch(rule):
                report.add(
                    "error", "canonical_rule_invalid", f"invalid rule name {rule!r}", location
                )
            elif rule.startswith("blocked_"):
                report.add(
                    "error",
                    "canonical_rule_blocked",
                    "nonblocked panel uses a blocked rule",
                    location,
                )
            elif rule in rule_to_panel:
                report.add(
                    "error",
                    "canonical_rule_duplicate",
                    f"rule {rule!r} is also assigned to {rule_to_panel[rule]}",
                    location,
                )
            else:
                rule_to_panel[rule] = panel_id
    if blocked_actual != BLOCKED_PANEL_IDS:
        report.add(
            "error",
            "blocked_panel_set",
            "blocked_external must be exactly: " + ", ".join(sorted(BLOCKED_PANEL_IDS)),
        )


def _is_external_placeholder(row: Mapping[str, str]) -> bool:
    return row.get("role") == "external_placeholder" or bool(row.get("external_accession"))


def _validate_artifacts(report: RegistryReport, *, strict_files: bool) -> None:
    for value in sorted(_duplicates(report.artifacts, "artifact_id")):
        report.add("error", "artifact_id_duplicate", f"duplicate artifact ID {value!r}")
    for index, row in enumerate(report.artifacts, start=2):
        location = f"config/artifacts.csv:{index}"
        artifact_id = row["artifact_id"]
        if not artifact_id:
            report.add("error", "artifact_id_missing", "artifact_id is required", location)
        relative = row["relative_path"]
        placeholder = _is_external_placeholder(row)
        if not relative:
            severity = "warning" if placeholder else "error"
            report.add(severity, "artifact_path_missing", "relative_path is empty", location)
            continue
        path_error = validate_relative_path(relative)
        if path_error:
            report.add("error", "artifact_path_invalid", path_error, location)
            continue
        sha = row["sha256"].lower()
        if sha and not _SHA256_RE.fullmatch(sha):
            report.add(
                "error", "artifact_sha256", "sha256 must be 64 lowercase hex characters", location
            )
        byte_text = row["bytes"]
        if byte_text:
            try:
                if int(byte_text) < 0:
                    raise ValueError
            except ValueError:
                report.add(
                    "error", "artifact_bytes", "bytes must be a non-negative integer", location
                )

        local_path = report.root / PurePosixPath(relative)
        if not local_path.is_file():
            severity = "warning" if placeholder or not strict_files else "error"
            report.add(
                severity, "artifact_file_missing", f"file does not exist: {relative}", location
            )
            continue
        actual_bytes = local_path.stat().st_size
        if byte_text and int(byte_text) != actual_bytes:
            report.add(
                "error",
                "artifact_bytes_mismatch",
                f"expected {byte_text}, found {actual_bytes}",
                location,
            )
        elif not byte_text:
            severity = "error" if strict_files else "warning"
            report.add(severity, "artifact_bytes_unrecorded", "bytes is not recorded", location)
        if sha:
            actual_sha = sha256_file(local_path)
            if sha != actual_sha:
                report.add(
                    "error", "artifact_sha256_mismatch", "sha256 does not match file", location
                )
        elif not placeholder:
            severity = "error" if strict_files else "warning"
            report.add(severity, "artifact_sha256_unrecorded", "sha256 is not recorded", location)


def _validate_links(report: RegistryReport, *, strict_files: bool) -> None:
    panel_ids = {row["panel_id"] for row in report.panels}
    artifacts = {row["artifact_id"]: row for row in report.artifacts}
    seen: set[tuple[str, str, str]] = set()
    links_by_panel: dict[str, list[dict[str, str]]] = {}
    for index, row in enumerate(report.panel_artifacts, start=2):
        location = f"config/panel_artifacts.csv:{index}"
        key = (row["panel_id"], row["artifact_id"], row["usage"])
        if key in seen:
            report.add("error", "panel_artifact_duplicate", f"duplicate link {key!r}", location)
        seen.add(key)
        if row["panel_id"] not in panel_ids:
            report.add(
                "error",
                "panel_artifact_unknown_panel",
                f"unknown panel {row['panel_id']!r}",
                location,
            )
        if row["artifact_id"] not in artifacts:
            report.add(
                "error",
                "panel_artifact_unknown_artifact",
                f"unknown artifact {row['artifact_id']!r}",
                location,
            )
        if row["usage"] not in ARTIFACT_USAGES:
            report.add(
                "error", "panel_artifact_usage", f"unsupported usage {row['usage']!r}", location
            )
        links_by_panel.setdefault(row["panel_id"], []).append(row)

    for row in report.panels:
        panel_id = row["panel_id"]
        final_artifact_id = row["final_artifact_id"]
        links = links_by_panel.get(panel_id, [])
        if not links:
            severity = (
                "warning" if row["status"] == "blocked_external" or not strict_files else "error"
            )
            report.add(severity, "panel_artifacts_missing", f"{panel_id} has no artifact links")
        if final_artifact_id:
            if final_artifact_id not in artifacts:
                report.add(
                    "error",
                    "final_artifact_unknown",
                    f"{panel_id} references unknown final artifact {final_artifact_id!r}",
                )
            elif not any(
                link["artifact_id"] == final_artifact_id
                and link["usage"] in {"panel_output", "final_output"}
                for link in links
            ):
                report.add(
                    "error",
                    "final_artifact_unlinked",
                    f"{panel_id} final artifact is not linked as output",
                )
            elif (
                row["status"] != "blocked_external"
                and artifacts[final_artifact_id].get("role") == "frozen_reference"
                and not any(
                    link["usage"] in {"panel_output", "final_output"}
                    and artifacts.get(link["artifact_id"], {}).get("role")
                    != "frozen_reference"
                    for link in links
                )
            ):
                severity = "error" if strict_files else "warning"
                report.add(
                    severity,
                    "canonical_output_missing",
                    f"{panel_id} points only to a frozen reference, not a regenerated panel output",
                )
        elif row["status"] != "blocked_external":
            severity = "error" if strict_files else "warning"
            report.add(severity, "final_artifact_missing", f"{panel_id} has no final_artifact_id")


def available_panels(report: RegistryReport) -> list[dict[str, str]]:
    return [row for row in report.panels if row.get("status") != "blocked_external"]
