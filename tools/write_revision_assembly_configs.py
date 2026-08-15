#!/usr/bin/env python3
"""Write the approved deterministic layouts for seven main and five supplements."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def panel(label: str, source: str, x: float, y: float, width: float, height: float) -> dict:
    return {
        "label": label,
        "kind": "svg",
        "source": source,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
    }


def main_panel(figure: int, label: str, *box: float) -> dict:
    if figure <= 3:
        stem = f"F{figure}_{label}"
    elif figure <= 5:
        stem = f"Figure_{figure}_{label}"
    else:
        stem = f"Figure_{figure}{label}"
    source = f"build/panels/Figure_{figure}/{label}/{stem}.svg"
    return panel(label, source, *box)


def supp_panel(figure: int, label: str, *box: float) -> dict:
    source = f"build/panels/Supplementary_Figure_{figure}/{label}/S{figure}_{label}.svg"
    return panel(label, source, *box)


# Nature Communications sets the double column at 180 mm.  The collection used
# 183 mm before, so every figure lost 3 mm on 14 August 2026.
#
# The 3 mm came out of the two outer margins, which fell from 5.0 mm to 3.5 mm.
# Every panel box and every inter-panel gutter keeps its former size, because the
# assembler scales a panel by min(box / viewBox): a changed box changes the scale
# and every font size with it.  All twelve figures shared one frame — a 5 mm margin
# on each side and a rightmost panel edge at 178 mm — so one uniform trim served
# every figure.
#
# The outer margin carries no panel content.  The assembler fits and centres each
# panel inside its box, so panel ink never leaves the box.  Only the panel letter
# sits in the left margin, drawn 2 mm left of the box, and it still clears the
# canvas edge at a 3.5 mm margin.
LEFT_MARGIN_MM = 3.5

# The submission banner was removed on 14 August 2026.  A submitted figure must
# not carry it, so no configuration writes a ``notice`` key and the assembler
# treats the key as optional.  Five assets are still missing, so the banner can
# return: pass ``notice=PARTIAL_NOTICE`` to ``config`` and rerun this generator.
PARTIAL_NOTICE = "PARTIAL REPRODUCIBLE REVISION — SEE DECLARED LIMITATIONS"

# The banner occupied the band above the first panel row.  Panels began at
# y = 11 mm to clear it.  With the banner gone the band is white space, so every
# panel moved up by 6 mm and every figure lost 6 mm of height.  The remaining
# 5 mm holds the panel letter, whose cap top sits 3.75 mm below the canvas edge.
TOP_MARGIN_MM = 5.0


def config(
    figure_id: str,
    height: float,
    panels: list[dict],
    limitations: list[str],
    *,
    notice: str = "",
) -> dict:
    document = {
        "figure_id": figure_id,
        "status": "partial_reproduction",
        "width_mm": 180,
        "height_mm": height,
        "output_stem": f"build/figures/{figure_id}/{figure_id}_revision_partial",
        "limitations": limitations,
        "panels": panels,
    }
    if notice:
        document["notice"] = notice
    return document


def write(name: str, document: dict) -> None:
    (ROOT / "config" / name).write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def main() -> None:
    main_documents = {
        1: config(
            "Figure_1",
            212,
            [
                main_panel(1, "A", 3.5, 5, 54, 59),
                main_panel(1, "B", 62.5, 5, 55, 59),
                main_panel(1, "C", 122.5, 5, 54, 59),
                main_panel(1, "D", 3.5, 71, 54, 59),
                main_panel(1, "E", 62.5, 71, 55, 59),
                main_panel(1, "F", 122.5, 71, 54, 59),
                main_panel(1, "G", 3.5, 137, 84, 68),
                main_panel(1, "H", 92.5, 137, 84, 68),
            ],
            ["Panels A, B, F and G are explicit missing-asset placeholders."],
        ),
        2: config(
            "Figure_2",
            72,
            [
                main_panel(2, "A", 3.5, 5, 55, 60),
                main_panel(2, "B", 62.5, 5, 55, 60),
                main_panel(2, "C", 121.5, 5, 55, 60),
            ],
            ["Mother-machine source lineage remains partial; WT(S171) was not measured."],
        ),
        3: config(
            "Figure_3",
            132,
            [
                main_panel(3, "A", 3.5, 5, 55, 55),
                main_panel(3, "B", 62.5, 5, 55, 55),
                main_panel(3, "C", 121.5, 5, 55, 55),
                main_panel(3, "D", 3.5, 67, 84, 58),
                main_panel(3, "E", 92.5, 67, 84, 58),
            ],
            ["Panel A is an explicit missing editable-schematic placeholder."],
        ),
        # The measured sector composition returned as panel D, so the figure now
        # carries six panels.  Panels C to F share one 84 x 65 mm grid: the
        # measured and the modelled composition sit side by side in that grid, so
        # a reader compares them at one scale.
        4: config(
            "Figure_4",
            209,
            [
                main_panel(4, "A", 3.5, 5, 48, 55),
                main_panel(4, "B", 56.5, 5, 120, 55),
                main_panel(4, "C", 3.5, 67, 84, 65),
                main_panel(4, "D", 92.5, 67, 84, 65),
                main_panel(4, "E", 3.5, 139, 84, 65),
                main_panel(4, "F", 92.5, 139, 84, 65),
            ],
            ["Proteomics starts from delivered protein-level output; raw MS chain is absent."],
        ),
        5: config(
            "Figure_5",
            136,
            [
                main_panel(5, "A", 3.5, 5, 55, 57),
                main_panel(5, "B", 62.5, 5, 55, 57),
                main_panel(5, "C", 121.5, 5, 55, 57),
                main_panel(5, "D", 3.5, 69, 84, 60),
                main_panel(5, "E", 92.5, 69, 84, 60),
            ],
            [
                "Dynamic model between 0% and 1% flagellar allocation is recorded but "
                "not drawn; every step solves, and the solutions scatter across local "
                "optima."
            ],
        ),
        6: config(
            "Figure_6",
            142,
            [
                main_panel(6, "A", 3.5, 5, 55, 58),
                main_panel(6, "B", 62.5, 5, 55, 58),
                main_panel(6, "C", 121.5, 5, 55, 58),
                main_panel(6, "D", 3.5, 70, 84, 65),
                main_panel(6, "E", 92.5, 70, 84, 65),
            ],
            ["Original calibrated microscopy fields and scale bars remain unavailable."],
        ),
        # Panels A-C became a two-row block: unit mean speed above unit mean
        # log10 D_eff on the same paired-unit geometry.  Two 29 mm rows, a
        # medium header above the top row and a D ratio header above the bottom
        # row need 84 mm, up from 54 mm.  Panel D regained the D_eff row, so
        # its strip grows from 48 to 56 mm.
        7: config(
            "Figure_7",
            222,
            [
                main_panel(7, "A", 3.5, 5, 55, 84),
                main_panel(7, "B", 62.5, 5, 55, 84),
                main_panel(7, "C", 121.5, 5, 55, 84),
                main_panel(7, "D", 3.5, 96, 173, 56),
                main_panel(7, "E", 3.5, 159, 55, 56),
                main_panel(7, "F", 62.5, 159, 55, 56),
                main_panel(7, "G", 121.5, 159, 55, 56),
            ],
            ["Raw trajectory-to-summary and fluorescence-assignment chains remain partial."],
        ),
    }
    for number, document in main_documents.items():
        write(f"assembly_figure_{number:02d}.yaml", document)

    supplementary_documents = {
        1: config(
            "Supplementary_Figure_1",
            72,
            [supp_panel(1, "A", 3.5, 5, 84, 60), supp_panel(1, "B", 92.5, 5, 84, 60)],
            ["Upstream mother-machine tracking lineage remains partial."],
        ),
        2: config(
            "Supplementary_Figure_2",
            119,
            [supp_panel(2, "A", 3.5, 5, 173, 107)],
            ["Raw MS, FASTA and Spectronaut settings were not supplied."],
        ),
        # The paired motility panels lost their median effective-diffusivity row,
        # which duplicated Figure 7A-C.  Three metrics against three strain pairs
        # leave a true 3 x 3 grid, so each panel grows from 41 to 55 mm wide.
        #
        # The 14 August 2026 restyle put the two media side by side inside each
        # panel and moved the contrast wording to the legend and to the effect
        # table.  Each panel lost the 8 mm that wording cost, so the figure fell
        # from 190 to 166 mm, under the 185 mm the publisher allows for a caption
        # of fewer than 300 words.
        3: config(
            "Supplementary_Figure_3",
            166,
            [
                supp_panel(3, label, 3.5 + (index % 3) * 59, 5 + (index // 3) * 54, 55, 48)
                for index, label in enumerate("ABCDEFGHI")
            ],
            ["Raw trajectory processing lineage remains partial."],
        ),
        4: config(
            "Supplementary_Figure_4",
            186,
            [
                supp_panel(4, label, 3.5 + (index % 2) * 89, 5 + (index // 2) * 59, 84, 53)
                for index, label in enumerate("ADBECF")
            ],
            ["Parameters begin from migrated measured summaries; trajectories are illustrative."],
        ),
        # The speed against effective-diffusivity contours left main Figure 7
        # because a 55 mm box cannot hold them.  Each phenotype pair now gets a
        # full-width strip that carries agarose and liquid side by side.
        5: config(
            "Supplementary_Figure_5",
            194,
            [
                supp_panel(5, label, 3.5, 5 + index * 63, 173, 60)
                for index, label in enumerate("ABC")
            ],
            [
                "Contours pool trajectories; the paired experiment stays the inferential unit.",
                "Raw trajectory processing lineage remains partial.",
            ],
        ),
    }
    for number, document in supplementary_documents.items():
        write(f"assembly_supplementary_{number:02d}.yaml", document)
    stale = ROOT / "config" / "assembly_supplementary_06.yaml"
    stale.unlink(missing_ok=True)
    print("wrote 12 revision assembly configurations")


if __name__ == "__main__":
    main()
