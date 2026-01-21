#!/bin/bash

# Configuration
# ----------------
# Standardize the python environment for all scripts in this repo.
PYTHON_PATH="/Users/seawaylee/opt/anaconda3/envs/py311/bin/python"
export PYTHONPATH=$PYTHONPATH:.

# Validation
# ----------------
if [ ! -f "$PYTHON_PATH" ]; then
    echo "Error: Python executable not found at $PYTHON_PATH"
    echo "Please ensure the 'py311' conda environment is created."
    exit 1
fi



USAGE="Usage: ./run.sh [all | fish_basin | b1 | sector_flow | ladder]"

if [ -z "$1" ]; then
    echo "========================================================"
    echo "$USAGE"
    echo "========================================================"
    echo "Modules:"
    echo "  all          : Run all 4 modules in PARALLEL"
    echo "  fish_basin   : [Module 1] Trend Analysis (Indices + Sectors)"
    echo "  b1           : [Module 2] B1 Stock Selection & AI Analysis"
    echo "  sector_flow  : [Module 3] Sector Funds Flow"
    echo "  ladder       : [Module 4] Market Limit-up Ladder"
    echo "========================================================"
    exit 1
fi

# Forward args to main.py
"$PYTHON_PATH" main.py "$@"



