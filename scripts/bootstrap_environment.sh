#!/usr/bin/env bash
set -euo pipefail

readonly REQUIRED_UV_VERSION="0.8.11"
readonly REQUIRED_PYTHON_VERSION="3.12.11"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

task_tmp_dir=""
uv_bin=""
cleanup() {
  if [[ -n "${task_tmp_dir}" && -d "${task_tmp_dir}" ]]; then
    rm -rf -- "${task_tmp_dir}"
  fi
}
trap cleanup EXIT

select_uv() {
  if command -v uv >/dev/null 2>&1; then
    local installed_version
    installed_version="$(uv --version | awk '{print $2}')"
    if [[ "${installed_version}" == "${REQUIRED_UV_VERSION}" ]]; then
      uv_bin="$(command -v uv)"
      return 0
    fi
  fi

  if ! command -v curl >/dev/null 2>&1; then
    echo "curl is required to bootstrap uv ${REQUIRED_UV_VERSION}." >&2
    return 1
  fi

  task_tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/flagella-uv.XXXXXX")"
  local uv_install_dir="${task_tmp_dir}/bin"
  mkdir -p "${uv_install_dir}"
  curl --fail --location --silent --show-error \
    "https://astral.sh/uv/${REQUIRED_UV_VERSION}/install.sh" \
    | env UV_INSTALL_DIR="${uv_install_dir}" UV_NO_MODIFY_PATH=1 sh >/dev/null
  uv_bin="${uv_install_dir}/uv"
}

main() {
  select_uv
  if [[ "$("${uv_bin}" --version | awk '{print $2}')" != "${REQUIRED_UV_VERSION}" ]]; then
    echo "Failed to select uv ${REQUIRED_UV_VERSION}." >&2
    exit 1
  fi

  export UV_PROJECT_ENVIRONMENT="${PROJECT_ROOT}/.venv"

  "${uv_bin}" python install "${REQUIRED_PYTHON_VERSION}"
  "${uv_bin}" sync \
    --project "${PROJECT_ROOT}" \
    --frozen \
    --python "${REQUIRED_PYTHON_VERSION}" \
    --all-groups

  # CPython skips editable .pth files when this macOS workspace reapplies the
  # UF_HIDDEN flag. Install the local project as a regular wheel after the
  # frozen dependency sync so standalone environment commands remain reliable.
  # The Make interface sets PYTHONPATH to src/ and therefore always exercises
  # live canonical code during development and workflow execution.
  "${uv_bin}" pip install \
    --python "${PROJECT_ROOT}/.venv/bin/python" \
    --no-deps \
    --force-reinstall \
    "${PROJECT_ROOT}"

  "${PROJECT_ROOT}/.venv/bin/python" - <<'PY'
import sys

import flagella_repro

expected = (3, 12)
if sys.version_info[:2] != expected:
    raise SystemExit(f"Expected Python {expected[0]}.{expected[1]}, got {sys.version}")
print(sys.version)
print(f"flagella_repro import: {flagella_repro.__file__}")
PY

  "${PROJECT_ROOT}/.venv/bin/python" -m snakemake --version
  echo "Environment ready at ${PROJECT_ROOT}/.venv"
}

main "$@"
