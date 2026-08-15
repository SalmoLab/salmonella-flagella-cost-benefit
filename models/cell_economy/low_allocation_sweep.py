#!/usr/bin/env python3
"""A3 harness for the 0–1% dynamic-model solver-domain sweep.

Four modes:

``--remote``
    The collaborator's route. GEKKO sends the model to the public APMonitor
    server, which solves it with IPOPT (solver 3). This mode reproduces the
    delivered dynamic tables at 1–5% flagellar allocation to 1e-9 relative
    error, so it is the canonical A3 mode. It needs network access.
``--continuation``
    The same remote route, plus a warm-start continuation and a multi-start.
    Each allocation is solved three ways: from the model's own cold initial
    guess, from the accepted solution of the neighbour below, and from the
    accepted solution of the neighbour above. The best objective wins. Only
    the initial guess changes; every equation, bound and initial condition
    stays as the upstream model declares it. This mode also writes the full
    accepted trajectory per allocation, which the panel needs.
``--execute``
    Local, non-network attempt. Local GEKKO 1.3.2 has no solver 3 and its APOPT
    fallback fails on this model, so every step is recorded as failed.
``default``
    The historical blocked-status plan, kept so the pre-remote record is still
    reproducible. It invents no objective values.
"""

from __future__ import annotations

import argparse
import math
import re
import sys
import urllib.request
import uuid
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parents[2]
UPSTREAM = PROJECT / "models/cell_economy/upstream"
PARAMETERS = PROJECT / "data/external/cell_economy_results/sampling/kinetic_params_2026.csv"
TRACKED_OUTPUT = PROJECT / "data/processed/figure_05_revision/A3_low_allocation_solver_status.csv"
DEFAULT_OUTPUT = PROJECT / "build/statistics/Figure_5/A3/low_allocation_solver_status.csv"
STEADY_OUTPUT = PROJECT / "build/statistics/Figure_5/A3/low_allocation_steady_state.csv"
TRACKED_STEADY = PROJECT / "data/processed/figure_05_revision/A3_low_allocation_steady_state.csv"
CONTINUATION_OUTPUT = (
    PROJECT / "build/statistics/Figure_5/A3/low_allocation_continuation_status.csv"
)
TRACKED_CONTINUATION = (
    PROJECT / "data/processed/figure_05_revision/A3_low_allocation_continuation_status.csv"
)
ATTEMPT_OUTPUT = PROJECT / "build/statistics/Figure_5/A3/low_allocation_continuation_attempts.csv"
TRACKED_ATTEMPTS = (
    PROJECT / "data/processed/figure_05_revision/A3_low_allocation_continuation_attempts.csv"
)
TRAJECTORY_DIR = PROJECT / "data/processed/figure_05_revision/A3_trajectories"
ALLOCATIONS = np.round(np.arange(0.0, 0.0100001, 0.0005), 4)

# The anchor of the continuation. 1% is the highest allocation of the sweep, it
# converged on the first attempt, and it reproduces the delivered dynamic table
# ``dynamic_flag_0.010.csv`` to 1e-9 relative error.
CONTINUATION_ANCHOR = 0.01

# ``common.result`` multiplies the growth rate and the catalytic rates by 3.6
# before it returns the table. A warm start feeds values back into the solver,
# so these columns are divided by 3.6 again.
SCALED_COLUMNS = frozenset(
    {"mu", "v_tra", "v_cbn", "v_etc", "v_aab", "v_rib", "v_lpb", "v_fla", "v_ex_e", "v_ex_a"}
)

# ``time`` is the horizon. ``density`` and ``v_swimmax`` are parameters, not
# variables. ``slk_*`` are solver slacks that the model never declares.
NON_VARIABLE_COLUMNS = frozenset({"time", "density", "v_swimmax"})

# GEKKO 1.3.2 hardcodes ``http://byu.apmonitor.com``. That host no longer resolves
# (NXDOMAIN, checked 13 August 2026). The live public APMonitor server is below.
REMOTE_SERVER = "https://apmonitor.com"

# GEKKO 1.3.2 posts with the default urllib User-Agent. The CDN in front of
# apmonitor.com answers that agent with HTTP 403, so the client names itself.
# This is a truthful client identifier, not a browser string.
REMOTE_USER_AGENT = "GEKKO/1.3.2 (python-urllib)"


def sweep_plan() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "flagellar_allocation": ALLOCATIONS,
            "flagellar_allocation_percent": ALLOCATIONS * 100,
            "solver_requested": "APMonitor solver 3 (IPOPT)",
            "remote": False,
            "status": "blocked_exact_solver_unavailable",
            "objective_final_growth_rate_1h": np.nan,
            "final_distance_um": np.nan,
            "final_substrate_mM": np.nan,
            "message": (
                "Not executed: local GEKKO 1.3.2 lacks solver 3 and its APOPT fallback "
                "failed on the supplied model. Requires exact collaborator runtime."
            ),
        }
    )


def _model_inputs() -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    params = pd.read_csv(PARAMETERS, index_col=0)
    enzymes = ["Tra", "Cbn", "Etc", "Aab", "Rib", "Lpb", "Fla"]
    proteins = enzymes + ["Oth"]
    metabolites = ["cin", "cpre", "aa", "lip", "e"]
    membranes = ["cpm"]
    upper = pd.concat(
        [
            pd.Series([1e6, 1e6, 1e6, 1e6, 2e6, 1e6, 1e3, 5e7], index=proteins),
            pd.Series([1e5, 1e5, 1e5, 2e6, 1e6], index=metabolites),
            pd.Series([2e6], index=membranes),
        ]
    )
    return params.kcat, params.Km, params.hc, upper


def execute_sweep() -> pd.DataFrame:
    """Attempt every allocation with local, non-network GEKKO and record all failures."""
    sys.path.insert(0, str(UPSTREAM))
    from models.salmonella import dynamic, steadystate  # type: ignore[import-not-found]

    from models import common  # type: ignore[import-not-found]

    kcat, km, hill, upper = _model_inputs()
    time = np.concatenate([[0, 0.1], np.arange(0.5, 8.5, 0.5)])
    distance_initial = 8500
    gradient_age_seconds = 3 * 3600
    glucose_boundary_mM = 5.0
    glucose_initial = round(
        common.diffusion_model(
            distance_initial,
            gradient_age_seconds,
            600,
            glucose_boundary_mM,
        ),
        3,
    )
    rows: list[dict[str, float | str | bool]] = []
    for allocation in ALLOCATIONS:
        row: dict[str, float | str | bool] = {
            "flagellar_allocation": float(allocation),
            "flagellar_allocation_percent": float(allocation * 100),
            "solver_requested": "APMonitor solver 3 (IPOPT)",
            "remote": False,
            "status": "failed",
            "objective_final_growth_rate_1h": math.nan,
            "final_distance_um": math.nan,
            "final_substrate_mM": math.nan,
            "message": "",
        }
        try:
            steady = steadystate.simulate(
                time,
                glucose_initial,
                upper,
                float(allocation),
                kcat.copy(),
                km.copy(),
                hill.copy(),
                False,
            )
            concentrations = steady.c.apply(lambda value: round(value[1], 3))
            result = dynamic.simulate(
                time,
                gradient_age_seconds,
                distance_initial,
                glucose_boundary_mM,
                upper,
                float(allocation),
                kcat.copy(),
                km.copy(),
                hill.copy(),
                concentrations,
                False,
            )
            final = result.table.iloc[-1]
            row.update(
                {
                    "status": "success",
                    "objective_final_growth_rate_1h": float(final.mu),
                    "final_distance_um": float(final.distance),
                    "final_substrate_mM": float(final.cex),
                    "message": "local non-network solve completed",
                }
            )
        except Exception as error:  # solver libraries expose heterogeneous errors
            row["message"] = f"{type(error).__name__}: {error}"
        rows.append(row)
    return pd.DataFrame(rows)


def _install_remote_client() -> type:
    """Return a GEKKO subclass that reaches the live public APMonitor server.

    Two host-level facts force this shim, and both are recorded rather than hidden:

    1. The GEKKO 1.3.2 default server name no longer resolves, so the server is
       overridden with ``REMOTE_SERVER``.
    2. GEKKO names its models ``gk_model0``, ``gk_model1``, ... and the server keys
       each workspace on the observed client address. Behind a CDN that address is
       shared between clients, so every model receives a unique random name.

    Only the model is sent to the server. No data file and no credential leaves the
    host.
    """
    opener = urllib.request.build_opener()
    opener.addheaders = [("User-Agent", REMOTE_USER_AGENT)]
    urllib.request.install_opener(opener)

    from gekko import GEKKO  # type: ignore[import-not-found]

    class RemoteGEKKO(GEKKO):  # type: ignore[misc]
        def __init__(self, remote: bool = False, server: str = REMOTE_SERVER, name=None):
            super().__init__(
                remote=remote,
                server=server,
                name=name or "fla" + uuid.uuid4().hex[:12],
            )

    return RemoteGEKKO


def execute_remote_sweep() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Solve every allocation on the public APMonitor server with IPOPT.

    Returns the status table in the canonical schema and a companion table that
    carries the steady-state growth rate and sector composition per allocation.
    The steady-state stage and the dynamic stage are recorded separately, because
    the dynamic optimisation is the harder of the two and can fail on its own.
    """
    sys.path.insert(0, str(UPSTREAM))
    from models.salmonella import dynamic, steadystate  # type: ignore[import-not-found]

    from models import common  # type: ignore[import-not-found]

    remote_gekko = _install_remote_client()
    steadystate.GEKKO = remote_gekko
    dynamic.GEKKO = remote_gekko

    kcat, km, hill, upper = _model_inputs()
    time = np.concatenate([[0, 0.1], np.arange(0.5, 8.5, 0.5)])
    distance_initial = 8500
    gradient_age_seconds = 3 * 3600
    glucose_boundary_mM = 5.0
    glucose_initial = round(
        common.diffusion_model(
            distance_initial,
            gradient_age_seconds,
            600,
            glucose_boundary_mM,
        ),
        3,
    )
    rows: list[dict[str, float | str | bool]] = []
    steady_rows: list[dict[str, float | str]] = []
    for allocation in ALLOCATIONS:
        row: dict[str, float | str | bool] = {
            "flagellar_allocation": float(allocation),
            "flagellar_allocation_percent": float(allocation * 100),
            "solver_requested": "APMonitor solver 3 (IPOPT), remote=True",
            "remote": True,
            "status": "failed_steady_state_stage",
            "objective_final_growth_rate_1h": math.nan,
            "final_distance_um": math.nan,
            "final_substrate_mM": math.nan,
            "message": "",
        }
        steady_row: dict[str, float | str] = {
            "flagellar_allocation": float(allocation),
            "flagellar_allocation_percent": float(allocation * 100),
            "steady_state_status": "failed",
            "steady_state_growth_rate_1h": math.nan,
        }
        try:
            steady = steadystate.simulate(
                time,
                glucose_initial,
                upper,
                float(allocation),
                kcat.copy(),
                km.copy(),
                hill.copy(),
                True,
            )
            steady_row["steady_state_status"] = "success"
            steady_row["steady_state_growth_rate_1h"] = float(steady.table.iloc[-1].mu)
            for sector, variable in steady.a.items():
                steady_row[f"alpha_{sector}"] = float(variable[1])
            for species, variable in steady.c.items():
                steady_row[f"concentration_{species}"] = float(variable[1])
            concentrations = steady.c.apply(lambda value: round(value[1], 3))
            row["status"] = "failed_dynamic_stage"
        except Exception as error:  # solver libraries expose heterogeneous errors
            row["message"] = f"steady-state stage: {type(error).__name__}: {error}"
            rows.append(row)
            steady_rows.append(steady_row)
            continue
        try:
            result = dynamic.simulate(
                time,
                gradient_age_seconds,
                distance_initial,
                glucose_boundary_mM,
                upper,
                float(allocation),
                kcat.copy(),
                km.copy(),
                hill.copy(),
                concentrations,
                True,
            )
            final = result.table.iloc[-1]
            row.update(
                {
                    "status": "success",
                    "objective_final_growth_rate_1h": float(final.mu),
                    "final_distance_um": float(final.distance),
                    "final_substrate_mM": float(final.cex),
                    "message": "remote IPOPT solve completed",
                }
            )
        except Exception as error:  # solver libraries expose heterogeneous errors
            row["message"] = (
                "steady-state stage solved; dynamic stage did not: "
                f"{type(error).__name__}: {error}".strip()
            )
        rows.append(row)
        steady_rows.append(steady_row)
    return pd.DataFrame(rows), pd.DataFrame(steady_rows)


#: Initial guess handed to the next model. ``None`` means the cold start that
#: the upstream model declares. The GEKKO subclass below reads it.
_WARM_START: dict[str, list[float]] | None = None


def _warm_start_from(table: pd.DataFrame) -> dict[str, list[float]]:
    """Turn a solved trajectory into an initial guess, keyed by variable name."""
    guess: dict[str, list[float]] = {}
    for column in table.columns:
        if column in NON_VARIABLE_COLUMNS or column.startswith("slk_"):
            continue
        values = table[column].astype(float)
        if column in SCALED_COLUMNS:
            values = values / 3.6
        guess[column] = [float(value) for value in values]
    return guess


def _install_continuation_client() -> type:
    """Return a remote GEKKO subclass that accepts a warm start.

    The subclass overrides one thing: the initial guess written into the model
    data file. Every equation, bound and initial condition stays as
    ``dynamic.py`` declares it.

    The guess is applied inside ``solve``, after the model has built every
    equation. It cannot be applied at ``Var`` time: a GEKKO variable whose value
    is a list is a sequence, so NumPy broadcasts it elementwise and the symbolic
    equations collapse into numbers.

    The first node of the guess is overwritten with the declared value, so a
    differential variable keeps its exact initial condition and only the later
    nodes are seeded.
    """
    base = _install_remote_client()

    class ContinuationGEKKO(base):  # type: ignore[misc, valid-type]
        def solve(self, *args, **kwargs):
            if _WARM_START is not None:
                for variable in self._variables:
                    guess = _WARM_START.get(re.sub(r"\W+", "_", str(variable.name)).lower())
                    if guess is None:
                        continue
                    declared = np.atleast_1d(np.asarray(variable.value.value, dtype=float))
                    seeded = [float(value) for value in guess]
                    seeded[0] = float(declared.ravel()[0])
                    variable.VALUE = seeded
            return super().solve(*args, **kwargs)

    return ContinuationGEKKO


def _objective_value(model) -> float:
    """Return the solver objective, or NaN when the solver did not report one."""
    try:
        return float(model.options.OBJFCNVAL)
    except Exception:  # the option is absent on some solver paths
        return math.nan


def execute_continuation_sweep() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Solve the 0–1% sweep with a warm-start continuation and a multi-start.

    Every allocation gets up to three attempts: the cold start of the upstream
    model, a warm start from the accepted solution of the neighbour above, and a
    warm start from the accepted solution of the neighbour below. The attempt
    with the lowest solver objective is accepted. GEKKO minimises, and the model
    maximises the growth rate, so the lowest objective is the best solution.

    Returns the accepted-status table, the per-attempt record and the accepted
    trajectories stacked into one long table.
    """
    global _WARM_START

    sys.path.insert(0, str(UPSTREAM))
    from models.salmonella import dynamic, steadystate  # type: ignore[import-not-found]

    from models import common  # type: ignore[import-not-found]

    client = _install_continuation_client()
    steadystate.GEKKO = client
    dynamic.GEKKO = client

    kcat, km, hill, upper = _model_inputs()
    time = np.concatenate([[0, 0.1], np.arange(0.5, 8.5, 0.5)])
    distance_initial = 8500
    gradient_age_seconds = 3 * 3600
    glucose_boundary_mM = 5.0
    glucose_initial = round(
        common.diffusion_model(
            distance_initial, gradient_age_seconds, 600, glucose_boundary_mM
        ),
        3,
    )

    attempts: list[dict[str, object]] = []
    accepted: dict[float, dict[str, object]] = {}
    trajectories: dict[float, pd.DataFrame] = {}
    concentrations: dict[float, pd.Series] = {}
    steady_rows: list[dict[str, float | str]] = []

    # The steady-state stage is solved once per allocation and never warm
    # started. It converged at every one of the 21 steps on the first attempt.
    _WARM_START = None
    for allocation in ALLOCATIONS:
        steady_row: dict[str, float | str] = {
            "flagellar_allocation": float(allocation),
            "flagellar_allocation_percent": float(allocation * 100),
            "steady_state_status": "failed",
            "steady_state_growth_rate_1h": math.nan,
        }
        try:
            steady = steadystate.simulate(
                time,
                glucose_initial,
                upper,
                float(allocation),
                kcat.copy(),
                km.copy(),
                hill.copy(),
                True,
            )
            steady_row["steady_state_status"] = "success"
            steady_row["steady_state_growth_rate_1h"] = float(steady.table.iloc[-1].mu)
            for sector, variable in steady.a.items():
                steady_row[f"alpha_{sector}"] = float(variable[1])
            for species, variable in steady.c.items():
                steady_row[f"concentration_{species}"] = float(variable[1])
            concentrations[float(allocation)] = steady.c.apply(lambda value: round(value[1], 3))
        except Exception as error:  # solver libraries expose heterogeneous errors
            steady_row["message"] = f"{type(error).__name__}: {error}"
        steady_rows.append(steady_row)

    def attempt(allocation: float, start: str, guess: dict[str, list[float]] | None) -> None:
        """Solve one allocation from one initial guess and record the outcome."""
        global _WARM_START

        record: dict[str, object] = {
            "flagellar_allocation": float(allocation),
            "flagellar_allocation_percent": float(allocation * 100),
            "initial_guess": start,
            "solver_requested": "APMonitor solver 3 (IPOPT), remote=True",
            "remote": True,
            "status": "failed_dynamic_stage",
            "solver_objective": math.nan,
            "objective_final_growth_rate_1h": math.nan,
            "final_distance_um": math.nan,
            "final_substrate_mM": math.nan,
            "message": "",
        }
        if allocation not in concentrations:
            record["status"] = "failed_steady_state_stage"
            record["message"] = "steady-state stage did not solve; dynamic stage not attempted"
            attempts.append(record)
            return
        _WARM_START = guess
        try:
            result = dynamic.simulate(
                time,
                gradient_age_seconds,
                distance_initial,
                glucose_boundary_mM,
                upper,
                float(allocation),
                kcat.copy(),
                km.copy(),
                hill.copy(),
                concentrations[allocation],
                True,
            )
        except Exception as error:  # solver libraries expose heterogeneous errors
            record["message"] = f"{type(error).__name__}: {error}"
            attempts.append(record)
            _WARM_START = None
            return
        finally:
            _WARM_START = None
        final = result.table.iloc[-1]
        objective = _objective_value(result.model)
        record.update(
            {
                "status": "success",
                "solver_objective": objective,
                "objective_final_growth_rate_1h": float(final.mu),
                "final_distance_um": float(final.distance),
                "final_substrate_mM": float(final.cex),
                "message": f"remote IPOPT solve completed from {start} initial guess",
            }
        )
        attempts.append(record)
        best = accepted.get(allocation)
        if best is None or _is_better(record, best):
            accepted[allocation] = record
            trajectories[allocation] = result.table.copy()

    descending = [float(value) for value in ALLOCATIONS[::-1]]
    ascending = [float(value) for value in ALLOCATIONS]

    # Pass 1: cold start at every allocation. This repeats the ``--remote`` mode
    # and gives the continuation something to improve on.
    for allocation in descending:
        attempt(allocation, "cold", None)

    # Pass 2: continuation downward from the anchor.
    guess: dict[str, list[float]] | None = None
    anchor = trajectories.get(CONTINUATION_ANCHOR)
    if anchor is not None:
        guess = _warm_start_from(anchor)
    for allocation in descending:
        if allocation == CONTINUATION_ANCHOR or guess is None:
            continue
        attempt(allocation, "warm_from_above", guess)
        solved = trajectories.get(allocation)
        if solved is not None:
            guess = _warm_start_from(solved)

    # Pass 3: continuation upward from the lowest allocation that solved.
    guess = None
    for allocation in ascending:
        if guess is not None:
            attempt(allocation, "warm_from_below", guess)
        solved = trajectories.get(allocation)
        if solved is not None:
            guess = _warm_start_from(solved)

    status_rows: list[dict[str, object]] = []
    for allocation in ascending:
        record = accepted.get(allocation)
        if record is None:
            failures = [row for row in attempts if row["flagellar_allocation"] == allocation]
            status_rows.append(
                {
                    "flagellar_allocation": allocation,
                    "flagellar_allocation_percent": allocation * 100,
                    "initial_guess": "none accepted",
                    "solver_requested": "APMonitor solver 3 (IPOPT), remote=True",
                    "remote": True,
                    "status": "failed_dynamic_stage",
                    "attempts": len(failures),
                    "solver_objective": math.nan,
                    "objective_final_growth_rate_1h": math.nan,
                    "final_distance_um": math.nan,
                    "final_substrate_mM": math.nan,
                    "message": "no initial guess reached a solution",
                }
            )
            continue
        row = dict(record)
        row["attempts"] = len(
            [entry for entry in attempts if entry["flagellar_allocation"] == allocation]
        )
        status_rows.append(row)

    stacked: list[pd.DataFrame] = []
    for allocation, table in sorted(trajectories.items()):
        frame = table.copy()
        frame.insert(0, "flagellar_allocation", allocation)
        stacked.append(frame)
    trajectory_table = (
        pd.concat(stacked, ignore_index=True) if stacked else pd.DataFrame()
    )
    return pd.DataFrame(status_rows), pd.DataFrame(attempts), trajectory_table


def _is_better(candidate: dict[str, object], incumbent: dict[str, object]) -> bool:
    """Return True when the candidate solved to a better objective."""
    new = float(candidate["solver_objective"])  # type: ignore[arg-type]
    old = float(incumbent["solver_objective"])  # type: ignore[arg-type]
    if not math.isnan(new) and not math.isnan(old):
        return new < old
    new_mu = float(candidate["objective_final_growth_rate_1h"])  # type: ignore[arg-type]
    old_mu = float(incumbent["objective_final_growth_rate_1h"])  # type: ignore[arg-type]
    return new_mu > old_mu


def _write_continuation(
    status: pd.DataFrame, attempts: pd.DataFrame, trajectories: pd.DataFrame
) -> None:
    for path in (CONTINUATION_OUTPUT, TRACKED_CONTINUATION):
        path.parent.mkdir(parents=True, exist_ok=True)
        status.to_csv(path, index=False)
    for path in (ATTEMPT_OUTPUT, TRACKED_ATTEMPTS):
        path.parent.mkdir(parents=True, exist_ok=True)
        attempts.to_csv(path, index=False)
    if trajectories.empty:
        return
    TRAJECTORY_DIR.mkdir(parents=True, exist_ok=True)
    for allocation, frame in trajectories.groupby("flagellar_allocation"):
        target = TRAJECTORY_DIR / f"dynamic_flag_{float(allocation):.4f}.csv"
        frame.drop(columns=["flagellar_allocation"]).to_csv(target, index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--remote", action="store_true", help="canonical: solve on the APMonitor server"
    )
    mode.add_argument(
        "--continuation",
        action="store_true",
        help="remote solve with a warm-start continuation and a multi-start",
    )
    mode.add_argument("--execute", action="store_true", help="local, non-network attempt")
    mode.add_argument("--plan", action="store_true", help="historical blocked-status plan")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    steady: pd.DataFrame | None = None
    if args.continuation:
        status, attempts, trajectories = execute_continuation_sweep()
        _write_continuation(status, attempts, trajectories)
        successes = int(status.status.eq("success").sum())
        print(
            f"continuation: {successes}/{len(status)} allocations solved; "
            f"{len(attempts)} attempts recorded"
        )
        return
    if args.remote:
        result, steady = execute_remote_sweep()
    elif args.execute:
        result = execute_sweep()
    else:
        result = sweep_plan()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    if args.output == DEFAULT_OUTPUT:
        TRACKED_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(TRACKED_OUTPUT, index=False)
        if steady is not None:
            STEADY_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
            steady.to_csv(STEADY_OUTPUT, index=False)
            TRACKED_STEADY.parent.mkdir(parents=True, exist_ok=True)
            steady.to_csv(TRACKED_STEADY, index=False)
    successes = int(result.status.eq("success").sum())
    print(f"wrote {len(result)} allocation statuses to {args.output}; successes={successes}")


if __name__ == "__main__":
    main()
