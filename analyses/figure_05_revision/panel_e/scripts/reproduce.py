#!/usr/bin/env python3
"""Reproduce revised Figure 5E, including all deterministic simulation seeds."""

import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[4]
subprocess.run(
    [sys.executable, "analyses/figure_05_revision/build.py", "--panel", "E", "--force-simulation"],
    cwd=PROJECT,
    check=True,
)
