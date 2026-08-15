from pathlib import Path

from flagella_repro.population_growth import reproduce_population_panel

if __name__ == "__main__":
    reproduce_population_panel(Path(__file__).parents[1] / "config" / "panel.json")
