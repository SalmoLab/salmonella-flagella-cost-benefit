from pathlib import Path

from ...plotting import render

if __name__ == "__main__":
    render(Path(__file__).parents[1] / "config" / "config.json")
