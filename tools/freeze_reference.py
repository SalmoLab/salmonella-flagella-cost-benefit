#!/usr/bin/env python3
"""Copy and checksum the immutable 9 July 2026 manuscript reference release."""

from __future__ import annotations

import argparse
import csv
import hashlib
import mimetypes
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "reference" / "2026-07-09"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def artifact_id(path: Path) -> str:
    if path.suffix.lower() == ".docx":
        return "ref_manuscript_docx"
    stem = path.stem.lower().replace("-", "_").replace("supplemental_", "supplementary_")
    return f"ref_{stem}_{path.suffix.lower().lstrip('.')}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manuscript", type=Path, required=True)
    parser.add_argument("--figures", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_manuscript = args.manuscript.resolve()
    source_figures = args.figures.resolve()
    if RELEASE.exists() and any(RELEASE.rglob("*")):
        raise SystemExit(f"Refusing to overwrite non-empty frozen release: {RELEASE}")
    figures_out = RELEASE / "figures"
    manuscript_out = RELEASE / "manuscript"
    figures_out.mkdir(parents=True, exist_ok=True)
    manuscript_out.mkdir(parents=True, exist_ok=True)

    copied: list[tuple[Path, Path]] = []
    manuscript_target = manuscript_out / source_manuscript.name
    shutil.copy2(source_manuscript, manuscript_target)
    copied.append((source_manuscript, manuscript_target))

    for source in sorted(source_figures.iterdir()):
        if source.is_file() and source.suffix.lower() in {".png", ".svg"}:
            target = figures_out / source.name
            shutil.copy2(source, target)
            copied.append((source, target))

    manifest_path = ROOT / "reference_manifest.csv"
    artifact_path = ROOT / "config" / "artifacts.csv"
    manifest_fields = [
        "relative_path",
        "source_path",
        "sha256",
        "bytes",
        "mime_type",
        "source_modified_ns",
    ]
    artifact_fields = [
        "artifact_id",
        "relative_path",
        "role",
        "format",
        "sha256",
        "bytes",
        "generated_by_rule",
        "external_accession",
        "license",
    ]
    manifest_stream = manifest_path.open("w", encoding="utf-8", newline="")
    artifact_stream = artifact_path.open("w", encoding="utf-8", newline="")
    with manifest_stream as manifest_handle, artifact_stream as artifact_handle:
        manifest_writer = csv.DictWriter(manifest_handle, fieldnames=manifest_fields)
        artifact_writer = csv.DictWriter(artifact_handle, fieldnames=artifact_fields)
        manifest_writer.writeheader()
        artifact_writer.writeheader()
        for source, target in copied:
            checksum = sha256(target)
            relative = target.relative_to(ROOT).as_posix()
            mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            manifest_writer.writerow(
                {
                    "relative_path": relative,
                    "source_path": source.name,
                    "sha256": checksum,
                    "bytes": target.stat().st_size,
                    "mime_type": mime,
                    "source_modified_ns": source.stat().st_mtime_ns,
                }
            )
            artifact_writer.writerow(
                {
                    "artifact_id": artifact_id(target),
                    "relative_path": relative,
                    "role": "frozen_reference",
                    "format": target.suffix.lower().lstrip("."),
                    "sha256": checksum,
                    "bytes": target.stat().st_size,
                    "generated_by_rule": "",
                    "external_accession": "",
                    "license": "internal_reference",
                }
            )

    print(f"Frozen {len(copied)} files under {RELEASE}")
    print(f"Wrote {manifest_path}")
    print(f"Wrote {artifact_path}")


if __name__ == "__main__":
    main()
