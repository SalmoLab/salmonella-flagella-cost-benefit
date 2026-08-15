#!/usr/bin/env python3
"""Compose manuscript panels as a deterministic, editable SVG."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import yaml

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)

# The panel letter sits in the margin left of its box, in bold Arial.  One
# viewBox unit is one millimetre, so these numbers are millimetres on the page.
PANEL_LABEL_FONT_SIZE_MM = 5.2
PANEL_LABEL_OFFSET_MM = 2.0
# Arial Bold advances its widest panel letter, G, by 0.778 em.  The letter
# therefore reaches this far right of the box edge, into the panel itself.  A
# panel that draws its own text at the top left must start clear of this, or the
# letter and the text overprint.
PANEL_LABEL_REACH_MM = PANEL_LABEL_FONT_SIZE_MM * 0.778 - PANEL_LABEL_OFFSET_MM


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _number(value: str | None) -> float:
    if not value:
        raise ValueError("SVG dimension is missing")
    match = re.match(r"^([0-9.+-]+)", value)
    if not match:
        raise ValueError(f"Unsupported SVG dimension: {value}")
    return float(match.group(1))


def _view_box(root: ET.Element) -> tuple[float, float, float, float]:
    if "viewBox" in root.attrib:
        values = tuple(float(item) for item in root.attrib["viewBox"].split())
        if len(values) != 4:
            raise ValueError("SVG viewBox must have four values")
        return values  # type: ignore[return-value]
    return (0.0, 0.0, _number(root.get("width")), _number(root.get("height")))


def _namespace_ids(element: ET.Element, prefix: str) -> None:
    replacements: dict[str, str] = {}
    for node in element.iter():
        current = node.get("id")
        if current:
            replacements[current] = f"{prefix}_{current}"
            node.set("id", replacements[current])
    for node in element.iter():
        for key, value in list(node.attrib.items()):
            updated = value
            for old, new in replacements.items():
                updated = updated.replace(f"url(#{old})", f"url(#{new})")
                if updated == f"#{old}":
                    updated = f"#{new}"
            node.set(key, updated)


def _svg_group(source: Path, box: dict[str, Any], prefix: str) -> ET.Element:
    imported_root = ET.parse(source).getroot()
    min_x, min_y, width, height = _view_box(imported_root)
    target_width = float(box["width"])
    target_height = float(box["height"])
    scale = min(target_width / width, target_height / height)
    offset_x = float(box["x"]) + (target_width - width * scale) / 2
    offset_y = float(box["y"]) + (target_height - height * scale) / 2
    group = ET.Element(
        f"{{{SVG_NS}}}g",
        {
            "transform": (
                f"translate({offset_x:.6f} {offset_y:.6f}) scale({scale:.9f}) "
                f"translate({-min_x:.6f} {-min_y:.6f})"
            )
        },
    )
    for child in imported_root:
        group.append(deepcopy(child))
    _namespace_ids(group, prefix)
    return group


def _wrapped_lines(text: str, width: int = 33) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        candidate = " ".join([*current, word])
        if current and len(candidate) > width:
            lines.append(" ".join(current))
            current = [word]
        else:
            current.append(word)
    if current:
        lines.append(" ".join(current))
    return lines


def _placeholder(box: dict[str, Any]) -> ET.Element:
    group = ET.Element(f"{{{SVG_NS}}}g")
    x, y = float(box["x"]), float(box["y"])
    width, height = float(box["width"]), float(box["height"])
    group.append(
        ET.Element(
            f"{{{SVG_NS}}}rect",
            {
                "x": str(x),
                "y": str(y),
                "width": str(width),
                "height": str(height),
                "rx": "1.5",
                "fill": "#f4f4f4",
                "stroke": "#999999",
                "stroke-width": "0.35",
                "stroke-dasharray": "2 1.2",
            },
        )
    )
    lines = _wrapped_lines(str(box["text"]))
    text = ET.Element(
        f"{{{SVG_NS}}}text",
        {
            "x": str(x + width / 2),
            "y": str(y + height / 2 - (len(lines) - 1) * 2.2),
            "text-anchor": "middle",
            "font-family": "Arial, Helvetica, sans-serif",
            "font-size": "3.1",
            "fill": "#555555",
        },
    )
    for index, line in enumerate(lines):
        span = ET.SubElement(
            text,
            f"{{{SVG_NS}}}tspan",
            {"x": str(x + width / 2), "dy": "0" if index == 0 else "4.4"},
        )
        span.text = line
    group.append(text)
    return group


def assemble(project_root: Path, config_path: Path) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    width = float(config["width_mm"])
    height = float(config["height_mm"])
    root = ET.Element(
        f"{{{SVG_NS}}}svg",
        {
            "width": f"{width}mm",
            "height": f"{height}mm",
            "viewBox": f"0 0 {width} {height}",
            "version": "1.1",
        },
    )
    root.append(
        ET.Element(
            f"{{{SVG_NS}}}rect",
            {"x": "0", "y": "0", "width": str(width), "height": str(height), "fill": "white"},
        )
    )
    # The submission banner is optional and absent by default.  A submitted
    # figure must not carry it.  The collection is still incomplete, so the
    # banner can return: give the assembly configuration a ``notice`` key and
    # the assembler draws it again, above the first panel row.
    notice_text = str(config.get("notice") or "").strip()
    if notice_text:
        notice = ET.SubElement(
            root,
            f"{{{SVG_NS}}}text",
            {
                "x": str(width / 2),
                "y": "5.3",
                "text-anchor": "middle",
                "font-family": "Arial, Helvetica, sans-serif",
                "font-size": "3.2",
                "font-weight": "bold",
                "fill": "#9b2f2f",
            },
        )
        notice.text = notice_text

    inputs: list[dict[str, Any]] = [
        {
            "relative_path": config_path.relative_to(project_root).as_posix(),
            "sha256": sha256_file(config_path),
            "bytes": config_path.stat().st_size,
        }
    ]
    assembler_path = Path(__file__).resolve()
    if assembler_path.is_relative_to(project_root):
        inputs.append(
            {
                "relative_path": assembler_path.relative_to(project_root).as_posix(),
                "sha256": sha256_file(assembler_path),
                "bytes": assembler_path.stat().st_size,
            }
        )
    for index, panel in enumerate(config["panels"]):
        if panel["kind"] == "svg":
            source = project_root / panel["source"]
            if not source.is_file():
                raise FileNotFoundError(source)
            root.append(_svg_group(source, panel, f"p{index:02d}"))
            inputs.append(
                {
                    "relative_path": panel["source"],
                    "sha256": sha256_file(source),
                    "bytes": source.stat().st_size,
                }
            )
        elif panel["kind"] == "placeholder":
            root.append(_placeholder(panel))
        else:
            raise ValueError(f"Unknown assembly item kind: {panel['kind']}")
        if panel.get("label"):
            label = ET.SubElement(
                root,
                f"{{{SVG_NS}}}text",
                {
                    "x": str(float(panel["x"]) - PANEL_LABEL_OFFSET_MM),
                    "y": str(float(panel["y"]) + 2.5),
                    "font-family": "Arial, Helvetica, sans-serif",
                    "font-size": str(PANEL_LABEL_FONT_SIZE_MM),
                    "font-weight": "bold",
                    "fill": "black",
                },
            )
            label.text = str(panel["label"])

    output_stem = project_root / config["output_stem"]
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    svg_path = output_stem.with_suffix(".svg")
    ET.ElementTree(root).write(svg_path, encoding="utf-8", xml_declaration=True)
    svg_bytes = svg_path.read_bytes()
    rendered_paths: list[Path] = []
    render_blocker = ""
    try:
        import cairosvg

        png_path = output_stem.with_suffix(".png")
        pdf_path = output_stem.with_suffix(".pdf")
        cairosvg.svg2png(
            bytestring=svg_bytes,
            write_to=str(png_path),
            output_width=2161,
            output_height=2575,
        )
        cairosvg.svg2pdf(bytestring=svg_bytes, write_to=str(pdf_path))
        rendered_paths = [pdf_path, png_path]
    except (ImportError, OSError) as error:
        render_blocker = f"Python CairoSVG runtime unavailable: {error}"
    outputs = []
    for path in (svg_path, *rendered_paths):
        outputs.append(
            {
                "relative_path": path.relative_to(project_root).as_posix(),
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
            }
        )
    manifest = {
        "schema_version": "1.0.0",
        "figure_id": config["figure_id"],
        "status": config["status"],
        "backend": "Python",
        "config": config_path.relative_to(project_root).as_posix(),
        "dimensions_mm": {"width": width, "height": height},
        "grid": config.get("grid", {}),
        "panel_placements": [
            {
                key: panel[key]
                for key in ("label", "kind", "source", "x", "y", "width", "height")
                if key in panel
            }
            for panel in config["panels"]
        ],
        "inputs": inputs,
        "outputs": outputs,
        "limitations": config.get("limitations", []),
        "placeholders": [
            panel["text"] for panel in config["panels"] if panel["kind"] == "placeholder"
        ],
        "render_blocker": render_blocker,
        "manual_postprocessing": False,
    }
    manifest_path = output_stem.with_suffix(".manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    args = parser.parse_args()
    manifest = assemble(args.root.resolve(), args.config.resolve())
    encoded = base64.b64encode(json.dumps(manifest, sort_keys=True).encode()).decode()
    print(f"assembled {manifest['figure_id']} manifest_b64={encoded}")


if __name__ == "__main__":
    main()
