import re
import json
import os
import sys

def parse_performance_prompt(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Define sections and their regex markers
    # 🚀 盈利增速TOP5 (预增王) -> Growth
    # 🔄 扭亏为盈TOP5 (翻身仗) -> Turnaround
    # 📉 盈转亏TOP5 (业绩变脸) -> LossTurn
    # 💣 亏损扩大TOP5 (避雷区) -> LossExpansion

    sections = [
        {"key": "growth", "marker": "🚀 盈利增速TOP5"},
        {"key": "turnaround", "marker": "🔄 扭亏为盈TOP5"},
        {"key": "loss_turn", "marker": "📉 盈转亏TOP5"},
        {"key": "loss_expand", "marker": "💣 亏损扩大TOP5"},
    ]

    result = {
        "title": "A股业绩风云榜",
        "date": "01月26日",
        "sections": []
    }

    # Split content by markers roughly? 
    # Or just scan line by line.
    
    # Let's use regex to find blocks.
    # Block starts with ### [Marker] and ends with ```
    
    for section in sections:
        # Construct regex: ### .*? Marker .*? \n ... ```(.*?)```
        # Note: Marker contains special chars, escape them? No, simple string match usually ok in python regex if no special chars.
        # "🚀" is fine.
        
        pattern = r"###.*?" + re.escape(section['marker']) + r".*?```(.*?)```"
        match = re.search(pattern, content, re.DOTALL)
        
        items = []
        if match:
            block = match.group(1).strip()
            # Parse lines
            # Format:
            # 南方精工 +1274%
            #   └─ 汽车零部件 | 108亿 | 3.35亿 | 2439万
            
            lines = [l.strip() for l in block.split('\n') if l.strip()]
            
            # They come in pairs usually, skipping headers/separators
            # Header: ..., --- lines are skipped.
            
            current_item = None
            
            for line in lines:
                if line.startswith("Header:") or line.startswith("---"):
                    continue
                
                # Check for "Name +Percentage"
                # Ex: 南方精工 +1274%
                # Or: 渤海租赁 -7592%
                
                name_match = re.match(r"^([\u4e00-\u9fa5A-Za-z0-9]+)\s+([+-]?\d+%?)", line)
                if name_match:
                    if current_item: items.append(current_item)
                    current_item = {
                        "name": name_match.group(1),
                        "change": name_match.group(2),
                        "details": "" # Will fill next line
                    }
                    continue
                
                if line.startswith("└─") and current_item:
                    # └─ 汽车零部件 | 108亿 | 3.35亿 | 2439万
                    details = line.replace("└─", "").strip()
                    parts = [p.strip() for p in details.split('|')]
                    current_item["industry"] = parts[0] if len(parts) > 0 else ""
                    current_item["market_cap"] = parts[1] if len(parts) > 1 else ""
                    current_item["profit"] = parts[2] if len(parts) > 2 else ""
                    current_item["last_profit"] = parts[3] if len(parts) > 3 else ""
            
            if current_item: items.append(current_item)
            
        result["sections"].append({
            "key": section["key"],
            "title": section["marker"].split(' ')[1], # e.g. "盈利增速TOP5"
            "subtitle": section["marker"].split('(')[1].replace(')', '') if '(' in section["marker"] else "",
            "items": items
        })

    return result

def main():
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    else:
        # Try to find today's folder
        # For demo, hardcode or auto detect?
        # User requested "今日", assuming 20260126 based on context.
        target_date = "20260126"

    prompt_path = f"/Users/seawaylee/Documents/github/stock-daily-report/results/{target_date}/AI提示词/业绩掘金_Prompt.txt"
    output_path = "/Users/seawaylee/Documents/github/stock-daily-report/remotion-video/public/performance_data.json"

    print(f"Targeting: {prompt_path}")
    data = parse_performance_prompt(prompt_path)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Success! Data saved to {output_path}")

if __name__ == "__main__":
    main()
