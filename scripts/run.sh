#!/bin/bash

# Configuration
# ----------------
# Determine Python Interpreter
# ----------------------------
# 1. Try loading from local .env file (for machine-specific overrides)
if [ -f ".env" ]; then
    source .env
fi

# 2. Try to activate Conda environment 'py311'
# Default conda base path for this user based on recent checks
CONDA_BASE="$HOME/opt/anaconda3"

# If not found there, try other common locations
if [ ! -f "$CONDA_BASE/etc/profile.d/conda.sh" ]; then
     # Try home directory anaconda3
     if [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
         CONDA_BASE="$HOME/anaconda3"
     # Try user NikoBelic path (legacy)
     elif [ -f "/Users/NikoBelic/anaconda3/etc/profile.d/conda.sh" ]; then
         CONDA_BASE="/Users/NikoBelic/anaconda3"
     fi
fi

if [ -f "$CONDA_BASE/etc/profile.d/conda.sh" ]; then
    source "$CONDA_BASE/etc/profile.d/conda.sh"
    # Try stock311 first, then py311
    conda activate stock311 2>/dev/null || conda activate py311
    
    if [ $? -eq 0 ]; then
        PYTHON_PATH=$(which python)
        echo "✅ Activated Conda Env: py311 ($PYTHON_PATH)"
    else
        echo "❌ Failed to activate Conda environment 'py311'"
        # Fallback to direct path execution if activation fails
        PYTHON_PATH="$CONDA_BASE/envs/py311/bin/python"
        if [ -f "$PYTHON_PATH" ]; then
             echo "⚠️  Fallback: Using direct python path: $PYTHON_PATH"
        else
             exit 1
        fi
    fi
else
    # Fallback to system or direct paths if conda.sh not found
    if [ -z "$PYTHON_PATH" ]; then
         # Check known paths
         POSSIBLE_PATHS=(
            "$HOME/opt/anaconda3/envs/py311/bin/python"
            "$HOME/anaconda3/envs/py311/bin/python"
            "/Users/NikoBelic/anaconda3/envs/stock311/bin/python"
         )
         for path in "${POSSIBLE_PATHS[@]}"; do
            if [ -f "$path" ]; then
                PYTHON_PATH="$path"
                break
            fi
        done
    fi
    
    if [ -z "$PYTHON_PATH" ] && command -v python3 &> /dev/null; then
        PYTHON_PATH=$(command -v python3)
    fi
    echo "⚠️  Conda profile not found. Using: $PYTHON_PATH"
fi

export PYTHONPATH=$PYTHONPATH:.




USAGE="Usage: ./run.sh [all | fish_basin | b1 | sector_flow | ladder | calendar | abnormal | jin10]"

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
    echo "  calendar     : [Module 5] Market Calendar (Tomorrow & Next Week)"
    echo "  abnormal     : [Module 6] Abnormal Fluctuation Alert"
    echo "  jin10        : [Module 7] Jin10 Economic Monitor"
    echo "========================================================"
    exit 1
fi

# Forward args to main.py
"$PYTHON_PATH" main.py "$@"



