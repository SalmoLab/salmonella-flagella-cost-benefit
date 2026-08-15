#!/usr/bin/env python3
"""Build the two Zenodo data deposits as deterministic zip archives.

The code of this collection is archived through a GitHub release.  The data are
not.  They go to Zenodo as two direct uploads:

1. **The data archive.**  ``data/external/``, ``data/processed/`` and
   ``data/source_data/``.  A reader unzips it at the root of a clone and every
   panel with a registered source rebuilds.  The archive keeps the three trees
   at ``data/<tree>/`` so that the instruction in the repository ``README.md``
   holds without a further move.

2. **The trajectory bundle.**  The six simulated-trajectory tables of
   Supplementary Figure 4, taken unchanged from
   ``build/source_data/deposit/Supplementary_Figure_4_trajectories/``.  The
   manuscript Data Availability statement names this bundle on its own, so it
   gets its own citable record.

Both archives are byte-reproducible.  Nothing in them comes from the clock:
every member carries the same fixed modification time, the member order is
sorted, and every generated text is derived from the file list.  Rebuild the
archives on another day and the sha256 does not move.  This follows the rule
already used for the Source Data zip in ``src/flagella_repro/source_workbook.py``.

What the archives leave out, and why, is written into their ``README.txt``:

* ``.DS_Store`` and ``__pycache__`` — machine litter, not data;
* ``.gitkeep`` — placeholders that belong to the code repository;
* ``data/source_data/superseded_2026-07/`` — nine directories of source data for
  the July 2026 figure layout.  Nothing reads them and no figure in the paper
  plots them.

Usage::

    python tools/build_data_deposits.py --root .

Complexity: one pass over ``data/`` (272 files, 140 MB).  The members are held
in memory while the archive is written, so peak memory is the archive size.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import tempfile
import textwrap
import zipfile
from collections.abc import Sequence
from pathlib import Path

#: Fixed modification time for every archive member, as ``ZipInfo.date_time``.
#: It is the date of the revision this deposit belongs to.  A fixed value is
#: what makes the archive byte-reproducible.
FIXED_ZIP_TIME = (2026, 8, 12, 0, 0, 0)

#: Version of both deposits.  It matches the code release, the git tag,
#: ``CITATION.cff`` and ``.zenodo.json``.
DEPOSIT_VERSION = "1.0.0"

#: The archived code release these data belong to.  Cite the version DOI, not
#: the concept DOI: the concept DOI resolves to the newest version, and a later
#: version may not reproduce these figures.
CODE_VERSION_DOI = "10.5281/zenodo.21950614"
CODE_CONCEPT_DOI = "10.5281/zenodo.21950613"
CODE_REPOSITORY = "https://github.com/SalmoLab/salmonella-flagella-cost-benefit"
CODE_TAG = "v1.0.0"

MANUSCRIPT = (
    'Giralt-Zúñiga et al., "The cost-benefit trade-off of peritrichous flagellation in bacteria"'
)

#: Width the generated READMEs wrap to.
WRAP = 76

LICENCE = "CC-BY-4.0"
LICENCE_URL = "https://creativecommons.org/licenses/by/4.0/"

#: Trees inside a deposit that do not carry the record licence, with the licence
#: they do carry and its holder.  ``LICENSES.md`` in the code repository is the
#: authority for this map; these entries repeat it, they do not decide it.
LICENCE_EXCEPTIONS: list[tuple[str, str, str]] = [
    (
        "data/external/cell_economy_results",
        "GPL-3.0-only",
        "M. Jahn. It follows the licence of the delivering package, the "
        "cell-economy models. The full GPL-3.0 text ships with the code "
        "release, as LICENSE and as models/cell_economy/upstream/LICENSE.",
    ),
]

CONTACT = "Marc Erhardt, Humboldt-Universität zu Berlin — marc.erhardt@hu-berlin.de"

#: File and directory names that never enter a deposit.
EXCLUDED_NAMES = frozenset({".DS_Store", ".gitkeep", "__pycache__"})

#: Directories under ``data/`` that are excluded by decision, with the reason
#: the ``README.txt`` prints.
EXCLUDED_TREES: dict[str, str] = {
    "data/source_data/superseded_2026-07": (
        "Nine directories of source data for the July 2026 figure layout, "
        "before the 12 August repartition. Nothing in the code reads them and "
        "no figure in the paper plots them."
    ),
}

#: The three trees the data archive carries, with the one-line description each
#: gets in the ``README.txt``.
DATA_TREES: list[tuple[str, str]] = [
    (
        "data/external",
        "Collaborator deliveries: the promoter-series proteomics tables and the "
        "cell-economy model results.",
    ),
    (
        "data/processed",
        "Processed measurement tables. Most panel producers read from here.",
    ),
    (
        "data/source_data",
        "The registered per-panel source tables, one directory per figure.",
    ),
]

TRAJECTORY_BUNDLE = "build/source_data/deposit/Supplementary_Figure_4_trajectories"

CHECKSUM_FILE = "CHECKSUMS.tsv"
README_FILE = "README.txt"


class DepositError(RuntimeError):
    """A deposit cannot be built from the tree as it stands."""


def sha256_of(payload: bytes) -> str:
    """Return the hex sha256 of ``payload``."""
    return hashlib.sha256(payload).hexdigest()


def is_excluded(relative: Path) -> bool:
    """Return True if ``relative`` must not enter a deposit."""
    if any(part in EXCLUDED_NAMES for part in relative.parts):
        return True
    text = relative.as_posix()
    return any(text == tree or text.startswith(f"{tree}/") for tree in EXCLUDED_TREES)


def collect(root: Path, tree: str) -> list[tuple[str, Path]]:
    """Return ``(archive_path, source_path)`` for every kept file under ``tree``.

    ``archive_path`` keeps the ``data/<tree>/...`` prefix, because the
    repository ``README.md`` tells the reader to unzip at the repository root.
    """
    base = root / tree
    if not base.is_dir():
        raise DepositError(f"missing input tree: {tree}")
    members: list[tuple[str, Path]] = []
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if is_excluded(relative):
            continue
        members.append((relative.as_posix(), path))
    if not members:
        raise DepositError(f"input tree holds no files after exclusions: {tree}")
    return members


def human_size(count: int) -> str:
    """Return ``count`` bytes as a short decimal string, e.g. ``38.1 MB``."""
    if count >= 1_000_000_000:
        return f"{count / 1_000_000_000:.1f} GB"
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f} MB"
    if count >= 1_000:
        return f"{count / 1_000:.1f} kB"
    return f"{count} B"


def wrap(text: str, indent: str = "", first: str | None = None) -> list[str]:
    """Return ``text`` wrapped to ``WRAP`` columns as a list of lines."""
    return textwrap.wrap(
        " ".join(text.split()),
        width=WRAP,
        initial_indent=indent if first is None else first,
        subsequent_indent=indent,
    )


def heading(text: str, rule: str = "=") -> list[str]:
    """Return ``text`` with an underline of its own length."""
    return [text, rule * len(text)]


def checksum_table(members: list[tuple[str, bytes]]) -> str:
    """Return the ``CHECKSUMS.tsv`` text for ``members``.

    One row per file, sorted by path, with the size in bytes and the sha256.
    ``CHECKSUMS.tsv`` cannot list itself, so it is the one file with no row.
    """
    lines = ["path\tbytes\tsha256"]
    for name, payload in sorted(members):
        lines.append(f"{name}\t{len(payload)}\t{sha256_of(payload)}")
    return "\n".join(lines) + "\n"


def write_zip(destination: Path, members: list[tuple[str, bytes]]) -> None:
    """Write ``members`` to ``destination`` as a deterministic zip archive.

    Every member carries ``FIXED_ZIP_TIME``, mode 0644 and the Unix create
    system, and the members are written in sorted path order.  Two runs over the
    same inputs therefore produce the same bytes.
    """
    with zipfile.ZipFile(
        destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for name, payload in sorted(members):
            info = zipfile.ZipInfo(name, date_time=FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o644 << 16
            archive.writestr(info, payload)


def publish(staged: Path, output: Path) -> str:
    """Move ``staged`` onto ``output`` and return the sha256 of the result."""
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.with_name(f".{output.name}.staging")
    shutil.copyfile(staged, staging)
    staging.replace(output)
    digest = hashlib.sha256()
    with output.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    checksum = digest.hexdigest()
    output.with_suffix(output.suffix + ".sha256").write_text(
        f"{checksum}  {output.name}\n", encoding="utf-8"
    )
    return checksum


def provenance_block() -> list[str]:
    """Return the paper, repository and licence lines both READMEs share."""
    lines = heading("Which paper, which code", "-")
    lines += wrap(f"Manuscript: {MANUSCRIPT}", "  ", "")
    lines += [
        "  DOI: pending. Add it once the paper is published.",
        "",
        f"Code repository: {CODE_REPOSITORY}",
        f"  Tag: {CODE_TAG}",
        f"  Archived release: https://doi.org/{CODE_VERSION_DOI}",
        "  Concept DOI, always the newest version:",
        f"    https://doi.org/{CODE_CONCEPT_DOI}",
        "",
    ]
    lines += wrap(
        "Cite the version DOI when you reproduce a figure. The concept DOI "
        "resolves to whatever version is newest, and a later version may not "
        "reproduce these figures."
    )
    lines.append("")
    return lines


def licence_block(present: frozenset[str] = frozenset()) -> list[str]:
    """Return the licence and contact lines both READMEs share.

    ``present`` names the archive paths that were actually packaged, so that an
    exception is printed only when the tree it covers is in this archive.
    """
    lines = heading("Licence", "-")
    lines.append(f"{LICENCE}. {LICENCE_URL}")
    lines += wrap(
        "You may share and adapt these data. Give credit: cite the manuscript and this deposit."
    )
    lines.append("")
    exceptions = [
        entry
        for entry in LICENCE_EXCEPTIONS
        if any(name.startswith(f"{entry[0]}/") for name in present)
    ]
    if exceptions:
        lines += wrap(
            "One tree in this archive is an exception. It keeps the licence of "
            "the package it came from:"
        )
        lines.append("")
        for tree, licence, holder in exceptions:
            lines += wrap(f"{tree}/ — {licence}. {holder}", "  ", "* ")
        lines.append("")
        lines += wrap(
            "LICENSES.md in the code repository holds the per-directory map and is the authority."
        )
        lines.append("")
    lines += wrap(
        "The code that reads these data carries a different licence. See "
        "LICENSES.md in the code repository."
    )
    lines.append("")
    lines += heading("Contact", "-")
    lines.append(CONTACT)
    return lines


def verify_block(checksum_path: str) -> list[str]:
    """Return the lines that tell a downloader how to verify the archive."""
    lines = heading("Verifying", "-")
    lines += wrap(
        f"{checksum_path} lists every file in this archive with its size in "
        "bytes and its sha256. It cannot list itself. From the directory you "
        "unzipped into, on Linux or macOS:"
    )
    lines += [
        "",
        f"    awk -F'\\t' 'NR>1 {{print $3\"  \"$1}}' {checksum_path} \\",
        "        | shasum -a 256 -c",
        "",
    ]
    lines += wrap("The Zenodo record description carries the sha256 of the archive file itself.")
    lines.append("")
    return lines


def data_readme(tree_totals: list[tuple[str, str, int, int]], present: frozenset[str]) -> str:
    """Return the ``README.txt`` of the data archive.

    ``tree_totals`` holds ``(tree, description, file_count, byte_count)`` for
    each of the three trees, so the printed sizes come from the archive that was
    actually built, not from a number typed by hand.  ``present`` holds the
    archive paths, so that a licence exception is printed only when its tree is
    really in the archive.
    """
    lines = heading("Data deposit — flagellar cost-benefit manuscript")
    lines += [
        "",
        f"Version {DEPOSIT_VERSION}",
        "",
    ]
    lines += heading("What this is", "-")
    lines += wrap(
        "This archive holds the input data for the figures of the manuscript "
        "named below. It is the deposit a reader needs to rebuild a panel. It "
        "carries three trees:"
    )
    lines.append("")
    for tree, description, count, size in tree_totals:
        lines.append(f"  {tree}/")
        lines += wrap(f"{count} files, {human_size(size)}. {description}", "    ")
    lines.append("")
    lines += wrap(
        "The tables are not raw instrument output. They are the registered "
        "starting points of the panel producers, recorded one by one in "
        "config/artifacts.csv of the code repository, each with its sha256."
    )
    lines.append("")
    lines += provenance_block()
    lines += heading("How to use it", "-")
    lines += wrap(f"1. Clone the code repository and check out tag {CODE_TAG}.", "   ", "")
    lines += wrap(
        "2. Unzip this archive at the root of the clone. The three trees then "
        "sit at data/external/, data/processed/ and data/source_data/, which "
        "is what the repository README.md asks for. Unzipping also writes "
        f"{README_FILE} (this file) and {CHECKSUM_FILE} to the repository "
        "root. Neither collides with a repository file and you may delete "
        "both.",
        "   ",
        "",
    )
    lines += wrap("3. Run `make bootstrap`, then `make reproduce-available`.", "   ", "")
    lines.append("")
    lines += wrap(
        "55 of the 60 panels have a registered source and rebuild from these "
        "trees. Five image panels have no registered source asset and render a "
        "labelled placeholder instead. The repository README.md names them. "
        "This is a stated limit of the collection, not a fault of this archive."
    )
    lines.append("")
    lines += verify_block(CHECKSUM_FILE)
    lines += heading("What is not here", "-")
    lines += wrap(
        "data/raw/ and data/interim/. They hold no data in the code release "
        "either. Raw microscopy and tracking files are not part of this "
        "collection. Each affected provenance document says so.",
        "  ",
        "* ",
    )
    lines += wrap(
        "Raw mass-spectrometry files. They are deposited in ProteomeXchange "
        "through the PRIDE partner repository. See the Data Availability "
        "statement of the paper.",
        "  ",
        "* ",
    )
    lines += wrap(".gitkeep placeholders. They belong to the code repository.", "  ", "* ")
    for tree, reason in sorted(EXCLUDED_TREES.items()):
        lines += wrap(
            f"{tree}/. {reason} They stay with the authors and are available on request.",
            "  ",
            "* ",
        )
    lines.append("")
    lines += heading("Overlap with the trajectory deposit", "-")
    lines += wrap(
        "data/source_data/supplementary_04/ holds the six simulated-trajectory "
        'tables S4_A to S4_F. The separate Zenodo record "Simulated '
        'trajectories of Supplementary Figure 4" holds the same six files, '
        "byte for byte, together with the seeds and the regeneration command "
        "of each one. This archive keeps them so that it rebuilds every "
        "available panel on its own. The two records point at each other "
        "through their Zenodo related identifiers."
    )
    lines.append("")
    lines += licence_block(present)
    return "\n".join(lines) + "\n"


def trajectory_readme(bundle_readme: str, file_count: int, byte_count: int) -> str:
    """Return the ``README.txt`` of the trajectory bundle.

    The text of the generated bundle README is kept verbatim at the end, under
    its own heading.  It holds the row count, the software versions and the
    upstream commit, and the build is its authority.
    """
    lines = heading("Simulated trajectories of Supplementary Figure 4")
    lines += [
        "",
        f"Version {DEPOSIT_VERSION}",
        "",
    ]
    lines += heading("What this is", "-")
    lines += wrap(
        f"{file_count} gzip-compressed CSV tables, {human_size(byte_count)} in "
        "total. Each table holds the position of every simulated cell at every "
        "time step of one panel of Supplementary Figure 4: 26 cells over 8001 "
        "steps, at a 0.0025 s time step across 20 s."
    )
    lines.append("")
    lines += wrap(
        "These tables are model output, not measurement. They are exactly "
        "regenerable from the seeds and the parameters recorded in "
        "MANIFEST.tsv. They are deposited rather than submitted as Source Data "
        "because they exceed the journal file limit, and because no reader "
        "re-derives a plotted value by hand from 208,026 rows."
    )
    lines.append("")
    lines += wrap(
        "Source Data Supplementary Figure 4, supplied with the paper, carries "
        "the obstacle fields and two summary tables derived from these "
        "trajectories. A reader can check every plotted value from those two "
        "tables alone. These trajectories are for a reader who wants the full "
        "model output."
    )
    lines.append("")
    lines += provenance_block()
    lines += heading("How to use it", "-")
    lines += [
        "To read a table:",
        "",
        "    import pandas as pd",
        '    frame = pd.read_csv("S4_A_simulated_trajectories.csv.gz")',
        "",
    ]
    lines += wrap(
        "To put the tables back into a clone of the code repository, unzip "
        "them into data/source_data/supplementary_04/. The data deposit of "
        "this collection already contains the same six files at that path, so "
        "you need this step only if you downloaded this record on its own."
    )
    lines.append("")
    lines += wrap(
        "MANIFEST.tsv gives, for every table, the row and column count, the "
        "sha256, the three random seeds, the exact regeneration command and "
        "the provenance record in the code repository. The command reproduces "
        "the file with the sha256 listed there."
    )
    lines.append("")
    lines += verify_block(CHECKSUM_FILE)
    lines += heading("Files", "-")
    lines += [
        "  S4_A … S4_F_simulated_trajectories.csv.gz",
        "      the six tables",
        "  MANIFEST.tsv",
        "      rows, columns, sha256, seeds, regeneration command, provenance",
        f"  {CHECKSUM_FILE}",
        "      every file in this archive, with its size and sha256",
        f"  {README_FILE}",
        "      this file",
        "",
    ]
    lines += heading("Related record", "-")
    lines += wrap(
        "The Zenodo data deposit of this collection holds the processed input "
        "tables, the external deliveries and the per-panel source tables, and "
        "it contains a byte-identical copy of these six tables. The two "
        "records point at each other through their Zenodo related identifiers."
    )
    lines.append("")
    lines += licence_block()
    lines += ["", ""]
    lines += heading("Bundle record, written by the build", "-")
    lines += wrap(
        "The lines below come from the generated bundle and are kept "
        "unchanged. Their DOI placeholder is resolved by the Zenodo record "
        "this archive belongs to."
    )
    lines.append("")
    lines.append(bundle_readme.rstrip("\n"))
    return "\n".join(lines) + "\n"


def build_data_deposit(root: Path, output_dir: Path) -> tuple[Path, str]:
    """Build the data archive and return its path and sha256."""
    members: list[tuple[str, bytes]] = []
    tree_totals: list[tuple[str, str, int, int]] = []
    for tree, description in DATA_TREES:
        files = collect(root, tree)
        size = 0
        for archive_path, source in files:
            payload = source.read_bytes()
            members.append((archive_path, payload))
            size += len(payload)
        tree_totals.append((tree, description, len(files), size))

    present = frozenset(name for name, _ in members)
    members.append((README_FILE, data_readme(tree_totals, present).encode("utf-8")))
    members.append((CHECKSUM_FILE, checksum_table(members).encode("utf-8")))

    output = output_dir / f"flagella_cost_benefit_data_v{DEPOSIT_VERSION}.zip"
    with tempfile.TemporaryDirectory() as temporary:
        staged = Path(temporary) / output.name
        write_zip(staged, members)
        return output, publish(staged, output)


def build_trajectory_deposit(root: Path, output_dir: Path) -> tuple[Path, str]:
    """Build the trajectory archive and return its path and sha256."""
    bundle = root / TRAJECTORY_BUNDLE
    if not bundle.is_dir():
        raise DepositError(
            f"missing trajectory bundle: {TRAJECTORY_BUNDLE}. "
            "Run `make source-data-available` first."
        )

    tables = sorted(
        path
        for path in bundle.iterdir()
        if path.is_file() and path.name.endswith("_simulated_trajectories.csv.gz")
    )
    if len(tables) != 6:
        raise DepositError(
            f"expected 6 trajectory tables in {TRAJECTORY_BUNDLE}, found {len(tables)}"
        )

    manifest = bundle / "MANIFEST.tsv"
    bundle_readme = bundle / "README.txt"
    for required in (manifest, bundle_readme):
        if not required.is_file():
            raise DepositError(f"missing {required.name} in {TRAJECTORY_BUNDLE}")

    members: list[tuple[str, bytes]] = []
    size = 0
    for path in tables:
        payload = path.read_bytes()
        members.append((path.name, payload))
        size += len(payload)
    members.append(("MANIFEST.tsv", manifest.read_bytes()))

    verify_manifest(manifest.read_text(encoding="utf-8"), dict(members))

    readme = trajectory_readme(bundle_readme.read_text(encoding="utf-8"), len(tables), size)
    members.append((README_FILE, readme.encode("utf-8")))
    members.append((CHECKSUM_FILE, checksum_table(members).encode("utf-8")))

    output = output_dir / f"flagella_cost_benefit_S4_trajectories_v{DEPOSIT_VERSION}.zip"
    with tempfile.TemporaryDirectory() as temporary:
        staged = Path(temporary) / output.name
        write_zip(staged, members)
        return output, publish(staged, output)


def verify_manifest(text: str, payloads: dict[str, bytes]) -> None:
    """Check every sha256 and byte count the bundle ``MANIFEST.tsv`` claims.

    The bundle manifest is the audited record of the panel provenance.  If a
    table on disk no longer matches it, the deposit must not be built.
    """
    rows = [line.split("\t") for line in text.strip("\n").split("\n")]
    header = rows[0]
    name_column = header.index("file")
    byte_column = header.index("bytes")
    hash_column = header.index("sha256")
    for row in rows[1:]:
        name = row[name_column]
        payload = payloads.get(name)
        if payload is None:
            raise DepositError(f"MANIFEST.tsv names a missing table: {name}")
        if len(payload) != int(row[byte_column]):
            raise DepositError(f"size differs from MANIFEST.tsv: {name}")
        if sha256_of(payload) != row[hash_column]:
            raise DepositError(f"sha256 differs from MANIFEST.tsv: {name}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="repository root (default: the parent of tools/)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="where to write the archives (default: <root>/build/deposits)",
    )
    arguments = parser.parse_args(argv)

    root = arguments.root.resolve()
    output_dir = arguments.output_dir or root / "build" / "deposits"
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        data_archive, data_checksum = build_data_deposit(root, output_dir)
        trajectory_archive, trajectory_checksum = build_trajectory_deposit(root, output_dir)
    except DepositError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    for path, checksum in (
        (data_archive, data_checksum),
        (trajectory_archive, trajectory_checksum),
    ):
        print(f"{path if not path.is_relative_to(root) else path.relative_to(root)}")
        print(f"  bytes  {path.stat().st_size}  ({human_size(path.stat().st_size)})")
        print(f"  sha256 {checksum}")
    print("Quote both sha256 values in the Zenodo record descriptions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
