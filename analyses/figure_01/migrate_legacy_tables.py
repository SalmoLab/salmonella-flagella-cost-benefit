#!/usr/bin/env python3
"""Copy or verify the canonical Figure 1 tables from the immutable legacy bundle.

Verification is the default. Use ``--write`` only for the deliberate migration
step. The legacy collection is never opened for writing.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CopySpec:
    source: str
    target: str
    role: str
    expected_rows: int


COPY_SPECS = (
    CopySpec(
        "Figure1/Figure1C_hook-count_Ptet/data/underlying_cell_points.csv",
        "data/processed/figure_01/F1_C/cell_points.csv",
        "processed_cell_points",
        23046,
    ),
    CopySpec(
        "Figure1/Figure1C_hook-count_Ptet/data/underlying_replicate_means.csv",
        "data/processed/figure_01/F1_C/replicate_means.csv",
        "processed_replicate_means",
        21,
    ),
    CopySpec(
        "Figure1/Figure1C_hook-count_Ptet/data/stats_vs_wt.csv",
        "data/processed/figure_01/F1_C/legacy_statistics.csv",
        "legacy_statistics_reference",
        7,
    ),
    CopySpec(
        "Figure1/Figure1C_hook-count_Ptet/data/underlying_all_plotted_points.csv",
        "data/source_data/figure_01/F1_C/plotted_values.csv",
        "source_data_plotted_values",
        23067,
    ),
    CopySpec(
        "Figure1/Figure1C_hook-count_Ptet/data/stats_vs_wt.csv",
        "data/source_data/figure_01/F1_C/statistics.csv",
        "source_data_statistics",
        7,
    ),
    CopySpec(
        "Figure1/Figure1C_flagella-count_Ptet/data/underlying_cell_points.csv",
        "data/processed/figure_01/F1_D/cell_points.csv",
        "processed_cell_points",
        23046,
    ),
    CopySpec(
        "Figure1/Figure1C_flagella-count_Ptet/data/underlying_replicate_means.csv",
        "data/processed/figure_01/F1_D/replicate_means.csv",
        "processed_replicate_means",
        21,
    ),
    CopySpec(
        "Figure1/Figure1C_flagella-count_Ptet/data/stats_vs_wt.csv",
        "data/processed/figure_01/F1_D/legacy_statistics.csv",
        "legacy_statistics_reference",
        7,
    ),
    CopySpec(
        "Figure1/Figure1C_flagella-count_Ptet/data/underlying_all_plotted_points.csv",
        "data/source_data/figure_01/F1_D/plotted_values.csv",
        "source_data_plotted_values",
        23067,
    ),
    CopySpec(
        "Figure1/Figure1C_flagella-count_Ptet/data/stats_vs_wt.csv",
        "data/source_data/figure_01/F1_D/statistics.csv",
        "source_data_statistics",
        7,
    ),
    CopySpec(
        "Figure1/Figure1D_hook-filament-count_Ptet/data/underlying_cell_points.csv",
        "data/processed/figure_01/F1_E/cell_points.csv",
        "processed_cell_points",
        18873,
    ),
    CopySpec(
        "Figure1/Figure1D_hook-filament-count_Ptet/data/underlying_bubble_counts.csv",
        "data/processed/figure_01/F1_E/legacy_bubble_counts.csv",
        "legacy_bubble_reference",
        51,
    ),
    CopySpec(
        "Figure1/Figure1D_hook-filament-count_Ptet/data/hook_filament_spearman_summary.csv",
        "data/processed/figure_01/F1_E/legacy_statistics.csv",
        "legacy_statistics_reference",
        1,
    ),
    CopySpec(
        "Figure1/Figure1D_hook-filament-count_Ptet/data/underlying_cell_points.csv",
        "data/source_data/figure_01/F1_E/cell_points.csv",
        "source_data_cell_points",
        18873,
    ),
    CopySpec(
        "Figure1/Figure1D_hook-filament-count_Ptet/data/underlying_bubble_counts.csv",
        "data/source_data/figure_01/F1_E/bubble_counts.csv",
        "source_data_plotted_values",
        51,
    ),
    CopySpec(
        "Figure1/Figure1D_hook-filament-count_Ptet/data/hook_filament_spearman_summary.csv",
        "data/source_data/figure_01/F1_E/statistics.csv",
        "source_data_statistics",
        1,
    ),
    CopySpec(
        "Figure2/Figure2E_hook-count_Ppro/data/hook_count_ppro_histogram_counts_by_replicate.csv",
        "data/processed/figure_01/F1_H/histogram_counts.csv",
        "processed_histogram_counts",
        162,
    ),
    CopySpec(
        "Figure2/Figure2E_hook-count_Ppro/data/hook_count_ppro_replicate_means.csv",
        "data/processed/figure_01/F1_H/replicate_means.csv",
        "processed_replicate_means",
        15,
    ),
    CopySpec(
        "Figure2/Figure2E_hook-count_Ppro/data/stats_vs_wt.csv",
        "data/processed/figure_01/F1_H/legacy_statistics.csv",
        "legacy_statistics_reference",
        5,
    ),
    CopySpec(
        "Figure2/Figure2E_hook-count_Ppro/data/Figure2E_hook-count_Ppro_summary_table.csv",
        "data/processed/figure_01/F1_H/legacy_summary.csv",
        "legacy_summary_reference",
        5,
    ),
    CopySpec(
        "Figure2/Figure2E_hook-count_Ppro/data/hook_count_ppro_all_plotted_points.csv",
        "data/source_data/figure_01/F1_H/plotted_values.csv",
        "source_data_plotted_values",
        41676,
    ),
    CopySpec(
        "Figure2/Figure2E_hook-count_Ppro/data/stats_vs_wt.csv",
        "data/source_data/figure_01/F1_H/statistics.csv",
        "source_data_statistics",
        5,
    ),
    CopySpec(
        "Figure2/Figure2E_hook-count_Ppro/data/Figure2E_hook-count_Ppro_summary_table.csv",
        "data/source_data/figure_01/F1_H/summary.csv",
        "source_data_summary",
        5,
    ),
)

FIELDS = (
    "source_path",
    "target_path",
    "role",
    "rows",
    "bytes",
    "source_sha256",
    "target_sha256",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        return sum(1 for _row in reader)


def inventory(
    collection_root: Path, legacy_root: Path, *, write: bool
) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    for spec in COPY_SPECS:
        source = legacy_root / spec.source
        target = collection_root / spec.target
        if not source.is_file():
            raise FileNotFoundError(f"missing legacy source: {source}")
        source_rows = csv_rows(source)
        if source_rows != spec.expected_rows:
            raise RuntimeError(
                f"unexpected source rows for {spec.source}: {source_rows} != {spec.expected_rows}"
            )
        source_hash = sha256(source)
        if write:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        if not target.is_file():
            raise FileNotFoundError(f"missing migrated target: {target}")
        target_rows = csv_rows(target)
        target_hash = sha256(target)
        if target_rows != source_rows or target_hash != source_hash:
            raise RuntimeError(f"migrated target differs from source: {spec.target}")
        rows.append(
            {
                "source_path": f"manuscript_plots_final/{spec.source}",
                "target_path": spec.target,
                "role": spec.role,
                "rows": source_rows,
                "bytes": source.stat().st_size,
                "source_sha256": source_hash,
                "target_sha256": target_hash,
            }
        )
    return rows


def render_csv(rows: list[dict[str, str | int]]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def main() -> int:
    collection_root = Path(__file__).resolve().parents[2]
    legacy_root = collection_root.parent / "manuscript_plots_final"
    manifest = Path(__file__).with_name("migration_inventory.csv")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="copy tables and replace inventory")
    args = parser.parse_args()

    rendered = render_csv(inventory(collection_root, legacy_root, write=args.write))
    if args.write:
        manifest.write_text(rendered, encoding="utf-8", newline="")
        print(f"migrated {len(COPY_SPECS)} table copies")
        return 0
    if not manifest.is_file() or manifest.read_text(encoding="utf-8") != rendered:
        print("Figure 1 migration inventory is missing or stale")
        return 1
    print(f"verified {len(COPY_SPECS)} migrated table copies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
