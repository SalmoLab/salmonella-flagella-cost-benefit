from __future__ import annotations

from pathlib import Path

from flagella_repro.figure_qa import svg_metrics


def test_svg_metrics_detect_editable_text_and_star(tmp_path: Path) -> None:
    path = tmp_path / "panel.svg"
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="10mm" height="8mm">'
        '<text font-size="7">p = 0.01</text></svg>',
        encoding="utf-8",
    )
    result = svg_metrics(path)
    assert result["editable_text_nodes"] == 1
    assert result["minimum_declared_font_size"] == 7
    assert result["contains_significance_star_text"] is False


def test_svg_metrics_rejects_significance_star(tmp_path: Path) -> None:
    path = tmp_path / "panel.svg"
    path.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><text>***</text></svg>',
        encoding="utf-8",
    )
    assert svg_metrics(path)["contains_significance_star_text"] is True
