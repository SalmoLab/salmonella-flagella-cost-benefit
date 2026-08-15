"""On-page font-size QA: declared panel font sizes shrink with the assembly scale."""

from __future__ import annotations

from pathlib import Path

import pytest

from flagella_repro.figure_qa import (
    assembly_scale,
    audit_graphics,
    effective_font_pt,
    svg_metrics,
)
from flagella_repro.theme import MINIMUM_ON_PAGE_FONT_PT

# Panel viewBox is 100 x 50 points, the assembly box is 25 x 20 millimetres.
# scale = min(25 / 100, 20 / 50) = 0.25 mm per point.
# effective_pt = 8 * 0.25 * (72 / 25.4) = 5.669291338582677 pt.
PANEL_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="100pt" height="50pt" '
    'viewBox="0 0 100 50"><text font-size="8">Time (min)</text></svg>'
)
EXPECTED_SCALE = 0.25
EXPECTED_EFFECTIVE_PT = 8.0 * 0.25 * (72.0 / 25.4)


def _write_panel(path: Path, content: str = PANEL_SVG) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_assembly_scale_matches_hand_computed_value() -> None:
    assert assembly_scale((100.0, 50.0), (25.0, 20.0)) == pytest.approx(EXPECTED_SCALE)


def test_effective_font_pt_converts_millimetres_to_points() -> None:
    assert effective_font_pt(8.0, EXPECTED_SCALE) == pytest.approx(EXPECTED_EFFECTIVE_PT)


def test_svg_metrics_reports_effective_font_size(tmp_path: Path) -> None:
    path = _write_panel(tmp_path / "panel.svg")
    result = svg_metrics(path, box_mm=(25.0, 20.0))
    assert result["minimum_declared_font_size"] == pytest.approx(8.0)
    assert result["assembly_scale"] == pytest.approx(EXPECTED_SCALE)
    assert result["minimum_effective_font_pt"] == pytest.approx(EXPECTED_EFFECTIVE_PT)
    assert result["minimum_effective_font_pt"] < MINIMUM_ON_PAGE_FONT_PT


def test_svg_metrics_without_box_reports_no_effective_size(tmp_path: Path) -> None:
    path = _write_panel(tmp_path / "panel.svg")
    result = svg_metrics(path)
    assert result["minimum_declared_font_size"] == pytest.approx(8.0)
    assert result["assembly_scale"] is None
    assert result["minimum_effective_font_pt"] is None


def _write_project(root: Path, box: dict[str, float]) -> None:
    _write_panel(root / "build" / "panels" / "Figure_9" / "A" / "F9_A.svg")
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "config" / "assembly_figure_09.yaml").write_text(
        "figure_id: Figure_9\n"
        "panels:\n"
        "- label: A\n"
        "  kind: svg\n"
        "  source: build/panels/Figure_9/A/F9_A.svg\n"
        f"  x: 5\n  y: 5\n  width: {box['width']}\n  height: {box['height']}\n",
        encoding="utf-8",
    )


def test_audit_graphics_flags_panel_below_threshold(tmp_path: Path) -> None:
    root = tmp_path / "project"
    _write_project(root, {"width": 25.0, "height": 20.0})
    payload = audit_graphics(root)
    panel = payload["svg_panels"][0]  # type: ignore[index]
    assert panel["figure_id"] == "Figure_9"
    assert panel["label"] == "A"
    assert panel["minimum_effective_font_pt"] == pytest.approx(EXPECTED_EFFECTIVE_PT)
    assert payload["minimum_on_page_font_pt"] == MINIMUM_ON_PAGE_FONT_PT
    assert payload["small_font_failures"] == ["build/panels/Figure_9/A/F9_A.svg"]


def test_audit_graphics_passes_large_enough_panel(tmp_path: Path) -> None:
    root = tmp_path / "project"
    # scale = min(100 / 100, 60 / 50) = 1.0 mm per point -> 8 * 72 / 25.4 = 22.68 pt.
    _write_project(root, {"width": 100.0, "height": 60.0})
    payload = audit_graphics(root)
    panel = payload["svg_panels"][0]  # type: ignore[index]
    assert panel["assembly_scale"] == pytest.approx(1.0)
    assert panel["minimum_effective_font_pt"] == pytest.approx(8.0 * 72.0 / 25.4)
    assert payload["small_font_failures"] == []


def test_audit_graphics_ignores_unreferenced_panel(tmp_path: Path) -> None:
    root = tmp_path / "project"
    _write_project(root, {"width": 25.0, "height": 20.0})
    _write_panel(root / "build" / "panels" / "Figure_9" / "diagnostic" / "extra.svg")
    payload = audit_graphics(root)
    extra = next(
        row
        for row in payload["svg_panels"]  # type: ignore[union-attr]
        if row["relative_path"].endswith("extra.svg")
    )
    assert extra["figure_id"] is None
    assert extra["minimum_effective_font_pt"] is None
    assert payload["small_font_failures"] == ["build/panels/Figure_9/A/F9_A.svg"]


def test_panel_declared_exactly_at_the_floor_passes(tmp_path: Path) -> None:
    """A panel rendered 1:1 and declared at the floor must not be failed.

    ``scale * 72 / 25.4`` is 1.0 in exact arithmetic but 0.99999999999999978 in
    binary floating point, so the effective size of a 6 pt label lands a whisker
    below 6 pt. Without a tolerance the whole collection fails on rounding.
    """
    root = tmp_path / "project"
    floor = MINIMUM_ON_PAGE_FONT_PT
    _write_panel(
        root / "build" / "panels" / "Figure_9" / "A" / "F9_A.svg",
        '<svg xmlns="http://www.w3.org/2000/svg" width="100pt" height="50pt" '
        f'viewBox="0 0 100 50"><text font-size="{floor}">N = 6</text></svg>',
    )
    # A 100 x 50 pt panel occupies exactly its own size in millimetres.
    box = {"width": 100.0 * 25.4 / 72.0, "height": 50.0 * 25.4 / 72.0}
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "config" / "assembly_figure_09.yaml").write_text(
        "figure_id: Figure_9\n"
        "panels:\n"
        "- label: A\n"
        "  kind: svg\n"
        "  source: build/panels/Figure_9/A/F9_A.svg\n"
        f"  x: 5\n  y: 5\n  width: {box['width']}\n  height: {box['height']}\n",
        encoding="utf-8",
    )
    payload = audit_graphics(root)
    panel = payload["svg_panels"][0]  # type: ignore[index]
    assert panel["minimum_effective_font_pt"] == pytest.approx(floor)
    assert payload["small_font_failures"] == []


def test_relative_font_declarations_are_counted_not_measured(tmp_path: Path) -> None:
    """A percentage font-size is relative to the inherited size, not absolute.

    Reading ``65%`` as 65 units would report a font that does not exist.
    """
    panel = _write_panel(
        tmp_path / "vendored.svg",
        '<svg xmlns="http://www.w3.org/2000/svg" width="100pt" height="50pt" '
        'viewBox="0 0 100 50"><text style="font-size:9px">Cell</text>'
        '<text style="font-size:65%">subscript</text></svg>',
    )
    metrics = svg_metrics(panel, box_mm=(100.0 * 25.4 / 72.0, 50.0 * 25.4 / 72.0))
    assert metrics["relative_font_declarations"] == 1
    assert metrics["minimum_declared_font_size"] == pytest.approx(9.0)
