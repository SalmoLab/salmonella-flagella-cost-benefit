"""Render revised Figure 3C with the shared single-cell engine.

The engine anchors rotated x tick labels at their centre.  That is fine for
the four short promoter labels of Figure 2C.  This panel carries six longer
genotype labels in a 55 mm box, so a centred anchor makes neighbouring labels
overlap.  Anchoring each label at its right edge stacks them along the
rotation instead.  ``xtick.alignment`` sets the anchor only; every font size
and colour still comes from the shared theme.
"""

from pathlib import Path

import matplotlib as mpl

from analyses.figure_02.panel_c.scripts.plot import render

if __name__ == "__main__":
    mpl.rcParams["xtick.alignment"] = "right"
    render(Path(__file__).resolve().parents[1] / "config" / "config.json")
