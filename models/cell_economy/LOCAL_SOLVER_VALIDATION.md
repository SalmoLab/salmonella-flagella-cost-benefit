# Local solver validation

Date: 12 August 2026

The exact vendored source, accepted `kinetic_params_2026.csv`, GEKKO 1.3.2, Python 3.12.11 and `remote=False` were used to attempt the F=5%, rotation-cost steady-state solve across the collaborator's 12-point substrate series.

The local APMonitor runtime reported that requested solver 3 was unsupported, fell back to APOPT, ran 609 iterations and ended with `@error: Solution Not Found`. Consequently, the delivered fixed-result tables—not a falsely claimed local re-solve—remain the canonical panel inputs. Reproducing the solver stage requires the collaborator's exact APMonitor/IPOPT runtime or a source-level numerical update that is scientifically reviewed against all supplied outputs.

The failure does not alter the verified downstream values; the supplied final tables reproduce the manuscript's static and gradient targets exactly.

## Remote solve, 13 August 2026

The model's author, Michael Jahn, reported on 13 August 2026 that he runs the model with `remote=True`, so the public APMonitor server solves it with IPOPT. We took that route the same day and it works.

Settings: GEKKO 1.3.2, `remote=True`, `server="https://apmonitor.com"`, solver 3 (IPOPT v3.12) server-side, Python 3.12.11 on macOS 26.6.1 arm64, parameters from `data/external/cell_economy_results/sampling/kinetic_params_2026.csv`. About 12 s per allocation.

Two host-level shims were needed. The GEKKO 1.3.2 default host `byu.apmonitor.com` no longer resolves, so the server is set explicitly. The CDN in front of apmonitor.com rejects the default urllib User-Agent with HTTP 403, so the client names itself `GEKKO/1.3.2 (python-urllib)`. Both are coded in `low_allocation_sweep.py`.

**The remote route reproduces the delivered tables.** The dynamic solve at 1%, 2%, 3%, 4% and 5% flagellar allocation matches `data/external/cell_economy_results/swimming/8500/dynamic_flag_*.csv` in final growth rate, distance and substrate concentration to within 1e-9 relative error. At 0.5% it reaches a different and better local optimum than the delivered table (1.7064 h⁻¹ against 1.6617 h⁻¹), which is expected of a non-convex NLP. The cell-economy solve is therefore independently reproduced. The delivered tables remain the canonical panel inputs; nothing in the figures was changed.

## Warm-start continuation, 14 August 2026

Command: `.venv/bin/python models/cell_economy/low_allocation_sweep.py --continuation`. Settings as above: GEKKO 1.3.2, `remote=True`, `server="https://apmonitor.com"`, solver 3 (IPOPT v3.12) server-side.

Each of the 21 allocation steps from 0% to 1% is solved three ways: from the cold initial guess the upstream model declares, from the accepted solution of the neighbour above, and from the accepted solution of the neighbour below. The attempt with the lowest solver objective is accepted. The warm start changes the initial guess and nothing else. It is applied inside `solve`, after every equation is built, because a GEKKO variable whose value is a list is a sequence and NumPy would broadcast it elementwise through the symbolic equations. The first node of each guess is overwritten with the declared value, so every initial condition stays exactly as `dynamic.py` sets it.

**All 21 steps solve.** The two cold failures of 13 August, 0.75% and 0.95%, both solve from a warm start above. The accepted trajectory at 1% reproduces `dynamic_flag_0.010.csv` to 1e-9 relative error across the whole time series.

**The scatter is not removed.** Three growth-rate reversals remain in the accepted curve, the largest a 5.3% drop between 0.25% and 0.30%. Each carries a distance reversal, in which the cell with more flagella ends farther from the source. Across the three initial guesses the solved endpoint of one allocation spreads by up to 27.6%. A warm start does not steer this problem onto one branch; at several steps it lands on a worse local optimum than the cold start does. Pinning the interior needs a global optimiser, not a better initial guess.

**The 0% step is robust.** With `alpha_Fla` fixed at 0 the cell cannot swim, the substrate stays at its initial 0.0911 mM, and the dynamic problem collapses onto a fixed-substrate steady state. The independent steady-state solve gives 1.0627 1/h; the dynamic plateau is 1.0634 1/h, a gap of 0.069%. The travelled distance stays at 8500 µm throughout.

Records: `build/statistics/Figure_5/A3/low_allocation_continuation_status.csv`, `low_allocation_continuation_attempts.csv`, and the 21 accepted trajectories under `data/processed/figure_05_revision/A3_trajectories/`.
