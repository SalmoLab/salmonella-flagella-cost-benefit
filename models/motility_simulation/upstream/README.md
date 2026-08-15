# Salmonella Motility Simulation

[![Linting](https://github.com/MPUSP/salmonella-motility-simulation/actions/workflows/linting.yml/badge.svg)](https://github.com/MPUSP/salmonella-motility-simulation/actions/workflows/linting.yml)
[![Testing](https://github.com/MPUSP/salmonella-motility-simulation/actions/workflows/testing.yml/badge.svg)](https://github.com/MPUSP/salmonella-motility-simulation/actions/workflows/testing.yml)
[![pages-build-deployment](https://github.com/MPUSP/salmonella-motility-simulation/actions/workflows/pages/pages-build-deployment/badge.svg)](https://github.com/MPUSP/salmonella-motility-simulation/actions/workflows/pages/pages-build-deployment)

An agent-based, standalone 2D single-cell motility simulation for flagellated bacteria.

![](data/screencast.gif)

This project contains Python scripts to simulate single-cell movement in various predefined conditions.
These conditions are currently:

Strains:

- `PproA`
- `WT`
- `PproB`

Environments:

- `liquid`
- `agarose`

The project uses predefined parameters obtained from single cell measurements, see `data/motility_summary_parameters.csv`.
An arbitrary number of `phenotype` x `environment` combinations can be added by extending the input CSV file.
Note: This project does **not** infer or refit parameters from raw trajectory data.

## Contents

- `docs/`: [**Rendered web page with motility simulations**](https://MPUSP.github.io/salmonella-motility-simulation/ppro_tracks.html).
- `src/salmonella_motility_simulation/`: CLI entry point and simulation implementation, including classes, simulations, and plotting.
- `data/motility_summary_parameters.csv`: Strain-specific movement parameters.
- `data/config.yml`: Global movement and obstacle parameters.
- `output/`: Figures and tables as output from the simulation.
- `pyproject.toml`: Project configuration and dependencies.

## Usage

We use [Pixi](https://pixi.prefix.dev/latest/) to manage dependencies and define standard tasks for simulations. If you have Pixi installed, you can run the full simulation with:

```bash
pixi run simulation
```

To run specific functions or scripts, check out the enclosed environments and execute python scripts directly, e.g.:

```bash
pixi shell
python -m salmonella_motility_simulation --output output/ppro
```

## Scientific purpose

The goal of this script is to provide a model that is:

- more biologically interpretable than a pure active Brownian particle model,
- much simpler than a large multi-state transport engine,
- directly grounded in observed or pre-estimated summary motility parameters,
- easy to read, explain, and modify.

## Model overview

The model simulates the typical movement of flagellated bacteria in terms of subsequent pauses / tumbles / reorientation events:

### 1. Motile cells in run mode

Motile cells move with:

- a phenotype- and medium-specific run speed,
- gradual angular decorrelation through rotational diffusion,
- a stochastic chance of entering a reorientation state.

In this state, the cell performs the visually dominant long displacements in the
simulation.

### 2. Reorientation state

Cells occasionally pause or strongly slow down for a short time.

During this state:

- translational motion is weak,
- the state lasts for a short random duration,
- when the state ends, the heading changes by a random turn angle.

### 3. Non-motile cells

A phenotype- and medium-specific fraction of cells are permanently non-motile
throughout the simulation.

These cells:

- never enter active run mode,
- undergo only weak passive diffusion,
- contribute short, local trajectories.

### Liquid vs. agarose environment

The agarose condition adds one explicit environmental interaction:

- the environment contains static, non-overlapping circular obstacles,
- cells are not initialized inside obstacles,
- if a motile cell overlaps an obstacle after a proposed move, it is projected
  back to the obstacle surface.

After contact, the cell either:

- slides tangentially along the obstacle with reduced displacement, or
- enters a short stalled state with a phenotype-specific probability.

## What the model deliberately does not include

This project represents an **illustrative but data-grounded track generator**.
For reasons of simplicity, the model does currently **not** include:

- chemotaxis,
- cell-cell interactions,
- hydrodynamics,
- wall accumulation,
- phenotype switching,
- source-target transport metrics,
- pore-network reconstruction,
- direct fitting to raw trajectories.

### Model parameters

All strain-specific parameters are stored in `data/motility_summary_parameters.csv`.

- `motile_fraction`: Fraction of cells that are assigned to the motile subpopulation at the start of the simulation.
- `run_speed_um_s`: Speed of a motile cell during run mode, in micrometers per second.
- `rotational_diffusion_rad2_s`: Angular diffusion coefficient controlling how quickly the heading wanders during run mode. Higher values produce more curved and less persistent trajectories.
- `reorientation_rate_s`: Rate at which a running cell enters the reorientation state.
- `reorientation_duration_s`: Mean duration of a single reorientation event.
- `turn_angle_sd_rad`: Standard deviation of the heading change applied when reorientation ends.
- `passive_diffusion_um2_s`: Weak translational diffusion used for non-motile cells, reorientation motion, and stalled motion.
- `stall_probability`: In agarose only, probability that an obstacle contact leads to a short stall instead of tangent sliding.
- `stall_mean_duration_s`: Mean duration of a stall event in agarose.

## Authors

- Concept & initial draft: Marc Erhardt, Maria Giralt Zuniga (Humboldt University Berlin, MPUSP)
- Code review, restructuring, editing: Michael Jahn (MPUSP)

The initial draft was created with assistance of a large language model (LLM).

## Citation

Coming soon.
