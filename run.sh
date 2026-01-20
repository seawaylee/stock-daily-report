#!/bin/bash

# Configuration
# ----------------
# Standardize the python environment for all scripts in this repo.
PYTHON_PATH="/Users/seawaylee/opt/anaconda3/envs/py311/bin/python"

# Validation
# ----------------
if [ ! -f "$PYTHON_PATH" ]; then
    echo "Error: Python executable not found at $PYTHON_PATH"
    echo "Please ensure the 'py311' conda environment is created."
    exit 1
fi

if [ -z "$1" ]; then
    echo "========================================================"
    echo "Usage: ./run.sh <script_name.py> [args...]"
    echo "========================================================"
    echo "Examples:"
    echo "  ./run.sh run_ai_analysis.py"
    echo "  ./run.sh sector_flow.py"
    echo "========================================================"
    exit 1
fi

SCRIPT=$1
shift

# Execution
# ----------------
echo "🐍 Running $SCRIPT using py311..."
"$PYTHON_PATH" "$SCRIPT" "$@"
