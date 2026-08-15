SHELL := /bin/bash
.DEFAULT_GOAL := inventory

PROJECT_ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
VENV_PYTHON := $(PROJECT_ROOT)/.venv/bin/python
SNAKEFILE := $(PROJECT_ROOT)/workflow/Snakefile
export PYTHONPATH := $(PROJECT_ROOT)/src

.PHONY: bootstrap inventory organize reproduce-available reproduce audit source-data-available figure-qa supplementary-information software-versions clean-room clean test

bootstrap:
	$(PROJECT_ROOT)/scripts/bootstrap_environment.sh
	$(VENV_PYTHON) -m flagella_repro bootstrap --root $(PROJECT_ROOT)

inventory:
	@test -x $(VENV_PYTHON) || { echo "Environment missing; run 'make bootstrap' first." >&2; exit 2; }
	$(VENV_PYTHON) -m flagella_repro inventory --root $(PROJECT_ROOT)

organize:
	@test -x $(VENV_PYTHON) || { echo "Environment missing; run 'make bootstrap' first." >&2; exit 2; }
	$(VENV_PYTHON) $(PROJECT_ROOT)/tools/organize_build.py --root $(PROJECT_ROOT)

reproduce-available:
	@test -x $(VENV_PYTHON) || { echo "Environment missing; run 'make bootstrap' first." >&2; exit 2; }
	$(VENV_PYTHON) -m flagella_repro preflight --root $(PROJECT_ROOT) --mode available
	$(VENV_PYTHON) -m snakemake --snakefile $(SNAKEFILE) --directory $(PROJECT_ROOT) --cores 1 --forceall --config mode=available
	$(VENV_PYTHON) $(PROJECT_ROOT)/tools/assemble_available_figures.py --root $(PROJECT_ROOT)
	$(VENV_PYTHON) $(PROJECT_ROOT)/tools/organize_build.py --root $(PROJECT_ROOT)
	@echo "Available reproduction completed. See build/workflow/available_reproduction.json for executed, partial, blocked, and missing panels."

reproduce:
	@test -x $(VENV_PYTHON) || { echo "Environment missing; run 'make bootstrap' first." >&2; exit 2; }
	$(VENV_PYTHON) -m flagella_repro preflight --root $(PROJECT_ROOT) --mode strict
	$(VENV_PYTHON) -m snakemake --snakefile $(SNAKEFILE) --directory $(PROJECT_ROOT) --cores 1 --forceall --config mode=strict

audit:
	@test -x $(VENV_PYTHON) || { echo "Environment missing; run 'make bootstrap' first." >&2; exit 2; }
	$(VENV_PYTHON) -m flagella_repro audit --root $(PROJECT_ROOT)

source-data-available:
	@test -x $(VENV_PYTHON) || { echo "Environment missing; run 'make bootstrap' first." >&2; exit 2; }
	$(VENV_PYTHON) $(PROJECT_ROOT)/tools/build_source_data_workbook.py --root $(PROJECT_ROOT)

figure-qa:
	@test -x $(VENV_PYTHON) || { echo "Environment missing; run 'make bootstrap' first." >&2; exit 2; }
	$(VENV_PYTHON) $(PROJECT_ROOT)/tools/run_figure_qa.py --root $(PROJECT_ROOT)

supplementary-information:
	@test -x $(VENV_PYTHON) || { echo "Environment missing; run 'make bootstrap' first." >&2; exit 2; }
	$(VENV_PYTHON) $(PROJECT_ROOT)/tools/build_supplementary_information.py --root $(PROJECT_ROOT)

software-versions:
	@test -x $(VENV_PYTHON) || { echo "Environment missing; run 'make bootstrap' first." >&2; exit 2; }
	$(VENV_PYTHON) $(PROJECT_ROOT)/tools/build_software_versions.py --root $(PROJECT_ROOT)

clean-room:
	@test -x $(VENV_PYTHON) || { echo "Environment missing; run 'make bootstrap' first." >&2; exit 2; }
	$(VENV_PYTHON) -m flagella_repro clean-room --root $(PROJECT_ROOT)

clean:
	@test -x $(VENV_PYTHON) || { echo "Environment missing; run 'make bootstrap' first." >&2; exit 2; }
	$(VENV_PYTHON) -m flagella_repro clean --root $(PROJECT_ROOT)

test:
	@test -x $(VENV_PYTHON) || { echo "Environment missing; run 'make bootstrap' first." >&2; exit 2; }
	$(VENV_PYTHON) -m pytest
