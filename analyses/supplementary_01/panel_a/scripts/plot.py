from pathlib import Path

from analyses.figure_02.panel_c.scripts.plot import render

if __name__ == "__main__":
    render(Path(__file__).resolve().parents[1] / "config" / "config.json")
