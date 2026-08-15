# Reproducible computational environment

## Contract

The canonical runtime is CPython 3.12.11. Python package resolution is frozen in
`uv.lock`; the lock file, `pyproject.toml`, and the container base-image digest are
part of the scientific provenance. `requirements.lock` is a hash-pinned,
pip-compatible export of all runtime, workflow, test, and developer dependency groups.
`uv.lock` remains authoritative. Analyses must not depend on a workstation-global
Python installation.

The environment enforces the following deterministic defaults:

- UTC timezone and `C.UTF-8` locale;
- `PYTHONHASHSEED=0`;
- non-interactive Matplotlib rendering through `Agg`;
- one numerical thread for OpenBLAS, OpenMP, MKL, and NumExpr.

Panel-specific stochastic algorithms must additionally receive an explicit seed from
their tracked configuration. The global settings do not replace panel-level seeds.

## Local bootstrap

From the collection root, run:

```bash
./scripts/bootstrap_environment.sh
```

The script uses uv 0.8.11. If that exact version is not installed, it downloads a
temporary, version-pinned uv executable without modifying the shell profile. uv then
installs CPython 3.12.11 when necessary and creates `.venv` from `uv.lock` with
`--frozen`. It then installs the local project as a regular wheel because macOS File
Provider repeatedly reapplies `UF_HIDDEN` to uv's editable `.pth` file in this
workspace, causing CPython to skip it. The Make interface explicitly exports the
current `src/` tree through `PYTHONPATH`, so tests and workflow commands always use
live canonical code; standalone environment commands use the wheel produced during
bootstrap. Every documented release and clean-room sequence begins with bootstrap.
The temporary uv bootstrap directory is removed when the script exits.

After bootstrapping, use the executables in `.venv/bin`. `uv run --frozen` is also
valid when uv 0.8.11 is installed on `PATH`. Do not use bare `python` or `pip` commands
in workflow rules or provenance records.

Basic verification:

```bash
.venv/bin/python --version
.venv/bin/python -m snakemake --version
.venv/bin/python -m pytest
```

`make reproduce-available` forces a fresh execution of every panel whose
canonical `analyses/**/metadata/provenance.json` is valid and declares
`partial_reproduction` or `reproduced`. It verifies recorded input checksums before
execution and recorded output checksums afterward. The resulting workflow manifest
is explicit about panels that could not be run. This command returning zero therefore
means "all currently executable workflows passed", not "the manuscript is fully
reproducible". Only `make reproduce` is the full-collection acceptance command.

## Container

The Dockerfile pins both its Python and uv image indexes by SHA-256 digest. Build and
inspect the environment with:

```bash
docker build --tag flagella-manuscript-repro:0.1.0-dev .
docker run --rm flagella-manuscript-repro:0.1.0-dev
```

The image runs analyses as the unprivileged user `reproducibility`. A clean-room run
must prefetch and checksum external data, then execute the reproduction with network
access disabled. The workflow command is supplied by the Make/Snakemake layer rather
than hard-coded into the image.

## Dependency policy

- Add direct runtime dependencies to `[project.dependencies]`.
- Add workflow, test, or developer tools to the corresponding dependency group.
- Regenerate `uv.lock` only as an explicit, reviewed environment change using uv
  0.8.11 and CPython 3.12.11.
- Regenerate `requirements.lock` from the accepted `uv.lock`; never resolve or edit it
  independently:

  ```bash
  uv export --frozen --all-groups --no-emit-project \
    --format requirements-txt --no-header --no-annotate
  ```

  Preserve the three explanatory header lines in the tracked export.
- Record the old and new lock-file hashes and rerun numerical and visual regression
  tests after every dependency change.
- Do not add packages merely because they occur in a historical script; canonical
  migrated code must prove that it imports and uses them.

The accepted collaborator model uses GEKKO 1.3.2; that exact solver package is now
part of the canonical lock. The vendored source defaults to local solving
(`remote=False`). Unseeded historical parameter sampling is not rerun as part of the
canonical panel build; the accepted fixed parameter set and final result tables are
preserved separately.

## System dependencies

The container includes only the native libraries required for headless scientific
plotting, common raster formats, SVG rendering, and numerical linear algebra. Image
analysis tools such as Fiji, ilastik, or Omnipose require separately pinned workflows
if their outputs become direct inputs to the figure build; do not silently rely on a
desktop installation.
