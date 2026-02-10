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
             
        # Support for Merged Excel (Single Sheet Parsing)
        if df_index is None or df_sector is None:
            merged_path = f"{date_dir}/趋势模型_合并.xlsx"
            if os.path.exists(merged_path):
                print(f"Reading from Merged Excel: {merged_path}")
                try:
                    df_all = pd.read_excel(merged_path)
                    # Find split points
                    # Separator usually contains '题材趋势' in the first column
                    # But the file has Title rows too.
                    # Column 0 is usually '代码' or '名称' depending on saving?
                    # Let's inspect column 0 values
                    
                    # Identify rows
                    # Indices are at valid rows until '题材趋势' separator
                    # We look for the row where any column has '题材趋势'
                    split_idx = -1
                    for idx, row in df_all.iterrows():
                        if '题材趋势' in str(row.iloc[0]):
                             split_idx = idx
                             break
                    
                    if split_idx != -1:
                        # Indices are before split (excluding title row 0 if it exists)
                        # Actually 'save_merged_excel' adds title at row 0: '指数趋势'
                        # So Index Data = Row 1 to split_idx-1 (exclusive of separator)
                        # Sector Data = Row split_idx+1 to End
                        
                        # Note: dataframe loaded with header=0 (first row as columns).
                        # But save_merged_excel puts '指数趋势' in the DATA body row 0?
                        # No, `to_excel(index=False)` writes headers.
                        # `save_merged_excel` creates `df_index_title` (Row 0 of data).
                        # So:
                        # Header (Code, Name...)
                        # Row 0: "=== Index Trend ==="
                        # Row 1...N: Index Data
                        # Row N+1: "=== Sector Trend ==="
                        # Row N+2...: Sector Data
                        
                        df_index = df_all.iloc[1:split_idx]
                        df_sector = df_all.iloc[split_idx+1:]
                        
                        # Filter out empty/title rows if any remain
                        df_index = df_index[df_index.iloc[:,0].astype(str).str.len() < 20] 
                        df_sector = df_sector[df_sector.iloc[:,0].astype(str).str.len() < 20]
                        print(f"Extracted {len(df_index)} Indices and {len(df_sector)} Sectors from Merged Excel.")
                except Exception as e:
                    print(f"Failed to parse Merged Excel: {e}")

             
        if df_index is None and df_sector is None:
            print("❌ Missing Index AND Sector data. Cannot generate prompt.")
            return None
        
        # Helper to format rows
        def process_df(df, is_sector=False):
            # Safe conversion helper
            def safe_convert_pct(series):
                return pd.to_numeric(series.astype(str).str.replace('+', '').str.rstrip('%'), errors='coerce')

            # Ensure proper types
            if '黄线偏离率' in df.columns:
                df['dev_val'] = safe_convert_pct(df['黄线偏离率'])
            else:
                df['dev_val'] = 0.0
            
            # For Sectors: Mix of Top Deviation AND Top Gainers
            if is_sector:
                try:
                    df['chg_val'] = safe_convert_pct(df['涨幅%'])
                    
                    # 1. Top Deviation (Trend Kings)
                    top_dev = df.sort_values('dev_val', ascending=False).head(20)
                    
                    # 2. Top Gainers (Today's Stars) - Force include Top 5 even if trend is weak
                    # Filter out those with NaN change
                    valid_gainers = df.dropna(subset=['chg_val'])
                    top_gainers = valid_gainers.sort_values('chg_val', ascending=False).head(5)
                    
                    # print(f"Top 5 Gainers Debug: {top_gainers[['名称', 'chg_val']].to_string()}")

                    # 3. Combine and Dedup
                    combined = pd.concat([top_dev, top_gainers]).drop_duplicates(subset=['名称'])
                    
                    # 4. Sort by Deviation for consistency (Trend Model)
                    # Or maybe put Gainers on top? No, "Trend Model" implies Trend Rank.
                    return combined.sort_values('dev_val', ascending=False).head(25) # Allow up to 25
                except Exception as e:
                    print(f"⚠️ Error processing sector mix: {e}")
                    return df.sort_values('dev_val', ascending=False)
            
            return df.sort_values('dev_val', ascending=False)
            
        df_index = process_df(df_index) if df_index is not None else pd.DataFrame()
        df_sector = process_df(df_sector, is_sector=True) if df_sector is not None else pd.DataFrame()

        # === AI Trend Analysis Task Generation ===
        try:
            if not df_sector.empty and 'dev_val' in df_sector.columns:
                # 1. Top 10 High Deviation (Strong Trend)
                top_dev = df_sector.sort_values('dev_val', ascending=False).head(10)
                # 2. Bottom 5 Low Deviation (Oversold/Weak)
                bot_dev = df_sector.sort_values('dev_val', ascending=True).head(5)

                # Format Data for LLM
                sector_text = "【High Deviation Sectors (Strong Trend)】\n"
                for _, row in top_dev.iterrows():
                    sector_text += f"- {row['名称']}: Dev {row['黄线偏离率']}, Chg {row['涨幅%']}, RankChg {row.get('排名变化','-')}\n"

                sector_text += "\n【Low Deviation Sectors (Weak/Oversold)】\n"
                for _, row in bot_dev.iterrows():
                    sector_text += f"- {row['名称']}: Dev {row['黄线偏离率']}, Chg {row['涨幅%']}, RankChg {row.get('排名变化','-')}\n"

                # Create Task Prompt
                task_prompt = f"""Analyze the sector trend data from the 'Fish Basin' model.
Identify 1 "Best Value" sector (Trend Up + Reasonable Deviation) and 1 "High Risk" sector (Extreme Deviation).
Output a VERY CONCISE summary (max 50 words) in Chinese.

Format:
📊 **AI趋势精选**: [Sector] (Reason) | ⚠️ **风险**: [Sector] (Reason)

Data:
{sector_text}
"""
                # Save Task File
                temp_dir = os.path.join(date_dir, "temp_data")
                os.makedirs(temp_dir, exist_ok=True)
                task_path = os.path.join(temp_dir, "task_trend_summary.txt")
                with open(task_path, "w", encoding="utf-8") as f:
                    f.write(task_prompt)
                print(f"✅ Agent Task Saved: {task_path}")

        except Exception as e:
            print(f"⚠️ Failed to generate agent task: {e}")
        # =========================================
        
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
            sector_rows = [format_row(r, i+1) for i, (_, r) in enumerate(df_sector.head(25).iterrows())] # Top 25 sectors
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

Layout: Top 25 ranking sectors sorted by trend strength (including Top Gainers).
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
