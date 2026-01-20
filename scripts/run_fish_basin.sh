#!/bin/bash

# Define the Python path for the 'py311' environment
PYTHON_PATH="/Users/seawaylee/opt/anaconda3/envs/py311/bin/python"

# Check if the executable exists
if [ ! -f "$PYTHON_PATH" ]; then
    echo "Error: Python executable not found at $PYTHON_PATH"
    echo "Please ensure the 'py311' conda environment is created."
    exit 1
fi

echo "🐟 Running Fish Basin Model v2.0 using py311..."
export PYTHONPATH=$PYTHONPATH:.
"$PYTHON_PATH" modules/fish_basin/fish_basin.py
