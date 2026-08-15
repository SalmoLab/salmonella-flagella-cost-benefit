"""Deuteranopia/grayscale preview generation, and a regression guard on the
colour-vision transform.

An earlier version of this module called ``cspace_convert(rgb, "sRGB1",
{"name": "sRGB1+CVD", ...})``, which has the two colorspaces the wrong way
round: "+CVD" is the start space, not the end space. Reversed, the call
inverts the simulation matrix and returns values in the millions. The library
is correct; the call was not. ``figure_qa.simulate_deuteranomaly`` now applies
the published Machado et al. (2009) matrix directly in linear sRGB, and
``test_simulate_deuteranomaly_matches_library`` holds it against the correctly
ordered library call so the two cannot drift apart.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from flagella_repro.figure_qa import (
    assembled_figures,
    deuteranopia_preview,
    grayscale_preview,
    simulate_deuteranomaly,
)


def test_simulate_deuteranomaly_keeps_neutrals_neutral() -> None:
    """White and mid-grey have no red-green content, so CVD must not move them.

    The reversed call sent white to ``[-10.25, 1.28, 0.98]`` (see module
    docstring); the direct-matrix implementation must keep both within a hair
    of their input value.
    """
    white = np.ones((2, 2, 3))
    grey = np.full((2, 2, 3), 0.5)
    simulated_white = simulate_deuteranomaly(white)
    simulated_grey = simulate_deuteranomaly(grey)
    assert simulated_white == pytest.approx(1.0, abs=1e-3)
    assert simulated_grey == pytest.approx(0.5, abs=1e-3)


def test_simulate_deuteranomaly_stays_in_plausible_range() -> None:
    """A saturated colour desaturates; it must not explode past a small margin.

    The reversed call inflated a mid-tone orange's green channel from 0.11 to
    over 500,000. The correct transform can push a channel slightly out of
    [0, 1] (expected for a physically-based CVD simulation) but never by more
    than a fraction of a unit.
    """
    orange = np.tile(np.array([0.835, 0.369, 0.0]), (2, 2, 1))
    simulated = simulate_deuteranomaly(orange)
    assert np.all(simulated > -0.5)
    assert np.all(simulated < 1.5)


def test_simulate_deuteranomaly_matches_library() -> None:
    """The explicit matrix form must agree with colorspacious itself.

    ``simulate_deuteranomaly`` spells out the two gamma steps and the matrix
    product rather than using the fused "+CVD" colorspace. That is a
    readability choice, not a correction: the fused call is right as long as
    "+CVD" is the *start* space. This test pins the two together, so an
    upgrade that changes either one is caught.
    """
    from colorspacious import cspace_convert

    from flagella_repro.figure_qa import DEUTERANOMALY_SEVERITY

    samples = np.array(
        [
            [1.0, 1.0, 1.0],
            [0.5, 0.5, 0.5],
            [0.835, 0.369, 0.0],
            [0.106, 0.620, 0.467],
            [0.906, 0.161, 0.541],
        ]
    )
    cvd_space = {
        "name": "sRGB1+CVD",
        "cvd_type": "deuteranomaly",
        "severity": DEUTERANOMALY_SEVERITY,
    }
    expected = cspace_convert(samples, cvd_space, "sRGB1")
    assert simulate_deuteranomaly(samples) == pytest.approx(expected, abs=1e-3)


def test_assembled_figures_empty_when_build_figures_missing(tmp_path: Path) -> None:
    assert assembled_figures(tmp_path) == []


def test_assembled_figures_discovers_one_figure(tmp_path: Path) -> None:
    figure_dir = tmp_path / "build" / "figures" / "Figure_9"
    figure_dir.mkdir(parents=True)
    svg_path = figure_dir / "Figure_9_revision_partial.svg"
    svg_path.write_text("<svg></svg>", encoding="utf-8")
    assert assembled_figures(tmp_path) == [("Figure_9", svg_path)]


def _write_rgb_png(path: Path, rgb: tuple[int, int, int]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (4, 4), rgb).save(path)
    return path


def test_deuteranopia_preview_writes_same_size_rgb_image(tmp_path: Path) -> None:
    source = _write_rgb_png(tmp_path / "source.png", (213, 94, 0))  # D55E00
    target = tmp_path / "deuteranopia" / "source.png"
    record = deuteranopia_preview(source, target)
    assert target.is_file()
    with Image.open(target) as saved:
        assert saved.size == (4, 4)
        assert saved.mode == "RGB"
    assert record["width"] == 4
    assert record["height"] == 4


def test_grayscale_preview_writes_luminance_image(tmp_path: Path) -> None:
    source = _write_rgb_png(tmp_path / "source.png", (0, 114, 178))  # 0072B2
    target = tmp_path / "grayscale" / "source.png"
    record = grayscale_preview(source, target)
    with Image.open(target) as saved:
        assert saved.mode == "L"
    assert record["simulation"] == "sRGB luminance grayscale"
