#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
涨停阶梯图 AI绘图Prompt 自动生成器
每天运行生成当日的prompt文件
"""

import os
from datetime import datetime
from collections import Counter
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))) # Add project root
from modules.market_ladder.limit_up_ladder import get_limit_up_data, repair_board_counts, process_ladder_data
from common.image_generator import generate_image_from_text

def get_raw_image_prompt(date_str):
    display_date = f"{date_str[4:6]}月{date_str[6:8]}日"
    prompt = (
        f"Hand-drawn infographic poster, Chinese A-share stock market limit-up ladder chart, {display_date}. "
        f"Style: Warm cream paper texture, vintage notebook aesthetic, handwritten Chinese fonts. "
        f"Visual elements: Ladder structure table, red tags for limit-up stocks, hot sectors list. "
        f"Layout: 9:16 vertical, title '{display_date} A股涨停复盘'. "
        f"Atmosphere: Professional, detailed financial analysis. "
        f"--ar 9:16 --style raw --v 6"
    )
    return prompt

def generate_podcast_text(date_str, ladder, top_inds):
    """
    生成播客文稿
    """
    display_date = f"{date_str[4:6]}月{date_str[6:8]}日"

    # Statistics
    total_stocks = sum(len(items) for items in ladder.values())
    first_board = len(ladder.get(1, []))
    lian_board = total_stocks - first_board

    highest_board = max(ladder.keys()) if ladder else 0
    highest_stock = ladder[highest_board][0]['name'] if ladder and ladder.get(highest_board) else "无"

    text = f"""大家好，我是量化小万。今天是{display_date}，为您带来A股涨停天梯复盘。

首先来看整体数据：今天全市场共有{total_stocks}只涨停股。其中，首板{first_board}只，连板股{lian_board}只。

高度方面，今天的最高板是{highest_board}板，由{highest_stock}领衔。

题材热度方面，排名前三的板块分别是：
"""

    for i, (ind, cnt) in enumerate(top_inds[:3]):
        text += f"第{i+1}名，{ind}，共有{cnt}只涨停。\n"

    text += f"""
值得注意的是，市场的高标股表现往往代表了短线资金的风向，建议投资者密切关注{highest_stock}及其所在板块的持续性。

以上就是今天的涨停复盘，我们下期再见。
"""
    return text

def run(date_str=None, output_dir=None):
    """
    生成涨停阶梯的AI绘图Prompt (Wrapper for generate_ladder_prompt)
    """
    return generate_ladder_prompt(date_str, output_dir)

def generate_ladder_prompt(date_str=None, output_dir=None):
    """
    生成涨停阶梯的AI绘图Prompt + 播客文稿 + 自动生图
    """
    if date_str is None:
        date_str = datetime.now().strftime('%Y%m%d')

    if output_dir is None:
        output_dir = f"results/{date_str}"

    os.makedirs(output_dir, exist_ok=True)

    # 获取数据
    print(f"正在获取 {date_str} 涨停数据...")
    df_zt, df_fried, df_prev = get_limit_up_data(date_str)

    if df_zt is None:
        print("无法获取数据")
        return None

    df_zt = repair_board_counts(df_zt, date_str)
    ladder = process_ladder_data(df_zt, df_fried, df_prev)

    # 统计题材
    all_industries = []
    for items in ladder.values():
        for item in items:
            ind = item.get('industry', '')
            if ind and ind != '--':
                all_industries.append(ind)
    top_inds = Counter(all_industries).most_common(8)

    # 格式化日期显示
    display_date = f"{date_str[4:6]}月{date_str[6:8]}日"

    # 生成prompt内容 (Markdown)
    prompt_lines = []
    prompt_lines.append(f"# {date_str} A股涨停阶梯 - AI绘图Prompt (完整数据)")
    prompt_lines.append("")
    prompt_lines.append("## 图片规格")
    prompt_lines.append("- 比例: 9:16 竖版")
    prompt_lines.append("- 风格: 手绘/手账风格，暖色纸张质感")
    prompt_lines.append("- 背景色: #F5E6C8 纸黄色")
    prompt_lines.append("")
    prompt_lines.append("> **⚠️ 重要：必须画出所有股票！除非单个板块超过100只才可截断。**")
    prompt_lines.append("")
    prompt_lines.append("> **⚠️ 注意：每只股票包含2个元素！**")
    prompt_lines.append("> 1. **股票名**（粗体黑色）- 如 锋龙股份")
    prompt_lines.append("> 2. **题材**（下方小字 **必须红色** Red Color）- 如 电网设备")
    prompt_lines.append(">")
    prompt_lines.append("> **特殊标记**：")
    prompt_lines.append("> - **[一字]** = 红色喜庆标签，表示一字涨停")
    prompt_lines.append("> - **[X]** = 红色叉号，表示炸板或断板")
    prompt_lines.append("")
    prompt_lines.append("## 标题")
    prompt_lines.append(f'**{display_date} A股涨停复盘** （"涨停"红色）')
    prompt_lines.append("")
    
    # 热门题材
    prompt_lines.append("## 热门题材 (TOP8)")
    prompt_lines.append("> **颜色要求**: 题材文字全部使用 **红色** (Red Ink)")
    ind_strs = [f"{ind}({cnt})" for ind, cnt in top_inds]
    prompt_lines.append(" | ".join(ind_strs))
    prompt_lines.append("")
    prompt_lines.append("---")
    prompt_lines.append("")
    prompt_lines.append("## 涨停阶梯完整数据")
    prompt_lines.append("格式: 股票名(上, 黑色) / 题材(下, **红色**)")
    prompt_lines.append("")
    
    # 各板数据
    for board, items in sorted(ladder.items(), reverse=True):
        # 统计状态
        success_count = sum(1 for i in items if i['status'] == 'success')
        failed_count = len(items) - success_count
        
        status_note = ""
        if failed_count > 0 and board > 1:
            fried = sum(1 for i in items if i['status'] == 'fried')
            broken = sum(1 for i in items if i['status'] == 'broken')
            parts = []
            if fried > 0: parts.append(f"{fried}炸板")
            if broken > 0: parts.append(f"{broken}断板")
            if parts:
                status_note = f" - {'+'.join(parts)}"
        
        board_name = "首板" if board == 1 else f"{board}板"
        prompt_lines.append(f"### {board_name} ({len(items)}只){status_note}")
        prompt_lines.append("```")
        
        # 按封板时间排序 (一字最前，然后按时间升序，断板最后)
        def sort_key(item):
            time_str = item['time'] or ''
            if item['status'] != 'success':
                return (2, '')  # 失败的放最后
            if time_str == '一字':
                return (0, '')  # 一字最前
            return (1, time_str)  # 按时间排序
        
        sorted_items = sorted(items, key=sort_key)
        
        # 限制每层最多显示100只 (用户需求)
        if len(sorted_items) > 100:
            original_count = len(sorted_items)
            sorted_items = sorted_items[:100]
            status_note += f" (显示前100只，共{original_count}只)"
        
        # 格式化股票数据 - 只显示股票名和题材，不显示时间
        col_limit = 5 if board == 1 else 4
        
        for row_start in range(0, len(sorted_items), col_limit):
            row_items = sorted_items[row_start:row_start + col_limit]
            
            names = []
            inds = []
            
            for item in row_items:
                # 一字用红色标签，失败用[X]
                if item['time'] == '一字' and item['status'] == 'success':
                    prefix = "[一字]"
                elif item['status'] != 'success':
                    prefix = "[X]"
                else:
                    prefix = ""
                
                name = f"{prefix}{item['name']}"
                ind = item['industry'] if item['industry'] else ''
                
                # 对齐 (每列约12字符宽)
                names.append(f"{name:^12}")
                inds.append(f"{ind:^12}")
            
            prompt_lines.append("".join(names))
            prompt_lines.append("".join(inds))
            prompt_lines.append("")
        
        prompt_lines.append("```")
        prompt_lines.append("")
    
    # AI绘图Prompt英文版
    prompt_lines.append("---")
    prompt_lines.append("")
    prompt_lines.append("## AI绘图Prompt (English)")
    prompt_lines.append("")
    prompt_lines.append(f"Hand-drawn infographic poster, Chinese A-share stock market limit-up ladder chart, {display_date}.")
    prompt_lines.append("")
    prompt_lines.append("**Style**: Warm cream paper texture (#F5E6C8), vintage notebook aesthetic, handwritten Chinese fonts.")
    prompt_lines.append("")
    prompt_lines.append("**Layout (9:16 vertical)**:")
    prompt_lines.append(f'- Title: "{display_date} A股涨停复盘" (涨停 in red)')
    prompt_lines.append("- Hot sectors row below title")
    prompt_lines.append("- **Outer table structure**: horizontal lines separate different board levels (14板, 6板, etc.), left column shows board label")
    prompt_lines.append(f"- **Within each board**: stocks flow freely in rows")
    prompt_lines.append("")
    prompt_lines.append("**Stock display format (CRITICAL COLORS)**:")
    prompt_lines.append("```")
    prompt_lines.append(" [Stock Name]  (In BOLD BLACK ink)")
    prompt_lines.append("  [Industry]   (In SMALL **RED** ink underneath)")
    prompt_lines.append("```")
    prompt_lines.append("Example: **锋龙股份** (Black) / 电网设备 (Red)")
    prompt_lines.append("")
    prompt_lines.append("**Special markers**:")
    prompt_lines.append("- **[一字]** = Festive RED badge, means sealed at open and never opened (best performers)")
    prompt_lines.append("- **[X]** = RED cross/X mark over stock name, means failed (炸板/断板)")
    prompt_lines.append("")
    
    # 统计
    total_stocks = sum(len(items) for items in ladder.values())
    first_board_count = len(ladder.get(1, []))
    highest_board = max(ladder.keys())
    highest_stock = ladder[highest_board][0]['name'] if ladder.get(highest_board) else "N/A"
    
    prompt_lines.append("**Key highlights**:")
    prompt_lines.append(f"- {highest_board}板: {highest_stock} - highest streak")
    if top_inds:
        prompt_lines.append(f"- {top_inds[0][0]} dominates with {top_inds[0][1]} stocks")
    prompt_lines.append(f"- Total {total_stocks} stocks ({first_board_count} first-time + {total_stocks - first_board_count} 连板)")
    prompt_lines.append(f"- Note: Suspension days are ignored in consecutive limit calculation (e.g. 锋龙股份)")
    prompt_lines.append("")
    prompt_lines.append("---")
    prompt_lines.append("")
    prompt_lines.append("## 底部标语")
    prompt_lines.append("**总结不易，每天收盘后推送，点赞关注不迷路！**")
    prompt_lines.append("")
    prompt_lines.append("（居中显示，小字，温馨提示风格）")
    
    # 保存文件到子文件夹
    prompt_dir = os.path.join(output_dir, "AI提示词")
    os.makedirs(prompt_dir, exist_ok=True)
    
    output_path = os.path.join(prompt_dir, "涨停天梯_Prompt.txt")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(prompt_lines))

    print(f"Prompt已生成: {output_path}")

    # --- New: Automate Podcast Text Generation ---
    podcast_dir = os.path.join(output_dir, "podcast_inputs")
    os.makedirs(podcast_dir, exist_ok=True)
    podcast_text = generate_podcast_text(date_str, ladder, top_inds)
    podcast_file = os.path.join(podcast_dir, "market_ladder.txt")
    with open(podcast_file, 'w', encoding='utf-8') as f:
        f.write(podcast_text)
    print(f"🎙️ Podcast text saved to: {podcast_file}")

    # --- New: Automate Image Generation ---
    raw_prompt = get_raw_image_prompt(date_str)
    image_dir = os.path.join(output_dir, "images")
    os.makedirs(image_dir, exist_ok=True)
    image_path = os.path.join(image_dir, "market_ladder_cover.png")

    print("\n🎨 Generating Market Ladder Cover Image...")
    generate_image_from_text(raw_prompt, image_path)

    return output_path


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
    else:
        date_str = datetime.now().strftime('%Y%m%d')
    
    run(date_str)
