#!/usr/bin/env python3
"""Reproduce revised Figure 4F."""

import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[4]
subprocess.run(
    [sys.executable, "analyses/figure_04_revision/build.py", "--panel", "F"],
    cwd=PROJECT,
    check=True,
)
