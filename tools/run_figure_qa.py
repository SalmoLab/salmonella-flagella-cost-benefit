#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from flagella_repro.figure_qa import audit_graphics


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    result = audit_graphics(args.root)
    print(json.dumps(result, indent=2, sort_keys=True))
    if (
        result["star_text_failures"]
        or result["editable_text_failures"]
        or result["small_font_failures"]
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
