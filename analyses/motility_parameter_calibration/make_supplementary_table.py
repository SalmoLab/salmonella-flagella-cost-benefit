#!/usr/bin/env python3
"""Emit Supplementary Table X: every motility-simulation parameter and its source.

The table states, for each of the eight per-strain model parameters and each of
the four global noise constants, whether the value is measured in this study,
fitted to our measurements, taken from the literature, scaled to a published
ratio, or a nominal value of the published simulation code.  The per-strain rows
are generated from the adopted parameter file and the noise constants from the
config and the model, so the table cannot drift from the numbers the figures use.

The four noise constants are listed because they change the physics and none of
them has a source.  They appeared in no table before this revision.

Figure 5D, Figure 5E, Supplementary Figure 4 and the time-step convergence
ladder all read that one file through ``adopted_parameter_table_path()``.  Two
decisions shape it.  ``turn_angle_sd_rad`` is one value for all six rows,
anchored to Taute et al. 2015; see
``docs/revision_2026-08-12/turn_angle_model_comparison.md``.  The agarose
``stall_probability`` falls with flagella number at the strength Grognot et al.
2023 measured, and ``stall_mean_duration_s`` is one global value; see
``docs/revision_2026-08-12/stall_parameter_comparison.md``.

Sources are recorded in ``docs/revision_2026-08-12/motility_parameter_sources.md``.

Setup:
    PYTHONPATH=$PWD/src .venv/bin/python \
        analyses/motility_parameter_calibration/make_supplementary_table.py

Outputs two files under ``docs/revision_2026-08-12/``: a CSV for typesetting and
a markdown rendering for review.  Complexity is O(rows); it runs instantly.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "analyses/motility_turn_angle_comparison"))
sys.path.insert(0, str(PROJECT / "analyses/motility_stall_parameter_comparison"))
sys.path.insert(0, str(PROJECT / "analyses/motility_adopted_parameters"))
sys.path.insert(0, str(PROJECT / "models/motility_simulation/corrected/src"))

from calibrate_global_turn_angle import (  # noqa: E402
    TAUTE_DOI,
    TAUTE_MEAN_TURN_ANGLE_DEG,
    TAUTE_PMID,
    TAUTE_TURN_COUNT,
)
from common import (  # noqa: E402
    GROGNOT_STALL_FREQUENCY_RATIO,
    GROGNOT_STALL_FREQUENCY_RATIO_SD,
    grognot_exponent,
    mean_hooks,
)
import yaml  # noqa: E402

from derive_adopted_parameters import (  # noqa: E402
    adopted_parameter_table_path,
)
from salmonella_motility_corrected import STALL_TRANSLATIONAL_SCALE  # noqa: E402

#: The upstream config the corrected model reads its noise scales from.  It is
#: immutable provenance; the builders override values in memory, never in place.
SIMULATION_CONFIG = PROJECT / "models/motility_simulation/upstream/data/config.yml"

#: The parameter file the manuscript panels read.  Derived, never hand-edited.
CALIBRATED = adopted_parameter_table_path()

#: Exponent and hook numbers behind the stall-probability scaling.  Both are
#: derived, so a change in the hook data reaches this table without an edit.
STALL_EXPONENT = grognot_exponent()
MEAN_HOOKS = mean_hooks()
OUT_DIR = PROJECT / "docs/revision_2026-08-12"
CSV_OUT = OUT_DIR / "supplementary_table_X_motility_parameters.csv"
MD_OUT = OUT_DIR / "supplementary_table_X_motility_parameters.md"

STRAINS = ["PproA", "WT", "PproB"]
MEDIA = ["liquid", "agarose"]

#: Measured mean tumble duration of E. coli, Taute et al. 2015. Reported for
#: comparison only; the simulation keeps the nominal 0.05 s of the published code.
MEASURED_TUMBLE_DURATION_S = 0.19

#: parameter -> (printed symbol, unit, source class, note)
#: Source classes are the three states the methods paragraph uses.
PARAMETERS: dict[str, tuple[str, str, str, str]] = {
    "motile_fraction": (
        "f_motile",
        "-",
        "Measured",
        "Per-strain, per-medium fraction of swimming cells (this study).",
    ),
    "run_speed_um_s": (
        "v",
        "um s^-1",
        "Measured",
        "Per-strain, per-medium mean run speed (this study).",
    ),
    "rotational_diffusion_rad2_s": (
        "D_theta",
        "rad^2 s^-1",
        "Fitted",
        "Effective heading-decorrelation rate during runs. Not the rotational "
        "diffusion of the cell body, which is 0.057 rad^2 s^-1 for swimming "
        "E. coli (Drescher et al., 2011).",
    ),
    "reorientation_rate_s": (
        "lambda",
        "s^-1",
        "Fitted",
        "Scaled with D_theta by one factor so the model persistence time equals "
        "the measured one; the delivered ratio is kept.",
    ),
    "turn_angle_sd_rad": (
        "sigma",
        "rad",
        "Literature",
        "One global value for all six rows. Set so the mean turn magnitude "
        f"sigma * sqrt(2 / pi) equals the {TAUTE_MEAN_TURN_ANGLE_DEG:.0f} deg mean turn "
        f"angle of Taute et al., 2015 (n = {TAUTE_TURN_COUNT} turns, E. coli AW405; "
        f"doi:{TAUTE_DOI}, PMID {TAUTE_PMID}). Taute et al. tracked in three dimensions; "
        "this simulator is two-dimensional, so only the mean magnitude is matched, not "
        "the forward-skewed shape of the measured distribution.",
    ),
    "passive_diffusion_um2_s": (
        "D_t",
        "um^2 s^-1",
        "Nominal",
        "Nominal value of the published code. Agrees within 3 % with the "
        "Stokes-Einstein value for a 2.0 x 0.8 um cell at 20 degC.",
    ),
    "stall_probability": (
        "p_stall",
        "-",
        "Literature-scaled",
        "Per-contact-event probability: the chance that one encounter with one "
        "obstacle ends in a stall rather than a tangential slide. It is drawn once, "
        "on the step where the cell first overlaps a disk it was not already "
        "touching, so the value is a property of the model and not of the time step. "
        "This is the same quantity Grognot et al. measured, a stall frequency per "
        "contact. No primary measurement gives its absolute value. Its ratio "
        "between strains is anchored: it falls with the mean hook number per cell "
        f"as N^-{STALL_EXPONENT:.3f} (PproA {MEAN_HOOKS['PproA']:.3f}, "
        f"WT {MEAN_HOOKS['WT']:.3f}, PproB {MEAN_HOOKS['PproB']:.3f}), normalised so "
        "the mean over the three strains is unchanged. The exponent sets the ratio "
        "between the least and the most flagellated strain to the "
        f"{GROGNOT_STALL_FREQUENCY_RATIO} +/- {GROGNOT_STALL_FREQUENCY_RATIO_SD} "
        "stall-frequency ratio measured in 0.25 % agar by Grognot et al., 2023 "
        "(doi:10.1073/pnas.2301873120, PMID 37579142). That study varied a second "
        "flagellar system in Vibrio alginolyticus, not the flagella count, so the "
        "mapping onto our hook numbers is an assumption. Zero in liquid.",
    ),
    "stall_mean_duration_s": (
        "t_stall",
        "s",
        "Nominal",
        "One global value for the three agarose rows. Grognot et al., 2023 found "
        "the flagella effect on stall duration significant only at 0.16 % agar, not "
        "at the 0.25 % that matches our condition, so a per-strain duration is not "
        "supported and one value is what the evidence carries. The absolute value "
        "has no source. Reported trapping times in gels span 0.4 to 40 s "
        "(Bhattacharjee and Datta, 2019) and average 2.1 to 3.6 s (Datta et al., "
        "2025), so this value sits below the published means. Those distributions "
        "are power-law; the model draws an exponential. The liquid rows keep the "
        "nominal 0.05 s of the published code, which never fires because their "
        "stall probability is zero.",
    ),
}


#: Global noise constants of the corrected model: one value for all six rows.
#:
#: These four numbers change the physics and none of them has a source.  They
#: were absent from every table until this revision, which is why they are listed
#: here rather than left in a config file.  Each entry is
#: ``key -> (symbol, unit, note)``; the value is read from the config or from the
#: model constant, never typed in, so the table cannot drift from the code.
NOISE_CONSTANTS: dict[str, tuple[str, str, str]] = {
    "run_translational_scale": (
        "c_run",
        "-",
        "Global model constant, one value for all six rows. It multiplies the "
        "passive diffusion coefficient D_t to set the translational noise of a "
        "cell that is running. It has no source: it is a default of the published "
        "code and no measurement in this study or in the literature sets it.",
    ),
    "stall_translational_scale": (
        "c_stall",
        "-",
        "Global model constant, one value for all six rows. It multiplies D_t to "
        "set the translational noise of a cell that is stalled against an "
        "obstacle. It has no source. Until this revision it was written as a bare "
        "number inside the integration loop, so it appeared in no config file and "
        "no table; it now carries the config key noise.stall_translational_scale.",
    ),
    "stall_slide_fraction": (
        "c_slide",
        "-",
        "Global model constant, one value for all six rows. When a cell meets an "
        "obstacle and does not stall, it keeps this fraction of the tangential "
        "part of its step and slides along the surface. It has no source.",
    ),
    "stall_rotational_diffusion_scale": (
        "c_rot",
        "-",
        "Global model constant, one value for all six rows. It multiplies the "
        "rotational diffusion rate D_theta while a cell is stalled, so a stalled "
        "cell reorients faster than a running one. It has no source.",
    ),
}


def noise_constant_values() -> dict[str, float]:
    """Return the four global noise scales the corrected model actually applies.

    Three are read from the upstream config.  The fourth, the stalled-cell
    translational scale, is the model constant: the upstream config is immutable
    provenance and does not carry the key, so the builders inject it and the
    default lives in the code.

    Example:
        >>> values = noise_constant_values()
        >>> values["stall_translational_scale"]
        0.2
    """
    noise = yaml.safe_load(SIMULATION_CONFIG.read_text(encoding="utf-8"))["noise"]
    return {
        "run_translational_scale": float(noise["run_translational_scale"]),
        "stall_translational_scale": float(STALL_TRANSLATIONAL_SCALE),
        "stall_slide_fraction": float(noise["stall_slide_fraction"]),
        "stall_rotational_diffusion_scale": float(noise["stall_rotational_diffusion_scale"]),
    }


def _significant(value: float) -> str:
    """Format a parameter value at three significant digits, without trailing noise."""
    if value == 0:
        return "0"
    return f"{value:.3g}"


def build_table() -> pd.DataFrame:
    """Return one row per parameter and one value column per strain-medium pair."""
    calibrated = pd.read_csv(CALIBRATED)
    calibrated = calibrated[calibrated.phenotype != "WT_slow"]
    indexed = calibrated.set_index(["phenotype", "medium"])

    rows: list[dict[str, str]] = []
    for column, (symbol, unit, source, note) in PARAMETERS.items():
        row: dict[str, str] = {"Parameter": column, "Symbol": symbol, "Unit": unit}
        for medium in MEDIA:
            for strain in STRAINS:
                row[f"{strain} ({medium})"] = _significant(
                    float(indexed.loc[(strain, medium), column])
                )
        row["Source"] = source
        row["Note"] = note
        rows.append(row)

    # The global noise constants close the table.  They take the same value in
    # every column because the model applies one value to every strain and medium.
    values = noise_constant_values()
    for column, (symbol, unit, note) in NOISE_CONSTANTS.items():
        row = {"Parameter": column, "Symbol": symbol, "Unit": unit}
        for medium in MEDIA:
            for strain in STRAINS:
                row[f"{strain} ({medium})"] = _significant(values[column])
        row["Source"] = "Nominal"
        row["Note"] = note
        rows.append(row)
    return pd.DataFrame(rows)


def persistence_times(frame: pd.DataFrame) -> pd.DataFrame:
    """Return the derived persistence time, which is not an independent parameter."""
    calibrated = pd.read_csv(CALIBRATED)
    calibrated = calibrated[calibrated.phenotype != "WT_slow"].copy()
    calibrated["tau_s"] = 1.0 / (
        calibrated.rotational_diffusion_rad2_s
        + calibrated.reorientation_rate_s
        * (1.0 - np.exp(-(calibrated.turn_angle_sd_rad**2) / 2.0))
    )
    return calibrated[["phenotype", "medium", "tau_s"]]


def reorient_duty_cycle(duration_s: float) -> tuple[float, float]:
    """Return the time fraction a cell would lose to a reorientation of ``duration_s``.

    The corrected model reorients instantaneously, so its duty cycle is zero and
    ``reorientation_duration_s`` is not a parameter.  This function answers the
    counterfactual the methods still have to address: what a measured tumble
    duration would cost if it were substituted without refitting.  A cell turns
    as a Poisson process of rate ``lambda`` and each turn would last
    ``duration_s``, so the lost fraction is ``d / (1 / lambda + d)``.

    Example:
        >>> low, high = reorient_duty_cycle(0.19)
        >>> 0.0 < low <= high < 1.0
        True
    """
    calibrated = pd.read_csv(CALIBRATED)
    calibrated = calibrated[calibrated.phenotype != "WT_slow"]
    duty = duration_s / (1.0 / calibrated.reorientation_rate_s + duration_s)
    return float(duty.min()), float(duty.max())


#: The convergence ladder and the built panel summary.  The integration note is
#: read from these, never typed in, so the table cannot drift from the figures.
CONVERGENCE = PROJECT / "build/diagnostics/Figure_5/timestep_convergence.csv"
PANEL_SUMMARY = (
    PROJECT / "data/processed/figure_05_revision/active_particle_100_seed_summary.csv"
)


def integration_note() -> str:
    """Return the integration sentence, derived from the rebuilt panel and ladder.

    Reading the built artefacts means the stated step is the step the panels
    actually ran, and the stated tolerance result is the one the ladder actually
    measured.
    """
    if not (CONVERGENCE.exists() and PANEL_SUMMARY.exists()):
        return (
            "Time step and convergence result are written here from "
            "build/diagnostics/Figure_5/timestep_convergence.csv once the panels are built."
        )
    panels = pd.read_csv(PANEL_SUMMARY)
    ladder = pd.read_csv(CONVERGENCE)
    panel_dt = float(panels.dt_s.iloc[0])
    accepted = float(ladder.selected_dt_s.iloc[0])
    tolerance = float(ladder.tolerance.iloc[0])
    reference = str(ladder.reference_dt_s.iloc[0])
    at_panel = ladder.query("dt_s == @panel_dt").net_displacement_um_rel_deviation
    width = float(panels.box_width_um.iloc[0])
    height = float(panels.box_height_um.iloc[0])
    agarose = panels.query("medium == 'agarose'")
    area_fraction = float(agarose.obstacle_area_fraction.mean())
    return (
        f"Time step {panel_dt:g} s. A {panels.groupby(['phenotype', 'medium']).size().max()}-seed "
        f"convergence test accepts every step whose group mean net displacement stays within "
        f"{tolerance:.0%} of the mean of the two finest steps tested, {reference} s. The largest "
        f"accepted step is {accepted:g} s; the panels run at {panel_dt:g} s, which is finer and "
        f"therefore inside the tolerance, where the largest group deviation is "
        f"{at_panel.max():.1%}. The stall probability is drawn once per contact event, so stall "
        f"occupancy converges with the step. Contour path length does not converge at all and is "
        f"not reported. The quantitative panels run in a {width:g} x {height:g} um box, enlarged "
        f"so the reflecting walls do not compress the strain ratios; the obstacle count scales "
        f"with box area and the realised obstacle area fraction is {area_fraction:.3f}."
    )


def main() -> None:
    table = build_table()
    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(CSV_OUT, index=False)

    tau = persistence_times(table).set_index(["phenotype", "medium"])
    tau_line = "; ".join(
        f"{strain} {medium} {tau.loc[(strain, medium), 'tau_s']:.3f}"
        for medium in MEDIA
        for strain in STRAINS
    )

    value_columns = [c for c in table.columns if "(" in c]
    header = ["Parameter", "Symbol", "Unit", *value_columns, "Source"]
    lines = [
        "# Supplementary Table X. Parameters of the active-particle motility simulation",
        "",
        "Every parameter carries one of five sources. **Measured** values come",
        "from the paired experimental units of this study. **Fitted** values are",
        "scaled so the model persistence time equals the measured persistence",
        "time. **Literature** values are taken from a published measurement in",
        "another organism. **Literature-scaled** values have no published",
        "absolute value; only their ratio between strains is set by a published",
        "measurement. **Nominal** values are defaults of the published",
        "simulation code and are not derived from our data.",
        "",
        "| " + " | ".join(header) + " |",
        "|" + "|".join(["---"] * len(header)) + "|",
    ]
    for _, row in table.iterrows():
        lines.append("| " + " | ".join(str(row[c]) for c in header) + " |")

    lines += [
        "",
        "## Notes",
        "",
    ]
    for _, row in table.iterrows():
        lines.append(f"- **{row['Parameter']}** ({row['Source']}). {row['Note']}")

    measured_low, measured_high = reorient_duty_cycle(MEASURED_TUMBLE_DURATION_S)
    lines += [
        "",
        f"- **Derived persistence time** tau (s), not an independent parameter: {tau_line}.",
        "  tau = 1 / (D_theta + lambda * (1 - exp(-sigma^2 / 2))).",
        "- **Reorientation is instantaneous.** The persistence relation above carries no",
        "  duration term, so a reorientation dwell would simulate a different model from the",
        "  one the parameters are fitted to. The corrected dynamics apply the heading kick at",
        "  the transition and the cell keeps swimming, so `reorientation_duration_s` is not a",
        "  parameter of the model and no longer appears in this table. The measured tumble",
        f"  duration of *E. coli*, {MEASURED_TUMBLE_DURATION_S} s (Taute et al., 2015), cannot "
        "simply be substituted: at",
        f"  the fitted reorientation rates it would put cells in a non-swimming state "
        f"{measured_low * 100:.0f} % to {measured_high * 100:.0f} %",
        "  of the time and remove most directed motion. A model with a real tumble duration",
        "  needs the persistence relation refitted with a duration term.",
        "- **The four noise constants have no source.** They are defaults of the published",
        "  code. They are listed here because they change the physics, and because they were",
        "  absent from every table before this revision. They also order translational noise",
        "  the wrong way round: a running cell gets 0.12 of the passive diffusion",
        "  coefficient, a stalled cell 0.20 and a non-motile cell 1.00, so a swimming cell",
        "  diffuses about eight times less than a stopped one. The size of that defect was",
        "  measured against a physically ordered alternative in which every state diffuses at",
        "  the full passive rate, 100 seeds per group, paired by seed. The plotted observable",
        "  barely moves: net displacement changes by at most 3.5 % (WT agarose, 95 % CI",
        "  [-7.1, +0.2] %), and no agarose interval excludes zero. Effective diffusivity in",
        "  agarose moves more, by -6.2 % (PproB, 95 % CI [-8.0, -4.5] %), because larger",
        "  translational noise drives cells into obstacles more often and raises the stall",
        "  occupancy. The constants are therefore declared and kept, not changed; the agarose",
        "  effective-diffusivity sensitivity is stated as a limitation. See",
        "  `motility_parameter_sources.md` for the full measurement.",
        f"- **Integration.** {integration_note()}",
        "- Full bibliographic records are in `motility_parameter_sources.md`.",
        "",
    ]
    MD_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {CSV_OUT.relative_to(PROJECT)}")
    print(f"wrote {MD_OUT.relative_to(PROJECT)}")


if __name__ == "__main__":
    main()
