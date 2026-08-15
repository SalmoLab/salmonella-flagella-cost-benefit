#!/usr/bin/env python3
"""Build the Source Data deliverables.

The script writes one file per figure for submission and the combined
workbook for internal use. Both pass the same checksum gate.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from flagella_repro.source_workbook import (
    MAX_SOURCE_DATA_FILE_BYTES,
    build_source_data_files,
    build_source_workbook,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("build/source_data/Source_Data_revision_partial.xlsx"),
        help="path of the combined internal workbook",
    )
    parser.add_argument(
        "--per-figure-dir",
        type=Path,
        default=Path("build/source_data/submission"),
        help="directory that receives one Source Data file per figure",
    )
    parser.add_argument(
        "--deposit-dir",
        type=Path,
        default=Path("build/source_data/deposit"),
        help="directory that receives the bundle for the DOI-bearing repository",
    )
    parser.add_argument(
        "--max-file-bytes",
        type=int,
        default=MAX_SOURCE_DATA_FILE_BYTES,
        help="size cap of one Source Data file; a larger figure ships as a ZIP",
    )
    parser.add_argument(
        "--skip-combined",
        action="store_true",
        help="write only the per-figure files",
    )
    args = parser.parse_args()

    root = args.root.resolve(strict=True)
    result: dict[str, object] = {}
    if not args.skip_combined:
        result["combined"] = build_source_workbook(root, args.output)
        manifest = root / "build" / "source_data" / "Source_Data_revision_partial.manifest.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(
            json.dumps(result["combined"], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    per_figure = build_source_data_files(
        root,
        args.per_figure_dir,
        args.max_file_bytes,
        deposit_dir=args.deposit_dir,
    )
    result["per_figure"] = per_figure
    per_figure_manifest = (
        root / "build" / "source_data" / "Source_Data_per_figure.manifest.json"
    )
    per_figure_manifest.parent.mkdir(parents=True, exist_ok=True)
    per_figure_manifest.write_text(
        json.dumps(per_figure, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
