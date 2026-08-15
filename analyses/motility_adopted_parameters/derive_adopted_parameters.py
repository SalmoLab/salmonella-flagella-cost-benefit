#!/usr/bin/env python3
"""Derive the one motility parameter table every manuscript panel reads.

What this module is
-------------------
The adopted table is the single canonical parameter file of the active-particle
simulation.  Figure 5D, Figure 5E, Supplementary Figure 4, the time-step
convergence ladder and Supplementary Table X all read it through
:func:`adopted_parameter_table_path`.  No other table may reach a manuscript
panel.

The table combines two decisions, both taken on the revision of 13 August 2026.

**Decision 1 - one global turn width.**  ``turn_angle_sd_rad`` is the same value
in all six phenotype-by-medium rows.  It is set so the mean turn magnitude
``sigma * sqrt(2 / pi)`` equals the 57 deg population mean turn angle of Taute
et al. 2015 (Nat Commun 6:8776, doi:10.1038/ncomms9776, PMID 26522289).  The two
turning rates are then rescaled by one factor per row so the model persistence
time still equals the measured one.  ``calibrate_global_turn_angle.py`` does
this; see ``docs/revision_2026-08-12/turn_angle_model_comparison.md``.

**Decision 2 - variant G of the stall parameters.**  ``stall_probability`` falls
with mean flagella number as ``N^-a``, with ``a`` set so the ratio between the
least and the most flagellated strain equals the 1.7 +/- 0.2 stall-frequency
ratio that Grognot et al. 2023 measured in 0.25 % agar (PNAS 120:e2301873120,
doi:10.1073/pnas.2301873120, PMID 37579142).  ``stall_mean_duration_s`` becomes
one global value in all three agarose rows.  See
``docs/revision_2026-08-12/stall_parameter_comparison.md``.

Why variant G and not the delivered stall numbers
-------------------------------------------------
Grognot et al. measured a significant flagella effect on the stall *frequency*
and quantified it.  They found the effect on stall *duration* significant only
at 0.16 % agar, not at the 0.25 % that matches our condition.  The delivered
table did the opposite: it put the flagella dependence in the duration and gave
the probability three per-strain values that are not monotone in flagella
number and have no source.  Variant G follows the evidence.

Provenance
----------
Nothing is typed in.  The turn width comes from the published angle, the stall
exponent from the published ratio, the flagella numbers from the per-cell hook
table, and every other column from the frozen delivered table and our paired
experimental units.  The derivation runs at build time and writes a checksum, an
audit table and a machine-readable record.

Setup:
    PYTHONPATH=$PWD/src .venv/bin/python \
        analyses/motility_adopted_parameters/derive_adopted_parameters.py

Complexity is O(rows).  The derivation runs in well under a second.  Pitfall:
the liquid rows carry ``stall_probability`` 0, so their stall duration never
fires; variant G leaves them untouched, and so does this module.
"""

from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "analyses/motility_parameter_calibration"))
sys.path.insert(0, str(PROJECT / "analyses/motility_turn_angle_comparison"))
sys.path.insert(0, str(PROJECT / "analyses/motility_stall_parameter_comparison"))
sys.path.insert(0, str(PROJECT / "models/motility_simulation/corrected/src"))

# The two upstream derivations are imported, never edited.  Importing them keeps
# the adopted table provably identical to the two decisions that were compared.
from calibrate_global_turn_angle import (  # noqa: E402
    GLOBAL_TURN_ANGLE_SD_RAD,
    TAUTE_DOI,
    TAUTE_MEAN_TURN_ANGLE_DEG,
    TAUTE_PMID,
    TAUTE_TURN_COUNT,
    global_turn_angle_table_path,
)
from common import (  # noqa: E402
    GROGNOT_STALL_FREQUENCY_RATIO,
    GROGNOT_STALL_FREQUENCY_RATIO_SD,
    PHENOTYPES,
    current_stall_values,
    grognot_exponent,
    mean_hooks,
    variant_table,
    variants,
)

# The corrected dynamics decide which parameters still exist.  Importing the
# retired set from there means the table can never keep a column the model has
# dropped.
from salmonella_motility_corrected.io import RETIRED_COLUMNS  # noqa: E402

#: Key of the adopted variant inside the stall-parameter comparison grid.
ADOPTED_VARIANT_KEY = "G_grognot_probability"

PROCESSED = PROJECT / "data/processed/motility_adopted_parameters"
ADOPTED_TABLE = PROCESSED / "motility_summary_parameters_adopted.csv"
CHECKSUM = PROCESSED / "motility_summary_parameters_adopted.sha256"
AUDIT = PROCESSED / "adopted_stall_parameter_audit.csv"
RECORD = Path(__file__).resolve().parent / "metadata/derivation.json"

GROGNOT_CITATION = (
    "Grognot M, Nam JW, Elson LE, Taute KM (2023) Proc Natl Acad Sci USA "
    "120:e2301873120, doi:10.1073/pnas.2301873120, PMID 37579142"
)

#: The adopted stall probability must fall with flagella number.  A violation
#: means the hook table or the exponent changed sign, not that the model moved.
MONOTONE_ATOL = 1e-12
#: The extreme-strain probability ratio must reproduce the published 1.7.
RATIO_ATOL = 1e-9


def adopted_variant():
    """Return the adopted variant record from the comparison grid.

    Example:
        >>> adopted_variant().key
        'G_grognot_probability'
    """
    for variant in variants():
        if variant.key == ADOPTED_VARIANT_KEY:
            return variant
    raise ValueError(f"variant {ADOPTED_VARIANT_KEY} is not in the comparison grid")


def derive_adopted_table() -> pd.DataFrame:
    """Return the adopted parameter table, derived from the frozen inputs.

    The global-turn-angle table is derived first, so the caller never depends on
    a stale file.  Variant G then replaces the two stall columns of the three
    agarose rows and leaves everything else untouched.

    ``reorientation_duration_s`` is dropped.  The corrected dynamics reorient
    instantaneously, so the model has no such parameter; see
    ``models/motility_simulation/corrected/README.md``.  Dropping the column
    rather than zeroing it means a stale reader fails loudly instead of
    simulating a dwell nobody fitted.
    """
    global_turn_angle_table_path()
    table = variant_table(adopted_variant())
    table = table.drop(columns=list(RETIRED_COLUMNS.intersection(table.columns)))
    _check(table)
    return table


def _check(table: pd.DataFrame) -> None:
    """Assert the properties the adoption decision rests on.

    Values are never compared against typed-in numbers.  Only the relations the
    decision asserts are checked, so a change in the hook data or in the frozen
    delivered table propagates instead of tripping an assertion.
    """
    liquid = table.query("medium == 'liquid'")
    if not np.allclose(liquid.stall_probability, 0.0):
        raise AssertionError("A liquid row carries a non-zero stall probability.")

    agarose = table.query("medium == 'agarose'").set_index("phenotype")
    hooks = mean_hooks()
    ordered = sorted(PHENOTYPES, key=lambda name: hooks[name])
    probabilities = [float(agarose.loc[name, "stall_probability"]) for name in ordered]
    if any(
        later - earlier > MONOTONE_ATOL
        for earlier, later in zip(probabilities[:-1], probabilities[1:], strict=True)
    ):
        raise AssertionError(
            "The adopted stall probability does not fall with flagella number: "
            f"{dict(zip(ordered, probabilities, strict=True))}"
        )

    ratio = probabilities[0] / probabilities[-1]
    if abs(ratio - GROGNOT_STALL_FREQUENCY_RATIO) > RATIO_ATOL:
        raise AssertionError(
            f"The extreme-strain probability ratio is {ratio:.6f}, not the published "
            f"{GROGNOT_STALL_FREQUENCY_RATIO}."
        )

    durations = agarose.stall_mean_duration_s.to_numpy(dtype=float)
    if not np.allclose(durations, durations[0]):
        raise AssertionError(f"The adopted stall duration is not global: {durations}.")

    widths = table.turn_angle_sd_rad.to_numpy(dtype=float)
    if not np.allclose(widths, GLOBAL_TURN_ANGLE_SD_RAD):
        raise AssertionError("The adopted table does not carry the global turn width.")

    retired = RETIRED_COLUMNS.intersection(table.columns)
    if retired:
        raise AssertionError(
            f"The adopted table still carries retired parameters: {sorted(retired)}."
        )


def adopted_stall_parameters() -> dict[str, dict[str, float]]:
    """Return the adopted agarose stall values per strain, for reporting.

    Example:
        >>> values = adopted_stall_parameters()
        >>> values["PproA"]["stall_probability"] > values["PproB"]["stall_probability"]
        True
    """
    agarose = derive_adopted_table().query("medium == 'agarose'").set_index("phenotype")
    return {
        name: {
            "mean_hooks": mean_hooks()[name],
            "stall_probability": float(agarose.loc[name, "stall_probability"]),
            "stall_mean_duration_s": float(agarose.loc[name, "stall_mean_duration_s"]),
        }
        for name in PHENOTYPES
    }


def _artifact(path: Path) -> dict[str, object]:
    item: dict[str, object] = {
        "relative_path": path.relative_to(PROJECT).as_posix(),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
    }
    if path.suffix == ".csv":
        item["rows"] = max(0, sum(1 for _ in path.open(encoding="utf-8")) - 1)
    return item


def write_adopted_table() -> pd.DataFrame:
    """Derive, write and checksum the adopted table plus its derivation record."""
    table = derive_adopted_table()
    PROCESSED.mkdir(parents=True, exist_ok=True)
    table.to_csv(ADOPTED_TABLE, index=False)
    digest = hashlib.sha256(ADOPTED_TABLE.read_bytes()).hexdigest()
    CHECKSUM.write_text(f"{digest}  {ADOPTED_TABLE.name}\n", encoding="utf-8")

    previous_probability, previous_duration = current_stall_values()
    adopted = adopted_stall_parameters()
    audit = pd.DataFrame(
        [
            {
                "phenotype": name,
                "mean_hooks": adopted[name]["mean_hooks"],
                "turn_angle_stage_stall_probability": previous_probability[name],
                "adopted_stall_probability": adopted[name]["stall_probability"],
                "turn_angle_stage_stall_mean_duration_s": previous_duration[name],
                "adopted_stall_mean_duration_s": adopted[name]["stall_mean_duration_s"],
            }
            for name in PHENOTYPES
        ]
    )
    audit.to_csv(AUDIT, index=False)

    exponent = grognot_exponent()
    hooks = mean_hooks()
    record = {
        "schema_version": "1.0.0",
        "record_type": "derived_parameter_calibration",
        "record_id": "motility_adopted_parameters",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "command": [
            ".venv/bin/python3.12",
            "analyses/motility_adopted_parameters/derive_adopted_parameters.py",
        ],
        "inputs": [
            _artifact(Path(__file__).resolve()),
            _artifact(
                PROJECT / "analyses/motility_turn_angle_comparison/calibrate_global_turn_angle.py"
            ),
            _artifact(PROJECT / "analyses/motility_stall_parameter_comparison/common.py"),
            _artifact(global_turn_angle_table_path()),
            _artifact(PROJECT / "data/processed/figure_07_revision/hook_count_per_cell.csv"),
        ],
        "outputs": [_artifact(ADOPTED_TABLE), _artifact(CHECKSUM), _artifact(AUDIT)],
        "software": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "parameters": {
            "adopted_variant": ADOPTED_VARIANT_KEY,
            "global_turn_angle_sd_rad": GLOBAL_TURN_ANGLE_SD_RAD,
            "global_turn_angle_sd_deg": math.degrees(GLOBAL_TURN_ANGLE_SD_RAD),
            "turn_angle_anchor": (
                "Taute KM, Gude S, Tans SJ, Shimizu TS (2015) Nat Commun 6:8776, "
                f"doi:{TAUTE_DOI}, PMID {TAUTE_PMID}; mean turn angle "
                f"{TAUTE_MEAN_TURN_ANGLE_DEG:.0f} deg over {TAUTE_TURN_COUNT} turns"
            ),
            "stall_probability_exponent": exponent,
            "stall_probability_relation": "p_s = p_mean * N_s^-a / mean_s(N_s^-a)",
            "stall_frequency_ratio_anchor": GROGNOT_STALL_FREQUENCY_RATIO,
            "stall_frequency_ratio_anchor_sd": GROGNOT_STALL_FREQUENCY_RATIO_SD,
            "stall_anchor_source": GROGNOT_CITATION,
            "mean_hooks_per_cell": hooks,
            "adopted_stall_parameters": adopted,
        },
        "random_seeds": {},
        "findings": [
            (
                "One table now carries both adopted decisions. Every manuscript panel that "
                "runs the active-particle simulation reads this file through "
                "adopted_parameter_table_path()."
            ),
            (
                f"The stall probability falls as N^-{exponent:.3f}, so the least flagellated "
                f"strain stalls {GROGNOT_STALL_FREQUENCY_RATIO} times more often per contact "
                "than the most flagellated one. The mean over the three strains is unchanged "
                "against the turn-angle stage, so the adoption redistributes the effect "
                "rather than enlarging it."
            ),
            (
                "The stall mean duration is one global value in the three agarose rows. "
                "Grognot et al. found the duration effect significant only at 0.16 % agar, "
                "not at the 0.25 % that matches our condition."
            ),
        ],
        "limitations": [
            (
                "Grognot et al. varied a second flagellar system in Vibrio alginolyticus, not "
                "the flagella count in Salmonella. Mapping the 1.7 ratio onto our mean hook "
                "numbers is an assumption made here, not a measurement. It fixes the ratio "
                "between the extreme strains; the power-law form is a choice."
            ),
            (
                "The absolute stall probability has no source. Only the ratio between strains "
                "is anchored. The absolute stall duration also has no source; it stays at the "
                "mean of the three delivered values and is reported as nominal."
            ),
            (
                "The model draws an exponential stall duration. Published gel trapping times "
                "are power-law distributed, so an anchored mean would fix the mean and "
                "nothing else."
            ),
            (
                "The persistence calibration sets the model persistence time to the measured "
                "mean, so the two turning rates remain fitted quantities with no independent "
                "physical meaning."
            ),
        ],
    }
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    RECORD.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return table


def adopted_parameter_table_path(*, force: bool = False) -> Path:
    """Return the adopted table, deriving it first if it is missing.

    This is the single canonical accessor.  Every builder that runs the
    active-particle simulation for a manuscript panel calls it.
    """
    if force or not ADOPTED_TABLE.exists():
        write_adopted_table()
    return ADOPTED_TABLE


def main() -> None:
    write_adopted_table()
    exponent = grognot_exponent()
    hooks = mean_hooks()
    print(
        f"turn width      {GLOBAL_TURN_ANGLE_SD_RAD:.6f} rad "
        f"({math.degrees(GLOBAL_TURN_ANGLE_SD_RAD):.2f} deg), all six rows"
    )
    print(
        f"stall exponent  a = {exponent:.6f}, from the "
        f"{GROGNOT_STALL_FREQUENCY_RATIO} +/- {GROGNOT_STALL_FREQUENCY_RATIO_SD} "
        "stall-frequency ratio of Grognot et al. 2023"
    )
    print()
    audit = pd.read_csv(AUDIT)
    audit.insert(2, "mean_hooks_check", [hooks[name] for name in audit.phenotype])
    with pd.option_context("display.width", 220, "display.precision", 4):
        print(audit.drop(columns="mean_hooks_check").to_string(index=False))
    print(f"\nadopted table: {ADOPTED_TABLE.relative_to(PROJECT)}")


if __name__ == "__main__":
    main()
