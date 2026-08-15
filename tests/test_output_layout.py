from __future__ import annotations

import csv
import json
from pathlib import Path

from tools.organize_build import FIGURE_FOLDERS, organize


def _panel_rows(root: Path) -> list[dict[str, str]]:
    with (root / "config" / "panels.csv").open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_canonical_output_tree_covers_every_panel_and_figure() -> None:
    root = Path(__file__).parents[1]
    counts = organize(root)
    assert counts == {"panels": 60, "figures": 12}

    rows = _panel_rows(root)
    expected_folders = set(FIGURE_FOLDERS.values())
    actual_folders = {
        path.name for path in (root / "build" / "panels").iterdir() if path.is_dir()
    }
    assert actual_folders == expected_folders
    for row in rows:
        panel_dir = (
            root
            / "build"
            / "panels"
            / FIGURE_FOLDERS[row["figure_id"]]
            / row["panel_label"]
        )
        assert (panel_dir / "status.json").is_file(), row["panel_id"]
        assert (panel_dir / "provenance.json").is_file(), row["panel_id"]

    actual_figures = {
        path.name for path in (root / "build" / "figures").iterdir() if path.is_dir()
    }
    assert actual_figures == expected_folders
    assert all(
        (root / "build" / "figures" / name / "status.json").is_file()
        for name in actual_figures
    )


def test_every_generated_panel_artifact_uses_its_panel_directory() -> None:
    root = Path(__file__).parents[1]
    folder_by_panel = {
        row["panel_id"]: (FIGURE_FOLDERS[row["figure_id"]], row["panel_label"])
        for row in _panel_rows(root)
    }
    for provenance_path in (root / "metadata" / "provenance").rglob("*.json"):
        document = json.loads(provenance_path.read_text(encoding="utf-8"))
        panel_id = document.get("panel_id")
        if not panel_id:
            continue
        folder, label = folder_by_panel[panel_id]
        panel_prefix = f"build/panels/{folder}/{label}/"
        allowed_data_prefixes = (
            f"build/source_data/{folder}/",
            f"build/statistics/{folder}/",
            f"build/diagnostics/{folder}/",
        )
        for output in document.get("outputs", []):
            relative = str(output["relative_path"])
            if relative.startswith("build/panels/"):
                assert relative.startswith(panel_prefix), (panel_id, relative)
            elif relative.startswith("build/"):
                assert relative.startswith(allowed_data_prefixes), (panel_id, relative)


def test_figure_composition_matches_the_approved_revision() -> None:
    """Pin the panel set of every figure after the 12 August 2026 revision.

    The revision withdrew the old Supplementary Figure 3, dropped the
    effective-diffusivity row of the old Supplementary Figure 4, renumbered the
    remaining supplements down one, and restored the measured sector composition
    as Figure 4D.
    """
    root = Path(__file__).parents[1]
    expected = {
        "Figure1": list("ABCDEFGH"),
        "Figure2": list("ABC"),
        "Figure3": list("ABCDE"),
        "Figure4": list("ABCDEF"),
        "Figure5": list("ABCDE"),
        "Figure6": list("ABCDE"),
        "Figure7": list("ABCDEFG"),
        "Supplementary1": list("AB"),
        "Supplementary2": list("A"),
        "Supplementary3": list("ABCDEFGHI"),
        "Supplementary4": list("ABCDEF"),
        "Supplementary5": list("ABC"),
    }
    actual: dict[str, list[str]] = {}
    for row in _panel_rows(root):
        actual.setdefault(row["figure_id"], []).append(row["panel_label"])
    assert actual == expected
    assert sum(len(labels) for labels in expected.values()) == 60


def test_collaborator_panels_have_generated_graphics() -> None:
    """Former collaborator-source panels keep canonical producers after renumbering."""
    root = Path(__file__).parents[1]
    cases = {
        "F3_D": ("Figure_3", "D", "F3_D"),
        "F3_E": ("Figure_3", "E", "F3_E"),
        "F4_B": ("Figure_4", "B", "Figure_4_B"),
        "F4_C": ("Figure_4", "C", "Figure_4_C"),
        "F4_D": ("Figure_4", "D", "Figure_4_D"),
        "F4_E": ("Figure_4", "E", "Figure_4_E"),
        "F4_F": ("Figure_4", "F", "Figure_4_F"),
        "F5_A": ("Figure_5", "A", "Figure_5_A"),
        "F5_B": ("Figure_5", "B", "Figure_5_B"),
        "F5_C": ("Figure_5", "C", "Figure_5_C"),
        "S2_A": ("Supplementary_Figure_2", "A", "S2_A"),
    }
    for panel_id, (folder, label, stem) in cases.items():
        directory = root / "build" / "panels" / folder / label
        status = json.loads((directory / "status.json").read_text(encoding="utf-8"))
        assert status["status"] == "partial_reproduction", panel_id
        assert (directory / f"{stem}.svg").is_file(), panel_id
        assert (directory / f"{stem}.pdf").is_file(), panel_id
        assert (directory / f"{stem}.png").is_file(), panel_id
