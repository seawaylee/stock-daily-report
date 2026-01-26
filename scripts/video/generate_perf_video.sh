#!/bin/bash

# Configuration
# ----------------
# 1. Determine Date
if [ -z "$1" ]; then
    TARGET_DATE=$(date +"%Y%m%d")
else
    TARGET_DATE="$1"
fi

echo "🎬 Generatng Performance Video for Date: $TARGET_DATE"

# 2. Check Input File
PROMPT_FILE="results/$TARGET_DATE/AI提示词/业绩掘金_Prompt.txt"
if [ ! -f "$PROMPT_FILE" ]; then
    echo "❌ Error: Prompt file not found at $PROMPT_FILE"
    echo "   Please run the python data collection first."
    exit 1
fi

# 3. Parse Data to JSON
echo "🔍 Parsing Data..."
/usr/bin/python3 scripts/video/parse_performance_prompt.py "$TARGET_DATE"

if [ $? -ne 0 ]; then
    echo "❌ Data parsing failed."
    exit 1
fi

# 4. Render Video
echo "🎥 Rendering Video (PerformanceVideo)..."
cd remotion-video
# Fixed: removed recursive argument
npm run render-perf

if [ $? -eq 0 ]; then
    echo "✅ Success! Video saved to remotion-video/performance.mp4"
    open performance.mp4
else
    echo "❌ Rendering failed."
    exit 1
fi
