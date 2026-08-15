# Collaborator science panels

`build_panels.py` is the canonical Python 3.12 producer for F2G-H, F3A-G, S2A and S3A. It consumes the checksum-frozen protein-level proteomics and fixed cell-economy result tables under `data/external/`, writes every plotted value under `data/source_data/<panel_id>/`, and exports PNG/SVG/PDF under `build/panels/<panel_id>/`.

Run all eleven panels with `.venv/bin/python3.12 analyses/collaborator_science/build_panels.py --panel all`, or pass one exact panel ID. Panel-local READMEs link back to this shared producer. The exact source intake, numerical gates and remaining raw-data/solver limitations are documented in `docs/SCIENTIFIC_SOURCE_INTAKE_2026-08-12.md`.
