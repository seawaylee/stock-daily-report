"""
Generate AI Image Prompts for Trend Model Tables
- Indices Table: fish_basin_indices_prompt.txt
- Sectors Table: fish_basin_sectors_prompt.txt
Style: Hand-drawn vintage illustration
"""
import pandas as pd
from datetime import datetime
import os

def generate_table_prompt(df, title_suffix, output_filename, date_dir):
    """Generate hand-drawn style table prompt."""
    
    # Split by status
    bullish = df[df['状态'] == 'YES']
    bearish = df[df['状态'] == 'NO']
    
    # Format table rows
    def format_row(row, rank):
        name = row['名称']
        status = "●" if row['状态'] == 'YES' else "○"
        dev = row['偏离率']
        interval = row['区间涨幅%']
        signal_date = row['状态变量时间']
        return f"{rank}. {status} {name} | 偏离率: {dev} | 信号日: {signal_date} | 期间涨幅: {interval}"
    
    bull_rows = [format_row(r, i+1) for i, (_, r) in enumerate(bullish.head(12).iterrows())]
    bear_rows = [format_row(r, i+1) for i, (_, r) in enumerate(bearish.head(5).iterrows())]
    
    prompt = f"""(masterpiece, best quality), (hand drawn), (illustration), (vintage style), (ink sketch), (vertical 10:16), (warm paper texture)

**SUBJECT**: A hand-drawn financial ranking chart titled "**AI量化趋势模型 · {title_suffix}**"

**HEADER**:
- Title: "**AI量化趋势模型**" in bold Chinese calligraphy brush style
- Subtitle: "**{title_suffix}** | {datetime.now().strftime('%Y.%m.%d')}"
- Style: Red-gold ink brush strokes on aged paper background

---

**TABLE DESIGN**:

**Style**: Hand-drawn vintage ranking list
- Background: Warm aged paper texture (sepia, cream)
- Lines: Ink brush strokes, slightly uneven for organic feel
- Text: Black ink calligraphy for Chinese, neat handwritten numbers
- Accents: Red circles for bullish (●), hollow circles for bearish (○)

**Column Headers** (Draw as a header row):
| 排名 | 名称 | 偏离率 | 信号日 | 期间涨幅 |

---

**SECTION 1: 趋势向上** (Bullish - Above SMA20)

Draw each row as a handwritten entry with:
- A RED filled circle (●) on the left
- Sector/Index name in bold brush calligraphy
- 偏离率 (Deviation) in RED ink
- 信号日 (Signal Date) in black ink
- 期间涨幅 (Interval Change) in RED ink

{chr(10).join(bull_rows)}

---

**SECTION 2: 趋势向下** (Bearish - Below SMA20)

Draw each row with:
- A HOLLOW circle (○) on the left
- Name in lighter/grey ink
- 偏离率 in GREEN ink
- 期间涨幅 in GREEN ink

{chr(10).join(bear_rows) if bear_rows else "(无)"}

---

**VISUAL ELEMENTS**:
1. **Divider Lines**: Horizontal ink brush strokes between sections
2. **Ranking Numbers**: Hand-drawn numerals with slight ink bleed effect
3. **Corner Decorations**: Simple ink brush accents (waves, clouds, or geometric)
4. **Status Legend**: Small legend at top: "● 趋势向上  ○ 趋势向下"

**FOOTER**:
- Hand-drawn banner at bottom
- Text: "**点赞关注  每日发布趋势模型**"
- Style: Elegant brush calligraphy, centered, with decorative underline

**TYPOGRAPHY**:
- All Chinese text: Traditional brush calligraphy style
- Numbers: Neat handwritten, slightly slanted
- Colors: Black ink primary, Red for positive, Green for negative, Gold accents

**ATMOSPHERE**:
- Warm, inviting, hand-crafted feel
- Like a traditional Chinese newspaper financial section
- Professional yet artistic

(Optimized for AI: Hand-drawn aesthetic with legible Chinese text. Vertical 10:16 format. Focus on clean table structure with brush stroke elements.)
"""
    
    # Save prompt
    output_file = f"{date_dir}/{output_filename}"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    print(f"✅ Saved: {output_file}")
    return prompt


def generate_all_prompts(date_str=None):
    """Generate both indices and sectors prompts."""
    if date_str is None:
        date_str = datetime.now().strftime('%Y%m%d')
    
    date_dir = f"results/{date_str}"
    
    # 1. Indices
    try:
        df_indices = pd.read_excel(f"{date_dir}/fish_basin_report.xlsx")
        generate_table_prompt(df_indices, "指数榜", "fish_basin_indices_prompt.txt", date_dir)
    except Exception as e:
        print(f"⚠️ Indices prompt failed: {e}")
    
    # 2. Sectors
    try:
        df_sectors = pd.read_excel(f"{date_dir}/fish_basin_sectors.xlsx")
        generate_table_prompt(df_sectors, "题材榜", "fish_basin_sectors_prompt.txt", date_dir)
    except Exception as e:
        print(f"⚠️ Sectors prompt failed: {e}")
    
    print("\n✅ All prompts generated!")


if __name__ == "__main__":
    import sys
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    generate_all_prompts(date_arg)
