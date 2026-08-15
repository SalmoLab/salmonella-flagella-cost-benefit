#!/usr/bin/env python3
"""Reproduce revised Figure 5D, including all deterministic simulation seeds."""

import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[4]
subprocess.run(
    [sys.executable, "analyses/figure_05_revision/build.py", "--panel", "D", "--force-simulation"],
    cwd=PROJECT,
    check=True,
)
