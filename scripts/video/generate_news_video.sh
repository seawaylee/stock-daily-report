#!/bin/bash

# Configuration
if [ -z "$1" ]; then
    TARGET_DATE=$(date +"%Y%m%d")
else
    TARGET_DATE="$1"
fi

echo "🎬 Generatng News Video for Date: $TARGET_DATE"

PROMPT_FILE="results/$TARGET_DATE/AI提示词/核心要闻_Prompt.txt"

# 1. Generate Data if missing
if [ ! -f "$PROMPT_FILE" ]; then
    echo "⚠️  Prompt file not found. Running Core News Monitor..."
    /usr/bin/python3 main.py core_news --date "$TARGET_DATE"
    
    if [ ! -f "$PROMPT_FILE" ]; then
        echo "❌ Error: Failed to generate prompt file."
        exit 1
    fi
fi

# 2. Parse Data to JSON
echo "🔍 Parsing Data..."
/usr/bin/python3 scripts/video/parse_news_prompt.py "$TARGET_DATE"

if [ $? -ne 0 ]; then
    echo "❌ Data parsing failed."
    exit 1
fi

# 3. Render Video
echo "🎥 Rendering Video (NewsVideo)..."
cd remotion-video
# Render NewsVideo composition
npx remotion render src/index.tsx NewsVideo news.mp4 --concurrency=1

if [ $? -eq 0 ]; then
    echo "✅ Success! Video saved to remotion-video/news.mp4"
    open news.mp4
else
    echo "❌ Rendering failed."
    exit 1
fi
