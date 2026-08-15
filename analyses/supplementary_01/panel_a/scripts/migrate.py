from pathlib import Path

from analyses.figure_02.panel_c.scripts.migrate import run

if __name__ == "__main__":
    run(Path(__file__).resolve().parents[1] / "config" / "config.json")
