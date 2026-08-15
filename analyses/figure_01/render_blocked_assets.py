"""Render unmistakable placeholders for unresolved Figure 1 visual assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import textwrap
from datetime import UTC, datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from flagella_repro.theme import (
    KEY_SWATCH,
    PALETTE,
    apply_publication_style,
    panel_figsize,
    save_figure,
)

COLLECTION_ROOT = Path(__file__).resolve().parents[2]
# The placeholder keeps its hatch and its "not supplied" wording; only the two
# inks move from literals to palette entries.  The notice takes the neutral
# reference grey so it reads as a note about the figure, never as data.
HATCH_INK = KEY_SWATCH
NOTICE_INK = PALETTE["neutral"]["reference"]
BLOCKED = {
    "A": "editable experimental-system schematic",
    "B": "raw representative hook-label microscopy field and crop metadata",
    "F": "editable constitutive-promoter schematic",
    "G": "raw representative constitutive-series microscopy field and crop metadata",
}


def artifact(path: Path) -> dict[str, object]:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "relative_path": path.relative_to(COLLECTION_ROOT).as_posix(),
        "sha256": digest.hexdigest(),
        "bytes": path.stat().st_size,
    }


def render(label: str) -> None:
    if label not in BLOCKED:
        raise KeyError(label)
    panel_id = f"F1_{label}"
    missing = BLOCKED[label]
    apply_publication_style()
    # The placeholder occupies the full assembly slot, so the assembler does
    # not shrink it and the notice stays readable at its declared size.
    figure, axis = plt.subplots(figsize=panel_figsize("Figure_1", label), constrained_layout=True)
    axis.add_patch(
        plt.Rectangle(
            (0.0, 0.0),
            1.0,
            1.0,
            transform=axis.transAxes,
            fill=False,
            hatch="///",
            edgecolor=HATCH_INK,
            linewidth=0.8,
        )
    )
    # A 54 mm slot holds about 24 characters per line at 7 pt.
    notice = textwrap.fill(missing.upper(), width=24)
    axis.text(
        0.5,
        0.5,
        f"{notice}\nnot supplied",
        ha="center",
        va="center",
        color=NOTICE_INK,
        fontsize=7,
        linespacing=1.35,
        transform=axis.transAxes,
    )
    axis.set_axis_off()
    panel_dir = COLLECTION_ROOT / "build/panels/Figure_1" / label
    figures = save_figure(figure, panel_dir / panel_id)
    source_dir = COLLECTION_ROOT / "build/source_data/Figure_1" / label
    source_dir.mkdir(parents=True, exist_ok=True)
    status_path = source_dir / f"{panel_id}_source_data.csv"
    pd.DataFrame(
        [
            {
                "panel_id": panel_id,
                "status": "blocked_asset",
                "missing_artifact": missing,
                "scientific_values_plotted": 0,
            }
        ]
    ).to_csv(status_path, index=False, lineterminator="\n")
    provenance = {
        "schema_version": "1.0.0",
        "panel_id": panel_id,
        "status": "blocked_asset",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "command": [
            ".venv/bin/python3.12",
            "analyses/figure_01/render_blocked_assets.py",
            "--panel",
            label,
        ],
        "inputs": [
            artifact(
                COLLECTION_ROOT
                / "analyses/figure_01"
                / f"panel_{label.lower()}"
                / "config/asset_intake.json"
            )
        ],
        "outputs": [artifact(path) for path in [status_path, *figures]],
        "software": {"python": platform.python_version(), "matplotlib": matplotlib.__version__},
        "parameters": {"scientific_values_plotted": 0},
        "random_seeds": {},
        "limitations": [f"Missing: {missing}. This output is an explicit placeholder."],
        "blocker": {"reason": missing, "required_assets": [missing]},
    }
    metadata = COLLECTION_ROOT / "analyses/figure_01" / f"panel_{label.lower()}" / "metadata"
    metadata.mkdir(parents=True, exist_ok=True)
    (metadata / "provenance.json").write_text(
        json.dumps(provenance, indent=2) + "\n", encoding="utf-8"
    )
    print(f"{panel_id}: blocked_asset placeholder")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--panel", choices=[*BLOCKED, "all"], default="all")
    args = parser.parse_args()
    labels = BLOCKED if args.panel == "all" else [args.panel]
    for label in labels:
        render(label)


if __name__ == "__main__":
    main()
