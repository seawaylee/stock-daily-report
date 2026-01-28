"""
Generate Combined AI Image Prompt for Fish Basin Trend Model
Combines Indices and Sectors into a single hand-drawn vintage style chart.
"""
import pandas as pd
from datetime import datetime
import os

def generate_combined_prompt(date_str=None, df_index=None, df_sector=None):
    if date_str is None:
        date_str = datetime.now().strftime('%Y%m%d')
    
    date_dir = f"results/{date_str}"
    prompt_dir = os.path.join(date_dir, "AI提示词")
    os.makedirs(prompt_dir, exist_ok=True)
    
    output_filename = "趋势模型_合并_Prompt.txt"
    output_path = os.path.join(prompt_dir, output_filename)
    
    try:
        # Load Data if not provided
        if df_index is None:
             try: df_index = pd.read_excel(f"{date_dir}/趋势模型_指数.xlsx")
             except: pass
        if df_sector is None:
             try: df_sector = pd.read_excel(f"{date_dir}/趋势模型_题材.xlsx")
             except: pass
             
        if df_index is None and df_sector is None:
            print("❌ Missing Index AND Sector data. Cannot generate prompt.")
            return None
        
        # Helper to format rows
        def process_df(df):
            # Ensure proper types
            df['dev_val'] = df['黄线偏离率'].astype(str).str.rstrip('%').astype(float)
            return df.sort_values('dev_val', ascending=False)
            
        df_index = process_df(df_index) if df_index is not None else pd.DataFrame()
        df_sector = process_df(df_sector) if df_sector is not None else pd.DataFrame()
        
        def format_row(row, rank):
            name = row['名称']
            status = "●" if row['状态'] == 'YES' else "○"
            
            # Fields
            daily_chg = row['涨幅%']
            dev = row['黄线偏离率']
            interval_chg = row['区间涨幅%']
            
            # Rank Change logic
            rank_chg = str(row.get('排名变化', '-'))
            if rank_chg == 'nan': rank_chg = '-'
            rank_icon = ""
            if rank_chg.startswith('+'): rank_icon = f"▲{rank_chg}"
            elif rank_chg.startswith('-') and rank_chg != '-': rank_icon = f"▼{rank_chg[1:]}"
            elif rank_chg == '新': rank_icon = "★NEW"
            else: rank_icon = "-"
            
            # Cross Days logic
            cross_days = ""
            if '金叉天数' in row and str(row['金叉天数']) != '-':
                cross_days = f"金叉{row['金叉天数']}天"
            elif '死叉天数' in row and str(row['死叉天数']) != '-':
                cross_days = f"死叉{row['死叉天数']}天"
            
            # Determines color tag helper
            def get_color_tag(val_str):
                try:
                    # Strip % and convert to float
                    val = float(str(val_str).strip('%'))
                    if val > 0: return "[RED]"
                    elif val < 0: return "[GREEN]"
                    else: return "" # Zero is neutral, or maybe grey
                except:
                    return ""

            chg_color = get_color_tag(daily_chg)
            dev_color = get_color_tag(dev)
            interval_color = get_color_tag(interval_chg)
            
            # Format: Rank. Status Name | Chg | Dev | Interval | Cross | RankChg
            return f"{rank}. {status} {name} | 涨跌:{chg_color}{daily_chg} | 偏离:{dev_color}{dev} | 区间:{interval_color}{interval_chg} | {cross_days} | 排名:{rank_icon}"

        # Generate Rows
        if not df_index.empty:
            index_rows = [format_row(r, i+1) for i, (_, r) in enumerate(df_index.head(15).iterrows())]
        else:
            index_rows = ["(No Index Data Available)"]

        if not df_sector.empty:
            sector_rows = [format_row(r, i+1) for i, (_, r) in enumerate(df_sector.head(20).iterrows())] # Top 20 sectors
        else:
            sector_rows = []
        
        # Build Prompt
        prompt = f"""(masterpiece, best quality), (hand drawn), (illustration), (vintage style), (ink sketch), (vertical 10:16), (warm paper texture)

**SUBJECT**: A comprehensive hand-drawn financial ranking chart titled "**AI量化趋势模型日报 · {datetime.now().strftime('%Y.%m.%d')}**"

**HEADER**:
- Title: "**AI量化趋势模型**" in bold Chinese calligraphy
- Date: "{datetime.now().strftime('%Y.%m.%d')} | 市场全景扫描"
- Style: Red-gold ink brush strokes on aged paper

---

**LAYOUT**:
The chart is divided into two main sections by a decorative horizontal divider.

**SECTION 1: 核心指数趋势** (Indices Trend)
*Header*: "════ 核心指数 ════" in bold calligraphy

Layout: A list of key market indices ranked by trend strength.
**Color Rules**:
- **RED ink** for Positive values (Starts with + or no sign)
- **GREEN ink** for Negative values (Starts with -)
- **Highlight**: Any row with "金叉1天" or "死叉1天" should be emphasized with a yellow highlight marker effect.

**Content Columns**:
[排名 名称 | 今日涨跌 | 长线偏离 | 区间涨幅 | 金叉/死叉 | 排名变化]

**Data**:
{chr(10).join(index_rows)}

---

---

**SECTION 2: 热门题材趋势** (Top Sectors Trend)
{f'''*Header*: "════ 热门题材 ════" in bold calligraphy

Layout: Top 20 ranking sectors sorted by trend strength.
Style: Same color rules apply.

**Content Columns**:
[排名 名称 | 今日涨跌 | 长线偏离 | 区间涨幅 | 金叉/死叉 | 排名变化]

**Data**:
{chr(10).join(sector_rows)}''' if sector_rows else '(No Sector Data Available)'}

---

**FOOTER**:
- Text: "**总结不易，每天收盘后推送，点赞关注不迷路！**"
- Style: Centered, smaller font, warm greetings style

---

**VISUAL ELEMENTS**:
1. **Paper Texture**: Authentic aged parchment paper background with slight creases
2. **Ink Style**: Traditional Chinese ink brush (Maobi) for titles, fine liner for data
3. **Color Palette**: 
   - Primary: Black ink
   - Bullish/Up: **Cinnabar Red**
   - Bearish/Down: **Jade Green**
   - Highlights: **Imperial Gold** wash
4. **Decorations**: Subtle mountain range sketch in the background (faint), cloud patterns at corners

**ATMOSPHERE**:
- Professional, historical, trustworthy
- "The wisdom of the trend"
- A fusion of ancient philosophy and modern data

(Optimized for AI: Hand-drawn chart, legible text structure, vintage aesthetic, accurate financial data representation)
"""

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(prompt)
            
        print(f"✅ Combined Prompt Saved: {output_path}")
        return prompt

    except Exception as e:
        print(f"❌ Failed to generate prompt: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    generate_combined_prompt()
