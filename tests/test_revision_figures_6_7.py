from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).parents[1]


def _load(name: str, relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


FIG6 = _load("figure_06_revision_builder", "analyses/figure_06_revision/build_figure_06_revision.py")
FIG7 = _load("figure_07_revision_builder", "analyses/figure_07_revision/build_figure_07_revision.py")


def test_figure_6_numerical_audit_and_scale_bar_blocker() -> None:
    a = FIG6.panel_a(check_only=True)
    b = FIG6.panel_b(check_only=True)
    c = FIG6.panel_c(check_only=True)
    d = FIG6.panel_d(check_only=True)
    e = FIG6.panel_e(check_only=True)
    assert a == {"days": 26, "conditions": 7}
    assert b == {"points": 30, "pairs_per_comparison": 6}
    assert c["cells"] == 771
    np.testing.assert_allclose(
        [c["means"][name] for name in ["Center", "Middle", "Out"]],
        [0.4396887159533074, 2.657587548638132, 3.9221789883268483],
        atol=1e-12,
    )
    assert d["source_sha256"] == FIG6.EXPECTED_SHA256["competition_scheme_source.pptx"]
    assert np.isclose(e["r1_pproa_fraction"], 4392 / 4817, atol=1e-12)
    assert np.isclose(e["r4_pprob_mean_hooks"], 5.810344827586207, atol=1e-12)
    source = Path(FIG6.__file__).read_text(encoding="utf-8")
    assert "Calibrated microscopy\\nfield required" in source
    assert "scale not inferred" in source
    assert "significance" not in source.lower()


def test_figure_7_direct_pair_counts_and_continuous_axis() -> None:
    expected = {
        "A": {"agarose": 18, "liquid": 16},
        "B": {"agarose": 18, "liquid": 18},
        "C": {"agarose": 18, "liquid": 16},
    }
    for panel, counts in expected.items():
        result = FIG7.panels_a_to_c(panel, check_only=True)
        assert result["unit_counts"] == counts
        direct = FIG7.load_direct_tracks(panel)
        assert set(direct.phenotype) == set(FIG7.PANEL_SPECS[panel]["phenotypes"])
        assert direct.log10_diffusivity.min() < 0 < direct.log10_diffusivity.max()
        one = direct[(direct.medium == "agarose") & (direct.phenotype == FIG7.PANEL_SPECS[panel]["phenotypes"][0])]
        _, _, density, thresholds = FIG7.hdr_levels(one.speed_um_s.to_numpy(), one.log10_diffusivity.to_numpy())
        enclosed = [density[density >= threshold].sum() / density.sum() for threshold in thresholds[::-1]]
        np.testing.assert_allclose(enclosed, FIG7.CONTOUR_MASSES, atol=0.015)
    source = Path(FIG7.__file__).read_text(encoding="utf-8")
    assert "ax.axhline(0" in source
    assert "CONTOUR_MASSES = (0.50, 0.80, 0.95)" in source


def test_figure_7_effective_diffusivity_decomposition() -> None:
    check = FIG7.panel_d(check_only=True)
    assert check["rows"] == 6
    assert check["max_closure_error"] < 1e-12

    rng = np.random.default_rng(FIG7.BOOTSTRAP_SEED)
    results = []
    for panel, spec in FIG7.PANEL_SPECS.items():
        direct = FIG7.load_direct_tracks(panel)
        direct["ln_D"] = np.log(direct.diffcoeff_cve_mean)
        direct["two_ln_speed"] = 2 * np.log(direct.meanspeed)
        direct["ln_tau"] = direct.ln_D - direct.two_ln_speed + np.log(2.0)
        units = direct.groupby(["metadata_key", "medium", "phenotype"], as_index=False).agg(
            ln_D=("ln_D", "mean"),
            two_ln_speed=("two_ln_speed", "mean"),
            ln_tau=("ln_tau", "mean"),
        )
        numerator, denominator = spec["contrast"]
        wide = units.pivot(index=["metadata_key", "medium"], columns="phenotype", values=["ln_D", "two_ln_speed", "ln_tau"])
        for medium in ["agarose", "liquid"]:
            one = wide.xs(medium, level="medium")
            contrasts = pd.DataFrame(
                {
                    "delta_ln_D": one["ln_D", numerator] - one["ln_D", denominator],
                    "delta_two_ln_speed": one["two_ln_speed", numerator] - one["two_ln_speed", denominator],
                    "delta_ln_tau": one["ln_tau", numerator] - one["ln_tau", denominator],
                }
            )
            results.append(FIG7.bootstrap_decomposition(contrasts, rng))
    expected_d = [0.311947, 0.369662, 1.650999, 1.476675, 4.099618, 3.102411]
    np.testing.assert_allclose([row["D_ratio"] for row in results], expected_d, atol=1e-6)
    assert all(abs(row["closure_error"]) < 1e-12 for row in results)


def test_figure_7_hook_counts_are_six_day_distributions() -> None:
    expected = {
        "E": {"WT": 2931, "PproA": 3524},
        "F": {"WT": 4018, "PproB": 4918},
        "G": {"PproA": 7904, "PproB": 6494},
    }
    for panel, counts in expected.items():
        result = FIG7.hook_panel(panel, check_only=True)
        assert result["cell_counts"] == counts
        assert set(result["repeat_counts"].values()) == {6}


def test_revision_panel_provenance_has_unique_runnable_commands() -> None:
    for figure, labels in [(6, "ABCDE"), (7, "ABCDEFG")]:
        for label in labels:
            path = ROOT / f"analyses/figure_0{figure}_revision/panel_{label.lower()}/metadata/provenance.json"
            document = json.loads(path.read_text(encoding="utf-8"))
            assert document["panel_id"] == f"F{figure}_{label}"
            assert document["command"][-2:] == ["--panel", label]
            assert all(not item["relative_path"].startswith("/") for item in document["inputs"])
