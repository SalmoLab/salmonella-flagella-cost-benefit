#!/usr/bin/env python3
"""Reproduce revised Figure 5C."""

import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[4]
subprocess.run(
    [sys.executable, "analyses/figure_05_revision/build.py", "--panel", "C"],
    cwd=PROJECT,
    check=True,
)
