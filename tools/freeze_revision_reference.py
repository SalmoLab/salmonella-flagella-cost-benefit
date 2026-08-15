#!/usr/bin/env python3
"""Freeze the immutable 12 August 2026 figure-revision reference package."""

from __future__ import annotations

import argparse
import csv
import hashlib
import mimetypes
import shutil
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "reference" / "2026-08-12-revision"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dimensions(path: Path) -> tuple[str, str]:
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".tif", ".tiff"}:
        with Image.open(path) as image:
            return str(image.width), str(image.height)
    if path.suffix.lower() == ".svg":
        root = ET.parse(path).getroot()
        view_box = root.get("viewBox", "").split()
        if len(view_box) == 4:
            return view_box[2], view_box[3]
        return root.get("width", ""), root.get("height", "")
    return "", ""


def copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def extract_embedded_figures(manuscript: Path, destination: Path) -> list[Path]:
    extracted: list[Path] = []
    with zipfile.ZipFile(manuscript) as archive:
        for name in sorted(archive.namelist()):
            if not name.startswith("word/media/") or name.endswith("/"):
                continue
            target = destination / Path(name).name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(name))
            extracted.append(target)
    return extracted


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--manuscript", type=Path, required=True)
    parser.add_argument("--figures", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    existing = (
        [
            path
            for path in RELEASE.rglob("*")
            if path.is_file() and path.name != "BASELINE_EXCEPTION.md"
        ]
        if RELEASE.exists()
        else []
    )
    if existing:
        raise SystemExit(f"Refusing to overwrite non-empty frozen release: {RELEASE}")

    sources: list[tuple[Path, Path, str]] = []
    prompt_target = RELEASE / "revision_prompt" / args.prompt.name
    manuscript_target = RELEASE / "manuscript" / args.manuscript.name
    copy_file(args.prompt.resolve(), prompt_target)
    copy_file(args.manuscript.resolve(), manuscript_target)
    sources.extend(
        [
            (args.prompt.resolve(), prompt_target, "updated revision instructions"),
            (args.manuscript.resolve(), manuscript_target, "merged coauthor manuscript"),
        ]
    )

    for source in sorted(args.figures.resolve().iterdir()):
        if source.is_file() and source.suffix.lower() in {".png", ".svg"}:
            target = RELEASE / "july_visual_reference" / source.name
            copy_file(source, target)
            sources.append((source, target, "9 July visual reference"))

    embedded = extract_embedded_figures(manuscript_target, RELEASE / "manuscript_embedded_media")
    sources.extend((manuscript_target, path, "embedded manuscript media") for path in embedded)

    fields = (
        "relative_path",
        "source_label",
        "source_filename",
        "sha256",
        "bytes",
        "mime_type",
        "width",
        "height",
        "source_modified_ns",
    )
    manifest = RELEASE / "reference_manifest.csv"
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for source, target, label in sources:
            width, height = dimensions(target)
            writer.writerow(
                {
                    "relative_path": target.relative_to(ROOT).as_posix(),
                    "source_label": label,
                    "source_filename": source.name,
                    "sha256": sha256_file(target),
                    "bytes": target.stat().st_size,
                    "mime_type": mimetypes.guess_type(target.name)[0] or "application/octet-stream",
                    "width": width,
                    "height": height,
                    "source_modified_ns": source.stat().st_mtime_ns,
                }
            )
    print(f"Frozen {len(sources)} revision-reference files under {RELEASE}")


if __name__ == "__main__":
    main()
