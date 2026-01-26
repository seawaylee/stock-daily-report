import re
import json
import os
import sys

def parse_news(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract Date
    date_match = re.search(r'\((\d{2}月\d{2}日)\)', content)
    date_str = date_match.group(1) if date_match else "今日"

    # Extract News Items
    # Format: - [HH:MM]【Type】 Title
    items = []
    
    # regex to match: - [22:15]【利多·低空】 title text
    pattern = re.compile(r'-\s*\[(\d{2}:\d{2})\]【(.*?)】\s*(.*)')
    
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        match = pattern.search(line)
        if match:
            time_str = match.group(1)
            tag_raw = match.group(2)
            title = match.group(3)
            
            # Determine type
            item_type = 'neutral'
            if '利多' in tag_raw:
                item_type = 'bull'
            elif '利空' in tag_raw:
                item_type = 'bear'
            
            # Clean tag? "利多·低空" -> "低空" maybe better for display?
            # Or keep full tag? "利多·低空"
            # Let's keep a simplified tag if it has '·', else keep as is
            display_tag = tag_raw
            if '·' in tag_raw:
                parts = tag_raw.split('·')
                if len(parts) > 1:
                    display_tag = parts[1] # "低空"
            else:
                display_tag = tag_raw # "利多" or "利空"

            items.append({
                "time": time_str,
                "tag_full": tag_raw,
                "tag": display_tag,
                "type": item_type,
                "title": title
            })
            
    return {
        "date": date_str,
        "items": items
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parse_news_prompt.py <YYYYMMDD>")
        sys.exit(1)

    target_date = sys.argv[1]
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Path to Prompt file
    prompt_path = os.path.join(base_dir, f"results/{target_date}/AI提示词/核心要闻_Prompt.txt")
    
    if not os.path.exists(prompt_path):
        print(f"Error: File not found: {prompt_path}")
        sys.exit(1)
        
    print(f"Targeting: {prompt_path}")
    data = parse_news(prompt_path)
    
    # Save to public/news_data.json
    output_path = os.path.join(base_dir, "remotion-video/public/news_data.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        
    print(f"Success! Data saved to {output_path}")
