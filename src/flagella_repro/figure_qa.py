"""Read-only QA and color-vision previews for canonical figure graphics."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from xml.etree import ElementTree as ET

import numpy as np
import yaml
from colorspacious import cspace_convert, machado_et_al_2009_matrix
from PIL import Image

from .theme import MINIMUM_ON_PAGE_FONT_PT

FONT_RE = re.compile(r"font-size\s*:\s*([0-9.]+)\s*([a-z%]*)")
STAR_RE = re.compile(r"(?:\*{1,3}|p\s*[<=>].*\*)", re.IGNORECASE)
NUMBER_RE = re.compile(r"^([0-9.+-]+)")
FONT_ATTR_RE = re.compile(r"^\s*([0-9.]+)\s*([a-z%]*)", re.IGNORECASE)
# An SVG font-size is either absolute or relative to the inherited size. Only an
# absolute value converts to a printed size on its own; a relative one (%, em,
# ex, rem) needs the whole inherited cascade. Relative declarations are counted
# and skipped, because reading "65%" as 65 units reports a font that does not
# exist and inflates the measured range.
ABSOLUTE_FONT_UNITS = {"", "px", "pt", "user"}

MM_PER_INCH = 25.4
POINTS_PER_INCH = 72.0
POINTS_PER_MM = POINTS_PER_INCH / MM_PER_INCH
# A panel rendered at its assembly box multiplies the declared size by
# scale * 72/25.4, which is 1.0 in exact arithmetic but 0.99999999999999978 in
# binary floating point. A panel declared exactly at the floor must pass, so the
# comparison allows a tolerance far below any real typographic difference.
FONT_PT_TOLERANCE = 1e-6


def _number(value: str | None) -> float | None:
    """Return the leading number of an SVG length such as ``504pt``."""
    if not value:
        return None
    match = NUMBER_RE.match(value.strip())
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def view_box_size(root: ET.Element) -> tuple[float, float] | None:
    """Return the user-unit (point) width and height of an SVG root element.

    The panel builders emit a ``viewBox`` in points. If it is absent, fall back
    to the ``width``/``height`` attributes, as ``analyses/assembly/assemble_svg.py``
    does.
    """
    view_box = root.get("viewBox")
    if view_box:
        values = [_number(item) for item in view_box.split()]
        if len(values) == 4 and None not in values:
            width, height = values[2], values[3]
            if width and height and width > 0 and height > 0:
                return (width, height)
    width = _number(root.get("width"))
    height = _number(root.get("height"))
    if width and height and width > 0 and height > 0:
        return (width, height)
    return None


def assembly_scale(view_box: tuple[float, float], box_mm: tuple[float, float]) -> float:
    """Return the uniform scale that fits a panel viewBox into an assembly box.

    ``analyses/assembly/assemble_svg.py`` places each panel with
    ``scale = min(box_w / viewBox_w, box_h / viewBox_h)``. The viewBox is in
    points, the box is in millimetres, so the scale is in millimetres per point.
    """
    view_width, view_height = view_box
    box_width, box_height = box_mm
    return min(box_width / view_width, box_height / view_height)


def effective_font_pt(declared_pt: float, scale: float) -> float:
    """Return the printed font size in points for a declared panel font size.

    ``declared_pt`` is the font size inside the panel SVG (viewBox units).
    ``scale`` is the assembly scale in millimetres per point. The result is the
    size on the printed page.
    """
    return declared_pt * scale * POINTS_PER_MM


def svg_metrics(path: Path, box_mm: tuple[float, float] | None = None) -> dict[str, object]:
    """Measure text metrics of one panel SVG.

    If ``box_mm`` gives the assembly box (width, height) in millimetres, the
    result also reports the assembly scale and the minimum on-page font size.

    Example:
        >>> svg_metrics(panel_path, box_mm=(54.0, 59.0))["minimum_effective_font_pt"]
    """
    root = ET.parse(path).getroot()
    text_nodes = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "text"]
    # A tspan carries its own font-size and its own text. Vendored artwork puts
    # both there, so a scan of <text> alone under-reports the smallest font and
    # can miss visible characters entirely.
    span_nodes = [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "tspan"]
    font_sizes: list[float] = []
    text_values: list[str] = []
    relative_declarations = 0
    for node in (*text_nodes, *span_nodes):
        if node.text:
            text_values.append(node.text)
        for match in (
            FONT_ATTR_RE.match(node.get("font-size") or ""),
            FONT_RE.search(node.get("style", "")),
        ):
            if match is None:
                continue
            if match.group(2).lower() in ABSOLUTE_FONT_UNITS:
                font_sizes.append(float(match.group(1)))
            else:
                relative_declarations += 1
    rendered_text = " ".join(text_values)
    declared = min(font_sizes) if font_sizes else None
    view_box = view_box_size(root)
    scale: float | None = None
    effective: float | None = None
    if box_mm is not None and view_box is not None:
        scale = assembly_scale(view_box, box_mm)
        if declared is not None:
            effective = effective_font_pt(declared, scale)
    return {
        "editable_text_nodes": len(text_nodes),
        "relative_font_declarations": relative_declarations,
        "minimum_declared_font_size": declared,
        "assembly_scale": scale,
        "minimum_effective_font_pt": effective,
        "contains_significance_star_text": bool(STAR_RE.search(rendered_text)),
        "width": root.get("width", ""),
        "height": root.get("height", ""),
        "viewBox": root.get("viewBox", ""),
    }


RENDER_DPI = 300.0
# 300 DPI reproduces build/diagnostics/figure_previews/Figure_1.png bit-for-bit
# (verified against the last known-good render), so new renders stay
# comparable to any preview kept from an earlier run.
FIGURE_SVG_SUFFIX = "_revision_partial.svg"


def render_svg_to_png(source: Path, target: Path, dpi: float = RENDER_DPI) -> Path:
    """Rasterise one assembled figure SVG to PNG with ``rsvg-convert``.

    The project's declared SVG renderer is CairoSVG, but ``cairocffi`` cannot
    ``dlopen`` libcairo on this host: the Homebrew prefix at ``/usr/local``
    ships an x86_64 dylib on an arm64 Mac, so the load fails with an
    architecture mismatch (see ``analyses/assembly/assemble_svg.py``, which
    already catches this and skips its PNG/PDF output). ``rsvg-convert`` is a
    self-contained x86_64 binary that macOS runs transparently under
    Rosetta 2, so it renders where CairoSVG cannot.

    Example:
        >>> render_svg_to_png(
        ...     Path("build/figures/Figure_1/Figure_1_revision_partial.svg"),
        ...     Path("build/diagnostics/figure_previews/Figure_1.png"),
        ... )
    """
    if shutil.which("rsvg-convert") is None:
        raise RuntimeError(
            "rsvg-convert is not on PATH; install it (e.g. `brew install librsvg`) "
            "to render figure previews."
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "rsvg-convert",
            "--dpi-x",
            str(dpi),
            "--dpi-y",
            str(dpi),
            "-o",
            str(target),
            str(source),
        ],
        check=True,
    )
    return target


def assembled_figures(root: Path) -> list[tuple[str, Path]]:
    """Return ``(figure_name, svg_path)`` pairs for each assembled figure.

    ``analyses/assembly/assemble_svg.py`` writes one SVG per figure to
    ``build/figures/<figure_name>/<figure_name>_revision_partial.svg``. The
    figure name is the directory name, e.g. ``Figure_1`` or
    ``Supplementary_Figure_3``. Missing ``build/figures`` (as in a QA test
    fixture that only sets up ``build/panels``) yields an empty list rather
    than an error.
    """
    figures_root = root / "build" / "figures"
    if not figures_root.is_dir():
        return []
    figures: list[tuple[str, Path]] = []
    for directory in sorted(figures_root.iterdir()):
        if not directory.is_dir():
            continue
        svg_path = directory / f"{directory.name}{FIGURE_SVG_SUFFIX}"
        if svg_path.is_file():
            figures.append((directory.name, svg_path))
    return figures


DEUTERANOMALY_SEVERITY = 100.0


def simulate_deuteranomaly(
    rgb01: np.ndarray, severity: float = DEUTERANOMALY_SEVERITY
) -> np.ndarray:
    """Apply the Machado, Oliveira & Fernandes (2009) deuteranomaly matrix.

    An earlier version of this module called ``cspace_convert(rgb, "sRGB1",
    {"name": "sRGB1+CVD", ...})``. That call has the two colorspaces the
    wrong way round. The "+CVD" space is the *start* space, not the end
    space: to simulate, convert **from** the CVD space **to** ``"sRGB1"``.
    Reversed, the conversion inverts the simulation matrix and returns
    nonsense — sRGB white comes back as ``[-10.25, 1.28, 0.98]`` and a
    saturated magenta reaches 5e6. colorspacious 1.1.2 is not at fault.

    This applies the published matrix directly in linear sRGB. The result
    agrees with the correctly ordered ``cspace_convert(rgb, {"name":
    "sRGB1+CVD", ...}, "sRGB1")`` to within 1e-3 per channel. The explicit
    form is kept because it states the two gamma steps and the matrix
    product on the page, which the fused call hides.

    ``rgb01`` holds sRGB channels in [0, 1] as the trailing array axis. The
    result is unclipped: some out-of-gamut values are expected (deuteranomia
    simulation systematically desaturates and can push a channel a little
    below 0 or above 1), and the caller decides how to clip for display.
    """
    linear = cspace_convert(rgb01, "sRGB1", "sRGB1-linear")
    matrix = machado_et_al_2009_matrix("deuteranomaly", severity)
    simulated_linear = np.einsum("ij,...j->...i", matrix, linear)
    return cspace_convert(simulated_linear, "sRGB1-linear", "sRGB1")


def deuteranopia_preview(source: Path, target: Path) -> dict[str, object]:
    with Image.open(source) as opened:
        image = opened.convert("RGB")
    rgb = np.asarray(image, dtype=float) / 255.0
    simulated = simulate_deuteranomaly(rgb)
    simulated = np.clip(simulated, 0.0, 1.0)
    target.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.round(simulated * 255).astype(np.uint8)).save(target)
    return {
        "source": source.as_posix(),
        "preview": target.as_posix(),
        "width": image.width,
        "height": image.height,
        "simulation": "Machado et al. (2009) deuteranomaly matrix, severity 100",
    }


def grayscale_preview(source: Path, target: Path) -> dict[str, object]:
    with Image.open(source) as opened:
        image = opened.convert("L")
    target.parent.mkdir(parents=True, exist_ok=True)
    image.save(target)
    return {
        "source": source.as_posix(),
        "preview": target.as_posix(),
        "width": image.width,
        "height": image.height,
        "simulation": "sRGB luminance grayscale",
    }


def assembly_placements(root: Path) -> dict[str, dict[str, object]]:
    """Map each panel SVG path to its placement in the assembly configs.

    The key is the panel path relative to the project root, as written in
    ``config/assembly_*.yaml``. If several configs place the same panel, the
    placement with the smallest scale wins, because it prints the smallest text.
    """
    placements: dict[str, dict[str, object]] = {}
    for config_path in sorted((root / "config").glob("assembly_*.yaml")):
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        figure_id = config.get("figure_id", "")
        for panel in config.get("panels", []):
            if panel.get("kind") != "svg" or not panel.get("source"):
                continue
            source = str(panel["source"])
            record = {
                "figure_id": figure_id,
                "label": panel.get("label", ""),
                "assembly_config": config_path.relative_to(root).as_posix(),
                "box_mm": (float(panel["width"]), float(panel["height"])),
            }
            previous = placements.get(source)
            if previous is None:
                placements[source] = record
                continue
            if min(record["box_mm"]) < min(previous["box_mm"]):  # type: ignore[arg-type]
                placements[source] = record
    return placements


def audit_graphics(root: Path) -> dict[str, object]:
    root = root.resolve()
    panel_root = root / "build" / "panels"
    placements = assembly_placements(root)
    svg_results = []
    for path in sorted(panel_root.glob("**/*.svg")):
        relative = path.relative_to(root).as_posix()
        placement = placements.get(relative)
        box_mm = placement["box_mm"] if placement else None
        svg_results.append(
            {
                "relative_path": relative,
                "figure_id": placement["figure_id"] if placement else None,
                "label": placement["label"] if placement else None,
                "assembly_config": placement["assembly_config"] if placement else None,
                **svg_metrics(path, box_mm=box_mm),  # type: ignore[arg-type]
            }
        )
    previews = []
    grayscale_previews = []
    figures = assembled_figures(root)
    deuteranopia_dir = root / "build" / "diagnostics" / "deuteranopia"
    grayscale_dir = root / "build" / "diagnostics" / "grayscale"
    preview_dir = root / "build" / "diagnostics" / "figure_previews"
    if figures:
        # Regenerate from scratch so a figure removed from the collection (as
        # happened to the former "Supplementary Figure 6") cannot leave a
        # stale preview behind under a name that no longer exists.
        for stale_dir in (deuteranopia_dir, grayscale_dir, preview_dir):
            if stale_dir.exists():
                shutil.rmtree(stale_dir)
            stale_dir.mkdir(parents=True, exist_ok=True)
    for name, svg_path in figures:
        rendered_png = render_svg_to_png(svg_path, preview_dir / f"{name}.png")
        target = deuteranopia_dir / f"{name}.png"
        record = deuteranopia_preview(rendered_png, target)
        record["source"] = rendered_png.relative_to(root).as_posix()
        record["preview"] = target.relative_to(root).as_posix()
        previews.append(record)
        grey_target = grayscale_dir / f"{name}.png"
        grey_record = grayscale_preview(rendered_png, grey_target)
        grey_record["source"] = rendered_png.relative_to(root).as_posix()
        grey_record["preview"] = grey_target.relative_to(root).as_posix()
        grayscale_previews.append(grey_record)
    payload: dict[str, object] = {
        "svg_panels": svg_results,
        "deuteranopia_previews": previews,
        "grayscale_previews": grayscale_previews,
        "svg_count": len(svg_results),
        "star_text_failures": [
            row["relative_path"] for row in svg_results if row["contains_significance_star_text"]
        ],
        "editable_text_failures": [
            row["relative_path"] for row in svg_results if not row["editable_text_nodes"]
        ],
        "minimum_on_page_font_pt": MINIMUM_ON_PAGE_FONT_PT,
        "small_font_failures": [
            row["relative_path"]
            for row in svg_results
            if row["minimum_effective_font_pt"] is not None
            and row["minimum_effective_font_pt"] < MINIMUM_ON_PAGE_FONT_PT - FONT_PT_TOLERANCE
        ],
    }
    report = root / "build" / "diagnostics" / "figure_qa.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload
