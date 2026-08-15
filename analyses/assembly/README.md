# Deterministic composite-figure assembly

Assembly is performed in Python from project-relative SVG panel inputs. The
assembler namespaces imported SVG identifiers, preserves vector paths and
editable text, and records dimensions and placement in YAML. PNG and PDF review
exports are rendered from the assembled SVG with CairoSVG; no manual edits are
permitted afterward.

Seven partial assembly targets are currently available: Figures 1, 2, 4 and 5,
and Supplementary Figures 1, 4 and 5. Placeholder boxes identify missing assets
or collaborator sources. Figure 3 and Supplementary Figures 2-3 remain
status-only targets; generating pictures for them before source intake would
fabricate provenance. All assemblies remain layout/integration tests rather than
final manuscript replacements because their raw-data chains or formal visual
acceptance are incomplete.

Run from the collection root:

```bash
.venv/bin/python tools/assemble_available_figures.py --root .
.venv/bin/python tools/organize_build.py --root .
```

Each available figure writes an editable SVG and checksum-bearing JSON manifest
under its own `build/figures/<figure_name>/` directory. All ten figure
directories also contain a truthful `status.json`. PNG/PDF assembly exports
require the Python CairoSVG runtime;
the current macOS machine has an incompatible x86_64 Cairo library, so those
formats remain an explicit local render blocker and are expected to be tested
in the supplied container or CI.
