#!/bin/bash

# Configuration
if [ -z "$1" ]; then
    TARGET_DATE=$(date +"%Y%m%d")
else
    TARGET_DATE="$1"
fi

echo "🎬 Generatng Market Summary Video for Date: $TARGET_DATE"

# Render Video
echo "🎥 Rendering Video (MarketSummaryVideo)..."
cd remotion-video
npx remotion render src/index.tsx MarketSummaryVideo summary.mp4 --concurrency=1

if [ $? -eq 0 ]; then
    echo "✅ Success! Video saved to remotion-video/summary.mp4"
    open summary.mp4
else
    echo "❌ Rendering failed."
    exit 1
fi
