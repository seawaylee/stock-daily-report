"""
[Module 8] Weekly Events Preview Generator
Generates:
1. Next Week's Major Events Preview Markdown
2. Next Week's Events Image Prompt (Hand-drawn Sketch Style)
"""
import pandas as pd
from datetime import datetime, timedelta
import os


def get_next_week_dates(date_str):
    """Get date strings for next week (Monday to Friday)"""
    dt = datetime.strptime(date_str, '%Y%m%d')
    
    # Find next Monday
    days_ahead = 0 - dt.weekday() + 7
    if dt.weekday() >= 5:  # Sat or Sun
        days_ahead = 7 - dt.weekday()
    
    next_mon = dt + timedelta(days=days_ahead)
    dates = [(next_mon + timedelta(days=i)) for i in range(5)]
    return dates


def check_is_weekend(date_str):
    """Check if date is Friday, Saturday, or Sunday"""
    dt = datetime.strptime(date_str, '%Y%m%d')
    return dt.weekday() >= 4


def generate_weekly_preview_content(start_date, end_date):
    """Generate the content for next week's major events preview"""
    
    # This is a template structure. In production, you would:
    # 1. Fetch from financial calendar API
    # 2. Parse major conference/policy events
    # 3. Use AI to generate sector analysis
    
    # For now, return a template that matches the structure we created
    content = {
        'dates': [],
        'summary': f"业绩预告冲刺 + 宏观靴子落地 + 政策催化密集期"
    }
    
    # Example structure for 5 days
    # In real implementation, fetch actual events
    return content


def generate_weekly_preview_markdown(date_str, output_dir):
    """Generate Weekly Preview Markdown Document"""
    dt = datetime.strptime(date_str, '%Y%m%d')
    
    if not check_is_weekend(date_str):
        print("Not weekend mode, skipping weekly preview generation.")
        return None
    
    print(f"Generating Weekly Events Preview for week starting {date_str}...")
    
    dates = get_next_week_dates(date_str)
    start_date = dates[0]
    end_date = dates[-1]
    
    # Format dates for display
    start_disp = start_date.strftime('%m.%d')
    end_disp = end_date.strftime('%m.%d')
    
    # Create markdown content (template - should be filled with actual events)
    markdown_content = f"""# 📅 下周大事件前瞻：节前关键博弈周

**时间范围：** {start_date.strftime('%Y.%m.%d')} ~ {end_date.strftime('%m.%d')}  
**核心逻辑：** 业绩预告冲刺 + 宏观靴子落地 + 政策催化密集期

---

## {start_date.strftime('%m月%d日')} 周一

### 📣 事件：[待填充 - 实际事件名称]

**看点：** [事件核心关注点]

**🔥 影响板块：** [相关板块]

**🎯 核心标的：**
- **标的1 (代码):** 逻辑说明
- **标的2 (代码):** 逻辑说明

---

## {dates[1].strftime('%m月%d日')} 周二

### 📣 事件：[待填充]

**看点：** [核心关注点]

**🔥 影响板块：** [相关板块]

**🎯 核心标的：**
- **标的1:** 说明

---

## {dates[2].strftime('%m月%d日')} 周三

### 📣 事件：[待填充]

**看点：** [核心关注点]

**🔥 影响板块：** [相关板块]

**🎯 核心标的：**
- **标的1:** 说明

---

## {dates[3].strftime('%m月%d日')} 周四

### 📣 事件：[待填充 - 关注宏观事件如美联储决议]

**看点：** [核心关注点]

**🔥 影响板块：** [相关板块]

**🎯 核心标的：**
- **标的1:** 说明

---

## {dates[4].strftime('%m月%d日')} 周五

### 📣 事件：[待填充 - 关注业绩预告截止日]

**看点：** [核心关注点]

**🔥 影响板块：** [相关板块]

**🎯 核心标的：**
- **标的1:** 说明

---

## 💡 制作提示

### 视觉优化建议
1. **标红重点：** 重大宏观事件日期用红色标注
2. **信息层级：** 使用不同字号区分事件、板块、标的三个层级
3. **图标运用：** 每个日期配专属icon

### 合规性声明
*本文仅供事件梳理和市场分析，不构成投资建议。股市有风险，投资需谨慎。*

---

**📊 策略建议：**
- **防守型：** 关注有色金属与高股息板块
- **进攻型：** 重点关注AI应用与智能驾驶
- **平衡型：** 分散配置，业绩预增+政策催化双主线
"""
    
    # Save markdown
    md_path = os.path.join(output_dir, f"weekly_preview_{date_str}.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    print(f"Saved Markdown: {md_path}")
    
    return markdown_content


def generate_weekly_preview_prompt(date_str, output_dir):
    """Generate Weekly Preview Image Prompt (Hand-drawn Sketch Style)"""
    dt = datetime.strptime(date_str, '%Y%m%d')
    
    if not check_is_weekend(date_str):
        print("Not weekend mode, skipping weekly preview prompt generation.")
        return None
    
    print(f"Generating Weekly Events Preview Image Prompt...")
    
    dates = get_next_week_dates(date_str)
    start_date = dates[0]
    end_date = dates[-1]
    
    # Create image prompt following the same style as other prompts
    prompt_content = f"""(masterpiece, best quality), (vertical:1.2), (aspect ratio: 10:16), (sketch style), (hand drawn), (infographic)

A TALL VERTICAL PORTRAIT IMAGE (Aspect Ratio 10:16) HAND-DRAWN SKETCH style weekly events preview infographic poster.

**LAYOUT & COMPOSITION:**
- **Canvas**: 1600x2560 vertical.
- **Background**: Hand-drawn warm paper texture (#F5E6C8) with faint blue-gold gradient pencil strokes.
- **Top Section**: 
  - Left: A cute hand-sketched Robot mascot wearing a blue scarf, holding a calendar in one hand and a telescope in the other, with an alert expression.
  - Right: A speech bubble with text: "节前关键博弈周！美联储决议+业绩预告双重考验，防守反击是主旋律💪"
  - Center Title: "下周大事件前瞻：节前关键博弈周" and date range "{start_date.strftime('%m.%d')}~{end_date.strftime('%m.%d')}" in bold hand-lettered font.
  - Subtitle: "核心逻辑：业绩预告冲刺 + 宏观靴子落地"

**MAIN CONTENT - 5 EVENT CARDS (Single Column):**
- **Card Style**: Hand-drawn rounded rectangles with visible pencil outlines, alternating between pale blue and pale yellow paper texture backgrounds.
- **SPECIAL HIGHLIGHTING**: Important dates (e.g., FOMC decision day) should have RED border and RED date text.

**Card Content Template (Hand-written text):**

1. **📅 {dates[0].strftime('%m月%d日')} 周一 | [事件主题]**
   **事件**: [具体事件名称]
   💡 看点: [核心关注点]
   📊 影响板块: [板块1] / [板块2]
   🎯 核心标的: [标的1(逻辑)] [标的2(逻辑)]

[Repeat for all 5 days...]

**FOOTER SECTION:**
- **Footer Text 1 (Summary) - DEEP BLUE COLOR (#2C5F8D)**: "本周宏观与微观双重考验：[具体分析内容]。防守型关注[板块]，进攻型布局[板块]。"
- **Footer Text 2 (Strategy) - DEEP GOLD COLOR (#B8860B)**: "重点关注：周一[板块]（[标的]）、周三[板块]（[标的]）、周四[板块]（[标的]）、周五[板块]（[标的]）。"
- **Footer Text 3 (CTA) - DEEP RED COLOR (#C41E3A)**: "每周盘前分享大事件前瞻，掌握交易节奏不迷路。次日关注进场，提前布局高确定性机会🚀"
- **Footer Text 4 (Disclaimer) - CHARCOAL GREY (#6B6B6B)**: "*本文仅供事件梳理，不构成投资建议，股市有风险*"

**VISUAL HIERARCHY:**
- **Level 1 (Largest)**: Date + Event Name
- **Level 2 (Medium)**: "看点"、"影响板块"
- **Level 3 (Small)**: Stock names and brief descriptions

**ART STYLE DETAILS:**
- **Lines**: Charcoal and graphite pencil strokes, varying thickness, slight wobbles for authenticity.
- **Shading**: Crosshatching and stippling only. NO smooth digital gradients.
- **Texture**: Heavy paper grain visible throughout the image.
- **Color Palette**: Vintage hues - faded blue, deep gold, warm yellow, charcoal grey, alert red for special events.
- **Icons**: Hand-drawn calendar icons, dollar sign for macro events, warning triangle for risk days, graph icons, target icons.
- **Special Elements**: 
  * Draw small "⚠️" warning icons next to critical dates
  * Draw small "💣" bomb icon next to earnings disclosure deadlines

(Optimized for high-quality vector-style sketch render with professional financial infographic layout)
"""
    
    # Save prompt following naming convention: [module]_image_prompt.txt or weekly_preview_prompt_YYYYMMDD.txt
    prompt_path = os.path.join(output_dir, f"weekly_preview_prompt_{date_str}.txt")
    with open(prompt_path, 'w', encoding='utf-8') as f:
        f.write(prompt_content)
    print(f"Saved Image Prompt: {prompt_path}")
    
    return prompt_content


def run(date_str, output_dir, run_weekly=None):
    """
    Main entry point for Weekly Preview module.
    
    Args:
        date_str: Date in YYYYMMDD format
        output_dir: Output directory path (e.g., results/20260124)
        run_weekly: Force run weekly mode (None = auto-detect based on weekday)
    """
    if run_weekly is None:
        run_weekly = check_is_weekend(date_str)
    
    if not run_weekly:
        print("⏭️ Skipping Weekly Preview (Not weekend mode)")
        return False
    
    print("\n=== [Module 8] Weekly Events Preview ===")
    
    # Generate both markdown and image prompt
    generate_weekly_preview_markdown(date_str, output_dir)
    generate_weekly_preview_prompt(date_str, output_dir)
    
    print("✅ Weekly Preview generation completed.")
    return True
