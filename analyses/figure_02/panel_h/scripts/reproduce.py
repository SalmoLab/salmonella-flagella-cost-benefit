from pathlib import Path
import runpy

module = runpy.run_path(str(Path(__file__).resolve().parents[4] / "analyses/collaborator_science/build_panels.py"))
module["build"]("F2_H")
