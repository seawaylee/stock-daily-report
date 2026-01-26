import re
import json
import os
import sys
from datetime import datetime

def parse_ladder_prompt(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split into sections by "### "
    # Regex to find sections like "### 18板 (1只)" or "### 首板 (92只)"
    sections = re.split(r'###\s+', content)
    
    ladder_data = []

    for section in sections[1:]:  # Skip preamble
        lines = section.split('\n')
        title_line = lines[0].strip()
        
        # Parse board count from title
        board_match = re.match(r'(.+?)\s*\((\d+)只\)', title_line)
        if board_match:
            board_name = board_match.group(1)
            count = int(board_match.group(2))
        else:
            continue

        # Find content inside ``` ```
        code_block = re.search(r'```(.*?)```', section, re.DOTALL)
        stocks = []
        if code_block:
            block_content = code_block.group(1).strip()
            # Remove empty lines
            block_lines = [line.strip() for line in block_content.split('\n') if line.strip()]
            
            for i in range(0, len(block_lines), 2):
                if i + 1 >= len(block_lines): break
                
                stock_row = block_lines[i]
                theme_row = block_lines[i+1]
                
                stock_tokens = stock_row.split()
                theme_tokens = theme_row.split()
                
                # Zip safely
                limit = min(len(stock_tokens), len(theme_tokens))
                
                for s, t in zip(stock_tokens[:limit], theme_tokens[:limit]):
                    is_yizi = '[一字]' in s
                    is_broken = '[X]' in s
                    clean_name = s.replace('[一字]', '').replace('[X]', '')
                    
                    stocks.append({
                        "name": clean_name,
                        "theme": t,
                        "is_yizi": is_yizi,
                        "is_broken": is_broken
                    })
        
        ladder_data.append({
            "board": board_name,
            "count": count,
            "stocks": stocks
        })

    return ladder_data

def main():
    # Dynamic Date: Default to today (YYYYMMDD) or arg
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    else:
        target_date = datetime.now().strftime("%Y%m%d")

    prompt_path = f"/Users/seawaylee/Documents/github/stock-daily-report/results/{target_date}/AI提示词/涨停天梯_Prompt.txt"
    output_dir = "/Users/seawaylee/Documents/github/stock-daily-report/remotion-video/public"
    output_path = os.path.join(output_dir, "ladder_data.json")

    print(f"Targeting Prompt: {prompt_path}")

    # Ensure output dir exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    data = parse_ladder_prompt(prompt_path)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Success! Data saved to {output_path}")

if __name__ == "__main__":
    main()
