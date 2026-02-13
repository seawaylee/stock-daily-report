#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

# Load local environment variables if present.
if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

PYTHON_BIN=""

# Try conda env first for dependency consistency.
CONDA_BASE="${CONDA_BASE:-$HOME/opt/anaconda3}"
if [ ! -f "${CONDA_BASE}/etc/profile.d/conda.sh" ] && [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
  CONDA_BASE="$HOME/anaconda3"
fi
if [ ! -f "${CONDA_BASE}/etc/profile.d/conda.sh" ] && [ -f "/Users/NikoBelic/anaconda3/etc/profile.d/conda.sh" ]; then
  CONDA_BASE="/Users/NikoBelic/anaconda3"
fi

if [ -f "${CONDA_BASE}/etc/profile.d/conda.sh" ]; then
  # shellcheck disable=SC1091
  source "${CONDA_BASE}/etc/profile.d/conda.sh"
  conda activate stock311 2>/dev/null || conda activate py311 2>/dev/null || true
  PYTHON_BIN="$(command -v python || true)"
fi

if [ -z "${PYTHON_BIN}" ]; then
  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  else
    PYTHON_BIN="$(command -v python)"
  fi
fi

exec "${PYTHON_BIN}" scripts/after_close_workflow.py "$@"
