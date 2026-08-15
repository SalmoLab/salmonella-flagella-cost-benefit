"""Documented protein-to-sector overrides for the proteomics panels.

The collaborator assigns every protein to one sector through its KEGG maps.  A
few proteins carry a flagellar map for a reason that is not flagellar: RpoD is
the primary sigma factor and appears on the flagellar-assembly map, RbsB is a
ribose-transport subunit and appears on the chemotaxis map.  Both are flat
across the promoter series, so counting them as flagellar fills the bars of the
low-flagella strains with protein that does not respond to flagellar demand.

The corrections live in ``config/protein_sector_overrides.csv`` with a ``reason``
column, not in code.  Figure 4 and Supplementary Figure 2 both read this one
table, so the two figures cannot disagree about which sector a protein is in.

Example:
    >>> proteins = apply_sector_overrides(pd.read_csv(delivered_export))
    >>> proteins.loc[proteins.uniprot_id == "P0A2E3", "sector_short"].unique()
    array(['Oth'], dtype=object)

The override is applied once, at the protein level, by every loader.  Sector
totals are then summed from the overridden protein table, so no downstream table
can carry the delivered assignment.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

OVERRIDE_TABLE = Path(__file__).resolve().parent / "config" / "protein_sector_overrides.csv"
REQUIRED_COLUMNS = (
    "uniprot_id",
    "gene_name_short",
    "delivered_sector_short",
    "override_sector_short",
    "override_sector",
    "reason",
)


def load_sector_overrides() -> pd.DataFrame:
    """Return the documented sector overrides, one row per protein."""
    table = pd.read_csv(OVERRIDE_TABLE)
    missing = [column for column in REQUIRED_COLUMNS if column not in table.columns]
    if missing:
        raise ValueError(f"{OVERRIDE_TABLE} lacks required columns: {missing}")
    if table.uniprot_id.duplicated().any():
        raise ValueError(f"{OVERRIDE_TABLE} lists a protein twice")
    blank = table.reason.fillna("").str.strip().eq("")
    if blank.any():
        raise ValueError(f"{OVERRIDE_TABLE} has an override without a reason")
    return table


def apply_sector_overrides(proteins: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of a protein-level table with the overrides applied.

    The delivered sector of every overridden protein is checked first.  A
    delivery that no longer matches the recorded ``delivered_sector_short``
    raises, so a silently re-annotated export cannot pass through unnoticed.
    """
    updated = proteins.copy()
    for row in load_sector_overrides().itertuples():
        rows = updated.uniprot_id.eq(row.uniprot_id)
        if not rows.any():
            raise ValueError(f"override protein {row.uniprot_id} is absent from the delivery")
        delivered = set(updated.loc[rows, "sector_short"].unique())
        if delivered != {row.delivered_sector_short}:
            raise ValueError(
                f"override protein {row.uniprot_id} is delivered in {sorted(delivered)}, "
                f"but the override records {row.delivered_sector_short!r}"
            )
        updated.loc[rows, "sector_short"] = row.override_sector_short
        if "sector" in updated.columns:
            updated.loc[rows, "sector"] = row.override_sector
    return updated
