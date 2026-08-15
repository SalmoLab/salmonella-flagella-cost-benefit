"""Guard the exact P and q values the legends print.

Coauthor decision 1.6 asks every legend to carry the effect size, the confidence
interval and the exact P value.  The values are computed by
``tools/build_revision_reports.py`` and registered in
``docs/revision_2026-08-12/figure_numbers.csv``.  A legend that quotes a value
the register no longer produces has drifted away from the statistics table, so
these tests fail when that happens.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
REGISTER = ROOT / "docs" / "revision_2026-08-12" / "figure_numbers.csv"
LEGENDS = ROOT / "docs" / "revision_2026-08-12" / "legends.md"

#: A panel whose legend prints at least one exact P value.  The list is the
#: authoring decision, not a derived fact, so it is written down here.
PANELS_THAT_PRINT_A_P_VALUE = {
    "F1_H",
    "F2_A",
    "F2_B",
    "F2_C",
    "F3_B",
    "F3_C",
    "F3_E",
    "F4_B",
    "F6_B",
}


def registered_probabilities() -> list[dict[str, str]]:
    with REGISTER.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [row for row in rows if "P value" in row["quantity"] or "q value" in row["quantity"]]


def test_every_registered_probability_is_printed_in_a_legend() -> None:
    text = LEGENDS.read_text(encoding="utf-8")
    missing = []
    for row in registered_probabilities():
        token = re.escape(row["value"])
        # The value must stand alone, so 0.0011 does not match inside 0.00119.
        if re.search(rf"(?<![0-9.]){token}(?![0-9])", text) is None:
            missing.append(f"{row['panel_id']}: {row['quantity']} = {row['value']}")
    assert missing == [], "registered values that no legend prints: " + "; ".join(missing)


def test_no_legend_prints_a_threshold() -> None:
    """A legend states an exact value, never ``P < 0.05`` or ``n.s.``."""
    text = LEGENDS.read_text(encoding="utf-8")
    # Markdown bold uses asterisks, so a star significance marker cannot be
    # separated from emphasis by a pattern; the other three forms can.
    for forbidden in (r"P\s*<", r"p\s*<\s*0", r"\bn\.s\.", r"\bns\b"):
        assert re.search(forbidden, text) is None, f"legends.md carries a threshold: {forbidden}"


def test_corrected_values_are_never_called_p() -> None:
    """Benjamini-Hochberg values are q values and are registered as such."""
    for row in registered_probabilities():
        corrected = "Benjamini-Hochberg" in row["quantity"]
        assert corrected == ("q value" in row["quantity"]), row["quantity"]
        assert not (corrected and "P value" in row["quantity"]), row["quantity"]


def test_every_printing_panel_has_registered_rows() -> None:
    panels = {row["panel_id"] for row in registered_probabilities() if "P value" in row["quantity"]}
    assert panels == PANELS_THAT_PRINT_A_P_VALUE
