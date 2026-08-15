#!/usr/bin/env python3
"""Freeze a collaborator delivery without inspecting or modifying its contents."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from flagella_repro.external_intake import freeze_delivery


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Checksum and freeze one external delivery before inspection."
    )
    parser.add_argument("payload", type=Path, help="file or directory exactly as delivered")
    parser.add_argument("--source-id", required=True, help="ID from config/external_sources.csv")
    parser.add_argument(
        "--received-date",
        type=date.fromisoformat,
        default=date.today(),
        help="delivery date in YYYY-MM-DD format (default: today)",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="reproducibility collection root",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    delivery_dir = freeze_delivery(
        project_root=args.project_root,
        source=args.payload,
        source_id=args.source_id,
        received_date=args.received_date,
    )
    print(f"Frozen immutable intake: {delivery_dir}")


if __name__ == "__main__":
    main()
