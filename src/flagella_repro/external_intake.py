"""Immutable intake for collaborator-delivered scientific source packages."""

from __future__ import annotations

import csv
import hashlib
import json
import mimetypes
import shutil
from datetime import UTC, date, datetime
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def known_source_ids(project_root: Path) -> set[str]:
    registry = project_root / "config" / "external_sources.csv"
    with registry.open(newline="", encoding="utf-8") as handle:
        return {row["source_id"] for row in csv.DictReader(handle)}


def freeze_delivery(
    *, project_root: Path, source: Path, source_id: str, received_date: date
) -> Path:
    source = source.resolve(strict=True)
    project_root = project_root.resolve(strict=True)
    if not (source.is_file() or source.is_dir()):
        raise ValueError("The delivered payload must be one file or directory")
    if source_id not in known_source_ids(project_root):
        raise ValueError(f"Unknown external source_id: {source_id}")

    delivery_dir = project_root / "archive" / "incoming" / received_date.isoformat() / source_id
    payload_dir = delivery_dir / "payload"
    destination = payload_dir / source.name
    if delivery_dir.exists():
        raise FileExistsError(
            f"Intake already exists and will not be overwritten: {delivery_dir}"
        )

    payload_dir.mkdir(parents=True)
    if source.is_file():
        source_hash = sha256_file(source)
        shutil.copyfile(source, destination)
        destination_hash = sha256_file(destination)
        if destination_hash != source_hash:
            raise OSError("Copied payload checksum does not match the delivered file")
        checksums = [(destination_hash, f"payload/{source.name}", destination.stat().st_size)]
        payload_kind = "file"
    else:
        symlinks = [path for path in source.rglob("*") if path.is_symlink()]
        if symlinks:
            raise ValueError("Directory deliveries containing symbolic links are not accepted")
        shutil.copytree(source, destination, copy_function=shutil.copyfile)
        checksums = []
        for source_file in sorted(path for path in source.rglob("*") if path.is_file()):
            relative = source_file.relative_to(source)
            copied_file = destination / relative
            source_hash = sha256_file(source_file)
            destination_hash = sha256_file(copied_file)
            if destination_hash != source_hash:
                raise OSError(f"Copied payload checksum mismatch: {relative.as_posix()}")
            checksums.append(
                (
                    destination_hash,
                    f"payload/{source.name}/{relative.as_posix()}",
                    copied_file.stat().st_size,
                )
            )
        payload_kind = "directory"

    checksum_record = "".join(f"{digest}  {relative}\n" for digest, relative, _ in checksums)
    (delivery_dir / "checksums.sha256").write_text(checksum_record, encoding="utf-8")
    manifest_hash = hashlib.sha256(checksum_record.encode("utf-8")).hexdigest()
    manifest = {
        "schema_version": 1,
        "source_id": source_id,
        "received_date": received_date.isoformat(),
        "intake_created_at_utc": datetime.now(UTC).isoformat(),
        "original_filename": source.name,
        "stored_relative_path": f"payload/{source.name}",
        "payload_kind": payload_kind,
        "file_count": len(checksums),
        "bytes": sum(size for _, _, size in checksums),
        "sha256": checksums[0][0] if payload_kind == "file" else manifest_hash,
        "checksum_manifest_sha256": manifest_hash,
        "mime_type": (
            mimetypes.guess_type(source.name)[0] or "application/octet-stream"
            if payload_kind == "file"
            else "inode/directory"
        ),
        "inspection_status": "not_inspected",
        "immutable": True,
    }
    (delivery_dir / "intake_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return delivery_dir
