import subprocess
import sys
from pathlib import Path

panel = Path(__file__).resolve().parents[1].name.removeprefix("panel_").upper()
subprocess.run(
    [sys.executable, str(Path(__file__).resolve().parents[2] / "build_supplementary_05.py"),
     "--panel", panel],
    check=True,
)
