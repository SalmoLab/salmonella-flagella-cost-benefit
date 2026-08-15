from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import pytest
import yaml

NOTICE = "PARTIAL REPRODUCIBLE REVISION — SEE DECLARED LIMITATIONS"


def _load_assembler():
    path = Path(__file__).parents[1] / "analyses" / "assembly" / "assemble_svg.py"
    spec = importlib.util.spec_from_file_location("flagella_svg_assembler", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_project(tmp_path: Path, **overrides: Any) -> Path:
    """Write one panel SVG and one assembly configuration, and return the config."""
    source = tmp_path / "panel.svg"
    source.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 5">'
        '<text id="label" x="1" y="3">data</text></svg>',
        encoding="utf-8",
    )
    config: dict[str, Any] = {
        "figure_id": "Figure_test_partial",
        "status": "partial_reproduction",
        "width_mm": 30,
        "height_mm": 20,
        "output_stem": "build/test_partial",
        "panels": [
            {
                "label": "A",
                "kind": "svg",
                "source": "panel.svg",
                "x": 2,
                "y": 4,
                "width": 12,
                "height": 8,
            },
            {
                "label": "B",
                "kind": "placeholder",
                "text": "Raw source required",
                "x": 16,
                "y": 4,
                "width": 12,
                "height": 8,
            },
        ],
    }
    config.update(overrides)
    config_path = tmp_path / "assembly.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return config_path


def _texts(output: Path) -> list[str]:
    root = ET.parse(output).getroot()
    return [node.text or "" for node in root.iter() if node.tag.endswith("text")]


def test_svg_assembly_is_deterministic_and_vector_only(tmp_path: Path) -> None:
    config_path = _write_project(tmp_path)
    assembler = _load_assembler()
    assembler.assemble(tmp_path, config_path)
    output = tmp_path / "build" / "test_partial.svg"
    first = output.read_bytes()
    assembler.assemble(tmp_path, config_path)
    assert output.read_bytes() == first
    root = ET.parse(output).getroot()
    assert not [node for node in root.iter() if node.tag.endswith("image")]
    assert [node for node in root.iter() if node.tag.endswith("text")]


def test_assembly_draws_no_banner_when_the_configuration_omits_the_notice(
    tmp_path: Path,
) -> None:
    """A submitted figure carries no banner, so the ``notice`` key is optional."""
    config_path = _write_project(tmp_path)
    _load_assembler().assemble(tmp_path, config_path)
    output = tmp_path / "build" / "test_partial.svg"
    assert NOTICE not in output.read_text(encoding="utf-8")
    root = ET.parse(output).getroot()
    assert not [node for node in root.iter() if node.get("fill") == "#9b2f2f"]


@pytest.mark.parametrize("empty", ["", "   "])
def test_assembly_treats_an_empty_notice_as_absent(tmp_path: Path, empty: str) -> None:
    config_path = _write_project(tmp_path, notice=empty)
    _load_assembler().assemble(tmp_path, config_path)
    output = tmp_path / "build" / "test_partial.svg"
    root = ET.parse(output).getroot()
    assert not [node for node in root.iter() if node.get("fill") == "#9b2f2f"]


def test_assembly_draws_the_banner_when_the_configuration_asks_for_it(
    tmp_path: Path,
) -> None:
    """The banner stays available while the collection is incomplete."""
    config_path = _write_project(tmp_path, notice=NOTICE)
    _load_assembler().assemble(tmp_path, config_path)
    output = tmp_path / "build" / "test_partial.svg"
    assert NOTICE in _texts(output)


def test_generated_configurations_carry_no_notice_key() -> None:
    """Every shipped assembly configuration builds a figure without a banner."""
    configs = sorted((Path(__file__).parents[1] / "config").glob("assembly_*.yaml"))
    assert len(configs) == 12
    for path in configs:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert "notice" not in document, path.name
