#!/usr/bin/env python3
"""Apply the approved seven-figure panel registry and baseline-reference mapping."""

from __future__ import annotations

import csv
from pathlib import Path

import yaml

from flagella_repro.registries import PANEL_ARTIFACT_FIELDS, PANEL_FIELDS

ROOT = Path(__file__).resolve().parents[1]

MAIN = {
    "Figure1": [
        (
            "A",
            "flhDC locus and Ptet control schematic",
            "schematic",
            "needs_asset_migration",
            "F1_A",
        ),
        (
            "B",
            "Representative Ptet hook and filament microscopy",
            "microscopy",
            "needs_asset_migration",
            "F1_B",
        ),
        ("C", "Ptet hook number across AnTc", "quantitative", "ready_migration", "F1_C"),
        ("D", "Ptet filament number across AnTc", "quantitative", "ready_migration", "F1_D"),
        ("E", "Hook-filament correlation in Ptet", "quantitative", "ready_migration", "F1_E"),
        (
            "F",
            "Synthetic Ppro promoter-series schematic",
            "schematic",
            "needs_asset_migration",
            "F1_F",
        ),
        ("G", "Representative Ppro hook microscopy", "microscopy", "needs_asset_migration", "F1_G"),
        ("H", "Ppro hook number across promoter series", "quantitative", "ready_migration", "F1_H"),
    ],
    "Figure2": [
        (
            "A",
            "Same-day-WT-normalized Ptet population growth",
            "quantitative",
            "ready_migration",
            "F2_A",
        ),
        (
            "B",
            "Same-day-WT-normalized Ppro population growth",
            "quantitative",
            "ready_migration",
            "F2_B",
        ),
        ("C", "Ppro single-cell growth distributions", "quantitative", "ready_migration", "F2_C"),
    ],
    "Figure3": [
        ("A", "Flagellar assembly-mutant schematic", "schematic", "needs_asset_migration", "F2_D"),
        ("B", "Assembly-mutant population growth", "quantitative", "ready_migration", "F2_E"),
        ("C", "Assembly-mutant single-cell growth", "quantitative", "ready_migration", "F2_F"),
        (
            "D",
            "Modeled growth versus flagellar mass and rotation",
            "model",
            "ready_migration",
            "F2_G",
        ),
        (
            "E",
            "Experimental and modeled growth-penalty comparison",
            "mixed_model_experiment",
            "ready_migration",
            "F2_H",
        ),
    ],
    "Figure4": [
        (
            "A",
            "Cell-economy model schematic",
            "model_schematic",
            "ready_migration",
            "F3_C:schematic",
        ),
        (
            "B",
            "Experimental sector changes with model overlay",
            "proteomics_model",
            "ready_migration",
            "F3_A;F3_C",
        ),
        ("C", "Protein-level sector composition", "proteomics", "ready_migration", "F3_B"),
        (
            "D",
            "Measured sector composition across strains",
            "proteomics",
            "ready_migration",
            "F3_A:composition",
        ),
        (
            "E",
            "Modeled sector allocation across flagellar fraction",
            "model",
            "ready_migration",
            "F3_C:quantitative",
        ),
        (
            "F",
            "Growth versus ribosomal and flagellar allocation",
            "proteomics",
            "ready_migration",
            "F3_D",
        ),
    ],
    "Figure5": [
        ("A", "Gradient migration and substrate access", "model", "ready_migration", "F3_E"),
        (
            "B",
            "Growth trajectories across flagellar allocation",
            "model",
            "ready_migration",
            "F3_F",
        ),
        ("C", "Final biomass optimum by flagellar fraction", "model", "ready_migration", "F3_G"),
        (
            "D",
            "Active-particle simulated net displacement in liquid",
            "simulation",
            "ready_migration",
            "S5:liquid",
        ),
        (
            "E",
            "Active-particle simulated net displacement in agarose",
            "simulation",
            "ready_migration",
            "S5:agarose",
        ),
    ],
    "Figure6": [
        ("A", "Ptet soft-agar motility", "quantitative", "ready_migration", "F4_A"),
        ("B", "Ppro soft-agar motility", "quantitative", "ready_migration", "F4_B"),
        (
            "C",
            "Radial halo sampling and WT hook counts",
            "mixed_image_quantitative",
            "ready_migration",
            "F4_C",
        ),
        ("D", "Structured-medium competition design", "schematic", "ready_migration", "F4_D"),
        (
            "E",
            "Competition-region microscopy and hook distributions",
            "mixed_image_quantitative",
            "ready_migration",
            "F4_E",
        ),
    ],
    "Figure7": [
        (
            "A",
            "WT versus PproA paired-unit effective diffusivity",
            "quantitative",
            "ready_migration",
            "F5_A",
        ),
        (
            "B",
            "WT versus PproB paired-unit effective diffusivity",
            "quantitative",
            "ready_migration",
            "F5_B",
        ),
        (
            "C",
            "PproA versus PproB paired-unit effective diffusivity",
            "quantitative",
            "ready_migration",
            "F5_C",
        ),
        (
            "D",
            "Effective-diffusivity speed and persistence decomposition",
            "quantitative",
            "ready_migration",
            "new:A4",
        ),
        ("E", "WT versus PproA hook distributions", "quantitative", "ready_migration", "F5_D"),
        ("F", "WT versus PproB hook distributions", "quantitative", "ready_migration", "F5_E"),
        ("G", "PproA versus PproB hook distributions", "quantitative", "ready_migration", "F5_F"),
    ],
}

REFERENCE = {
    "Figure1": "ref_figure_1_svg",
    "Figure2": "ref_figure_2_svg",
    "Figure3": "ref_figure_2_svg",
    "Figure4": "ref_figure_3_svg",
    "Figure5": "ref_figure_3_svg",
    "Figure6": "ref_figure_4_svg",
    "Figure7": "ref_figure_5_svg",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    old_panels = {row["panel_id"]: row for row in read_csv(ROOT / "config" / "panels.csv")}
    panels: list[dict[str, str]] = []
    links: list[dict[str, str]] = []
    figures: list[dict[str, object]] = []
    for figure_id, definitions in MAIN.items():
        panel_ids: list[str] = []
        for label, title, panel_type, status, legacy in definitions:
            number = figure_id.removeprefix("Figure")
            panel_id = f"F{number}_{label}"
            panel_ids.append(panel_id)
            panels.append(
                {
                    "panel_id": panel_id,
                    "figure_id": figure_id,
                    "panel_label": label,
                    "title": title,
                    "panel_type": panel_type,
                    "status": status,
                    "canonical_rule": f"build_revision_f{number}_{label.lower()}",
                    "final_artifact_id": REFERENCE[figure_id],
                    "legacy_panel_ids": legacy,
                    "notes": "12 August 2026 seven-figure revision",
                }
            )
            links.append(
                {
                    "panel_id": panel_id,
                    "artifact_id": REFERENCE[figure_id],
                    "usage": "final_output",
                }
            )
        figures.append(
            {
                "id": figure_id,
                "reference_source_id": ("Figure" + REFERENCE[figure_id].split("_")[2]),
                "panels": panel_ids,
            }
        )

    # The 12 August 2026 revision withdrew the old Supplementary Figure 3 and
    # renumbered the rest, so a supplement no longer reproduces the July figure
    # that carries its own number.  SUPPLEMENTARY records the surviving mapping.
    supplementary = (
        (1, "AB", "Supplementary1"),
        (2, "A", "Supplementary2"),
        (3, "ABCDEFGHI", "Supplementary4"),
        (4, "ABCDEF", "Supplementary5"),
        (5, "ABC", "Figure5"),
    )
    supplementary_ids = tuple(
        f"S{number}_{label}" for number, labels, _ in supplementary for label in labels
    )
    for panel_id in supplementary_ids:
        row = dict(old_panels[panel_id])
        panels.append(row)
        links.append(
            {
                "panel_id": panel_id,
                "artifact_id": row["final_artifact_id"],
                "usage": "final_output",
            }
        )
    for number, labels, reference_source_id in supplementary:
        figures.append(
            {
                "id": f"Supplementary{number}",
                "reference_source_id": reference_source_id,
                "panels": [f"S{number}_{label}" for label in labels],
            }
        )

    write_csv(ROOT / "config" / "panels.csv", PANEL_FIELDS, panels)
    base_links = [
        row
        for row in read_csv(ROOT / "config" / "panel_artifacts.csv")
        if row["artifact_id"].startswith("ref_")
    ]
    del base_links
    write_csv(ROOT / "config" / "panel_artifacts.csv", PANEL_ARTIFACT_FIELDS, links)
    (ROOT / "config" / "figures.yaml").write_text(
        yaml.safe_dump(
            {"reference_release": "2026-08-12-revision", "backend": "python", "figures": figures},
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    print(f"registered {len(panels)} panels across {len(figures)} figures")


if __name__ == "__main__":
    main()
