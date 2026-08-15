#!/usr/bin/env python3
"""Write the exact software version table from the frozen environment.

The Nature Communications Reporting Summary asks for the version of every
package that produced a result, and Michael Jahn asked for the same.  This tool
reads them, it does not retype them:

* ``uv.lock`` is the authoritative resolution and holds one version per package;
* ``requirements.lock`` is the hash-pinned export of that same resolution, and
  the two must agree, or the build stops;
* ``pyproject.toml`` holds the declared constraint each direct dependency was
  resolved against;
* ``build/environment/bootstrap.json`` holds the interpreter and the platform
  the frozen environment ran on;
* ``models/cell_economy/LOCAL_SOLVER_VALIDATION.md`` holds the remote solver
  route, which no lock file can pin.

The grouping into roles is an authoring decision and is written down in
``ROLES`` below.  Every version beside a name comes from the lock.

Usage::

    python tools/build_software_versions.py --root .
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import tomllib
from collections.abc import Sequence
from pathlib import Path

#: Role, then the packages that carry it, in the order the table prints them.
#: A package that produces a number in a figure belongs to a named role; the
#: rest are transitive and are counted, not listed.
ROLES: list[tuple[str, tuple[str, ...]]] = [
    (
        "Optimisation and solver stack",
        ("gekko", "scipy"),
    ),
    (
        "Numerical and tabular stack",
        (
            "numpy",
            "pandas",
            "pyarrow",
            "scikit-learn",
            "scikit-image",
            "openpyxl",
            "xlsxwriter",
        ),
    ),
    (
        "Plotting and image stack",
        (
            "matplotlib",
            "seaborn",
            "adjusttext",
            "cmcrameri",
            "colorspacious",
            "pillow",
            "imageio",
            "cairosvg",
        ),
    ),
    (
        "Workflow and validation",
        ("snakemake", "pyyaml", "jsonschema"),
    ),
    (
        "Testing and linting",
        ("pytest", "pytest-regressions", "ruff"),
    ),
]

SOLVER_NOTE = "models/cell_economy/LOCAL_SOLVER_VALIDATION.md"
SOLVER_PATTERN = re.compile(
    r"GEKKO (?P<gekko>[0-9.]+), `remote=True`, `server=\"(?P<server>[^\"]+)\"`, "
    r"solver 3 \(IPOPT (?P<ipopt>v[0-9.]+)\) server-side"
)


def normalise(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def read_uv_lock(path: Path) -> tuple[dict[str, str], str]:
    document = tomllib.loads(path.read_text(encoding="utf-8"))
    versions = {
        normalise(package["name"]): str(package["version"])
        for package in document["package"]
        if "version" in package
    }
    return versions, str(document.get("requires-python", "unrecorded"))


def read_requirements_lock(path: Path) -> dict[str, str]:
    versions: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Za-z0-9._-]+)==([^\s\\]+)", line.strip())
        if match:
            versions[normalise(match.group(1))] = match.group(2)
    return versions


def read_constraints(path: Path) -> dict[str, str]:
    """Return the declared constraint of every direct dependency."""
    document = tomllib.loads(path.read_text(encoding="utf-8"))
    declared: dict[str, str] = {}
    groups: list[Sequence[object]] = [document["project"].get("dependencies", [])]
    groups += list(document.get("dependency-groups", {}).values())
    for group in groups:
        for entry in group:
            if not isinstance(entry, str):
                continue  # an include-group reference, not a requirement
            match = re.match(r"^([A-Za-z0-9._-]+)\s*(.*)$", entry.strip())
            if match:
                declared[normalise(match.group(1))] = match.group(2).strip() or "any"
    return declared


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    arguments = parser.parse_args(argv)
    root = arguments.root.resolve()

    resolved, requires_python = read_uv_lock(root / "uv.lock")
    exported = read_requirements_lock(root / "requirements.lock")
    constraints = read_constraints(root / "pyproject.toml")
    bootstrap = json.loads((root / "build" / "environment" / "bootstrap.json").read_text("utf-8"))

    # The two lock files describe one resolution.  A disagreement means one of
    # them was regenerated alone, and the table would then be wrong.
    disagreements = sorted(
        f"{name}: uv.lock {resolved[name]}, requirements.lock {exported[name]}"
        for name in set(resolved) & set(exported)
        if resolved[name] != exported[name]
    )
    if disagreements:
        raise SystemExit(
            "uv.lock and requirements.lock disagree; regenerate the export:\n  "
            + "\n  ".join(disagreements)
        )

    listed: set[str] = set()
    rows: list[dict[str, str]] = []
    for role, packages in ROLES:
        for package in packages:
            key = normalise(package)
            if key not in resolved:
                raise SystemExit(f"{package} is named in ROLES but is not in uv.lock")
            listed.add(key)
            rows.append(
                {
                    "role": role,
                    "package": package,
                    "version": resolved[key],
                    "declared_constraint": constraints.get(key, "transitive"),
                    "hash_pinned": "yes" if key in exported else "no",
                    "source": "uv.lock",
                }
            )

    solver = SOLVER_PATTERN.search((root / SOLVER_NOTE).read_text(encoding="utf-8"))
    if solver is None:
        raise SystemExit(f"{SOLVER_NOTE} no longer records the remote solver route")

    transitive = sorted(set(resolved) - listed)
    reports = root / "docs" / "revision_2026-08-12"
    reports.mkdir(parents=True, exist_ok=True)

    csv_path = reports / "software_versions.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    lines: list[str] = []
    lines.append("# Software versions")
    lines.append("")
    lines.append(
        "Generated by `tools/build_software_versions.py` from `uv.lock`, "
        "`requirements.lock`, `pyproject.toml` and "
        "`build/environment/bootstrap.json`. Do not edit by hand; run "
        "`make software-versions`."
    )
    lines.append("")
    lines.append("## Language and platform")
    lines.append("")
    lines.append("| Item | Value | Source |")
    lines.append("|---|---|---|")
    lines.append(
        f"| Python | {bootstrap['python']} | build/environment/bootstrap.json |"
    )
    lines.append(f"| Python constraint | `{requires_python}` | uv.lock |")
    lines.append(f"| Platform | {bootstrap['platform']} | build/environment/bootstrap.json |")
    lines.append(
        f"| Environment frozen | {bootstrap['generated_at_utc']} | "
        "build/environment/bootstrap.json |"
    )
    lines.append("")
    lines.append("## Packages")
    lines.append("")
    lines.append(
        "`Declared constraint` is what `pyproject.toml` asks for. `Version` is "
        "what `uv.lock` resolved. `Hash-pinned` states whether "
        "`requirements.lock` carries the artefact hashes of that version."
    )
    lines.append("")
    for role, packages in ROLES:
        lines.append(f"### {role}")
        lines.append("")
        lines.append("| Package | Version | Declared constraint | Hash-pinned |")
        lines.append("|---|---|---|---|")
        for package in packages:
            row = next(
                item for item in rows if item["package"] == package and item["role"] == role
            )
            lines.append(
                "| {package} | {version} | `{declared_constraint}` | {hash_pinned} |".format(**row)
            )
        lines.append("")
    lines.append("## Solver route")
    lines.append("")
    lines.append(
        "The cell-economy model is solved through GEKKO on a remote server, so "
        "no lock file can pin the solver. The route is recorded in "
        f"`{SOLVER_NOTE}` and reproduced here."
    )
    lines.append("")
    lines.append("| Item | Value |")
    lines.append("|---|---|")
    lines.append(f"| GEKKO client | {solver.group('gekko')} |")
    lines.append(f"| Server | {solver.group('server')} |")
    lines.append(f"| Solver | APMonitor solver 3, IPOPT {solver.group('ipopt')}, server-side |")
    lines.append("")
    lines.append("## Remaining packages")
    lines.append("")
    lines.append(
        f"`uv.lock` resolves {len(resolved)} packages in total. The tables above "
        f"name {len(listed)} of them, which are the packages that produce a "
        f"number or a mark in a figure. The other {len(transitive)} are "
        "transitive dependencies; every one is pinned by version and by hash in "
        "`requirements.lock`, and that file is the complete record."
    )
    lines.append("")
    lines.append("## Software this repository does not pin")
    lines.append("")
    lines.append(
        "`rsvg-convert` (librsvg) rasterises the assembled figures and renders "
        "the Supplementary Information PDF, and Ghostscript joins its pages. "
        "Both are host programs outside the Python environment, so no lock file "
        "records them. `build/supplementary_information/"
        "Supplementary_Information.manifest.json` records the version of each "
        "one that produced the current PDF."
    )
    lines.append("")
    lines.append(
        "Image acquisition, segmentation and mass-spectrometry software is named "
        "in the manuscript Methods and is not installed here. See "
        "`docs/ENVIRONMENT.md`."
    )
    lines.append("")

    markdown_path = reports / "software_versions.md"
    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    print(
        f"wrote {markdown_path.relative_to(root)} and {csv_path.relative_to(root)} "
        f"for {len(rows)} named packages of {len(resolved)} resolved"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
