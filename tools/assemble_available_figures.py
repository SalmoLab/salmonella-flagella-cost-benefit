#!/usr/bin/env python3
"""Assemble every figure with currently reproducible panel SVGs."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from organize_build import organize

ASSEMBLY_CONFIGS = (
    "assembly_figure_01.yaml",
    "assembly_figure_02.yaml",
    "assembly_figure_03.yaml",
    "assembly_figure_04.yaml",
    "assembly_figure_05.yaml",
    "assembly_figure_06.yaml",
    "assembly_figure_07.yaml",
    "assembly_supplementary_01.yaml",
    "assembly_supplementary_02.yaml",
    "assembly_supplementary_03.yaml",
    "assembly_supplementary_04.yaml",
    "assembly_supplementary_05.yaml",
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    organize(root)
    for name in ASSEMBLY_CONFIGS:
        config = root / "config" / name
        # One process per composite bounds memory for SVGs containing millions
        # of path nodes and prevents one large figure from starving later ones.
        subprocess.run(
            [
                sys.executable,
                str(root / "analyses" / "assembly" / "assemble_svg.py"),
                "--root",
                str(root),
                "--config",
                str(config),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        print(f"assembled {name}")


if __name__ == "__main__":
    main()
