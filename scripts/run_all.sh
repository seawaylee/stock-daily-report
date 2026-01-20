export PYTHONPATH=$PYTHONPATH:.

echo "=== Running Fish Basin Indices ==="
conda run -n py311 python modules/fish_basin/fish_basin.py

echo "\n=== Running Fish Basin Sectors ==="
conda run -n py311 python modules/fish_basin/fish_basin_sectors.py
