
"""
Earnings Performance Prompt Generator
"""
import os
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta
from tqdm import tqdm
import time
from modules.earnings import data as earnings_data
from common import data_fetcher



def run(date_str, output_dir):
    print(f"🚀 Generating Performance Prompt for {date_str}...")
    
    # 1. Fetch Basic Stock List (with Market Cap)
    # Using common.data_fetcher
    # Filter 1: Exclude ST, Min Market Cap 50亿 (0.5 Billion? No, 50亿 = 5 Billion)
    # data_fetcher.get_all_stock_list returns market_cap in 100M (亿)
    # So min_market_cap = 50
    
    print("Fetching Stock List (Filter: >50亿, No ST)...")
    stock_list = data_fetcher.get_all_stock_list(min_market_cap=50, exclude_st=True)
    
    # Filter 2: Exclude 688 (STAR Market) and 8xx/4xx (BJ)
    # 688, 689 are STAR. 8xx, 4xx are BJ. 300 is ChiNext (Keep?). User just said "Remove 688".
    # Usually small caps are 300/688. But user said "Remove 688".
    # I will remove codes starting with '688'.
    stock_list = stock_list[~stock_list['code'].str.startswith('688')]
    # Also remove '8' and '4' for BJ just in case?
    stock_list = stock_list[~stock_list['code'].str.startswith(('8', '4'))]
    
    valid_codes = set(stock_list['code'].tolist())
    print(f"Valid Candidates after filtering: {len(valid_codes)}")
    
    # 2. Fetch Earnings Forecast (All Available)
    # We want "All released forecasts" to rank them.
    # Not just "This Week".
    forecast_df = earnings_data.fetch_earnings_forecast() # Default: current period
    
    if forecast_df.empty:
        print("No forecast data found.")
        return False
        
    # Filter Forecasts to only include Valid Codes
    forecast_df['code'] = forecast_df['股票代码'].astype(str)
    forecast_df = forecast_df[forecast_df['code'].isin(valid_codes)].copy()
    
    print(f"Forecasts matching valid stocks: {len(forecast_df)}")
    
    # 3. Process Metrics
    # Need columns: 业绩变动幅度 (Range string), 预告类型
    
    # Helper to parse range
    def parse_avg_range(s):
        try:
            import re
            nums = re.findall(r"[-+]?\d+\.?\d*", str(s))
            if nums:
                return sum(map(float, nums)) / len(nums)
        except:
            pass
        return -9999.0

    forecast_df['change_pct_avg'] = forecast_df['业绩变动幅度'].apply(parse_avg_range)
    
    # 类别划分
    # Type A: 盈利增速 (预增/略增) - Positive Growth
    # Type B: 扭亏 (Turnaround)
    # Type C: 亏损增速 (Type=预亏/首亏/续亏, Looking for largest Drop/Loss?) 
    #   "亏损增速top5" -> Usually means "Loss increased the most" (Bad) OR "Loss narrowing"?
    #   If user wants "引流", "Loss Kings" (亏损王) is a topic.
    #   I will interpret as: Magnitude of Loss Increase (change_pct is usually negative).
    #   Wait, for Loss stocks, change_pct is often comparison to last year.
    #   If Profit -100M -> -200M, change is -100%?
    #   Let's just sort by `change_pct_avg` ascending for "Loss Growth"?
    #   Or strictly Type = Loss.
    
    # --- Category 1: 盈利增速 (Profit Growth) ---
    # Filter: Type in [预增, 略增, 续盈] AND change_pct > 0
    growth_mask = forecast_df['预告类型'].str.contains('增|盈') & (forecast_df['change_pct_avg'] > 0)
    growth_df = forecast_df[growth_mask].copy()
    
    # --- Category 2: 扭亏 (Turnaround) ---
    turnaround_mask = forecast_df['预告类型'].str.contains('扭亏')
    turnaround_df = forecast_df[turnaround_mask].copy()
    
    # --- Category 3: 盈利大幅激增 (Profit Surge - Interpretation of '扭盈'?) ---
    # User said "扭盈比例". If it's not Turnaround (covered above), maybe it means "Profit Explosion".
    # Let's use Top Growth again but maybe strictly "预增" (Pre-increase) vs "略增".
    # Actually, let's look for "Highest Growth" overall (which is Category 1).
    # Maybe User meant:
    # 1. 盈利增速 Top 5 (Growth Top)
    # 2. 扭亏比例 Top 5 (Turnaround Max Range?)
    # 3. 扭盈比例? -> Maybe "RoE"? Or "Profit Margin"? Unlikely available.
    # Let's stick to: "Turnaround Top 5" and "Growth Top 5".
    # And "Loss Growth" (Kuisun).
    
    # --- Category 4: 亏损扩大 (Loss Deepening) ---
    # Broadly "Loss" or "Decrease", but excluding "Turnaround" and "First Loss" if we want distinct cats.
    # User asked for "Loss Zone" (Existing) + "Profit to Loss" (New).
    # Existing "Loss Zone" was `亏|减`.
    # Let's refine:
    # "Profit to Loss" -> 首亏
    # "Loss Deepening" -> 续亏, 预减, 略减 (if change < 0), 预亏 (general)
    
    # 3. Profit to Loss (New)
    to_loss_mask = forecast_df['预告类型'].str.contains('首亏')
    to_loss_df = forecast_df[to_loss_mask].copy()
    
    # 4. Loss (Rest)
    # Exclude '首亏' from the general loss pool to avoid duplication if user wants distinct lists
    loss_mask = forecast_df['预告类型'].str.contains('亏|减') & (~forecast_df['预告类型'].str.contains('首亏')) & (~forecast_df['预告类型'].str.contains('扭亏'))
    loss_df = forecast_df[loss_mask].copy()
    
    # --- Helpers (Restored) ---
    def parse_profit_str(s):
        """
        Parse profit string (usually in Yuan) and format to 亿/万
        """
        if pd.isna(s) or s == '':
            return "N/A"
        try:
            s_str = str(s)
            import re
            nums = re.findall(r"[-+]?\d+\.?\d*", s_str)
            if not nums: return "N/A"
            # Values in akshare are in Yuan
            avg_val_yuan = sum(map(float, nums)) / len(nums)
            # Convert to Wan (10k)
            avg_val_wan = avg_val_yuan / 10000
            
            abs_val_wan = abs(avg_val_wan)
            if abs_val_wan >= 10000:
                val_yi = avg_val_wan / 10000
                return f"{val_yi:.2f}亿"
            else:
                return f"{avg_val_wan:.0f}万"
        except:
            return "N/A"

    def enrich_with_industry(df, stock_list_df):
        merged = pd.merge(df, stock_list_df[['code', 'industry', 'market_cap']], on='code', how='left')
        from common.data_fetcher import fetch_specific_industries
        if 'industry' not in merged.columns: merged['industry'] = ''
        merged['industry'] = merged['industry'].fillna('')
        if not merged.empty:
            merged = fetch_specific_industries(merged)
        return merged

    def select_top_candidates(df, metric_col, ascending=False, top_n=8):
        valid_df = df[df[metric_col] > -9000].copy()
        valid_df = valid_df.drop_duplicates(subset=['code'], keep='first')
        sorted_df = valid_df.sort_values(metric_col, ascending=ascending)
        return sorted_df.head(top_n)
    # Growth
    cand_growth = select_top_candidates(growth_df, 'change_pct_avg', ascending=False, top_n=5)
    cand_growth = enrich_with_industry(cand_growth, stock_list)
    
    # Turnaround
    cand_turnaround = select_top_candidates(turnaround_df, 'change_pct_avg', ascending=False, top_n=5)
    cand_turnaround = enrich_with_industry(cand_turnaround, stock_list)

    # Profit to Loss (New)
    cand_to_loss = select_top_candidates(to_loss_df, 'change_pct_avg', ascending=True, top_n=5)
    cand_to_loss = enrich_with_industry(cand_to_loss, stock_list)

    # Loss Deepening
    cand_loss = select_top_candidates(loss_df, 'change_pct_avg', ascending=True, top_n=5)
    cand_loss = enrich_with_industry(cand_loss, stock_list)
    
    # 6. Generate Prompts
    
    # Check if Fri/Sat/Sun for Weekly "Earnings Gold Digging"
    dt = datetime.strptime(date_str, '%Y%m%d')
    is_weekend = dt.weekday() >= 4
    
    if is_weekend:
        print("📅 Weekend detected: Generating Earnings Gold Digging for Weekly Report...")
        # Save to Weekly folder
        generate_prompt_file(cand_growth, cand_turnaround, cand_to_loss, cand_loss, date_str, output_dir, profit_fmt=parse_profit_str, is_weekly=True)
    else:
        print("📅 Weekday: Skipping Earnings Gold Digging (Weekly Report Only).")

    # Generate Merged Today/Tomorrow Prompt
    generate_merged_daily_prompt(date_str, output_dir, stock_list, forecast_df, profit_fmt=parse_profit_str)
    
    return True

def generate_merged_daily_prompt(date_str, output_dir, valid_stock_df, all_forecast_df, profit_fmt=None):
    """
    Generate merged prompt for Today's and Tomorrow's Earnings Disclosure.
    """
    try:
        today_date = datetime.strptime(date_str, '%Y%m%d')
        tomorrow_date = today_date + timedelta(days=1)
        
        target_today_hyphen = today_date.strftime('%Y-%m-%d')
        target_tomorrow_hyphen = tomorrow_date.strftime('%Y-%m-%d')
        
        display_date = f"{date_str[4:6]}月{date_str[6:8]}日"
        
        print(f"🚀 Generating Merged Earnings Prompt for {target_today_hyphen} & {target_tomorrow_hyphen}...")
        
        # --- Helper to get dataframe for a specific date ---
        def get_disclosure_df(target_date_str):
            df = pd.DataFrame()
            if not all_forecast_df.empty and '公告日期' in all_forecast_df.columns:
                all_forecast_df['公告日期'] = all_forecast_df['公告日期'].astype(str)
                mask = all_forecast_df['公告日期'].str.contains(target_date_str)
                df = all_forecast_df[mask].copy()
                
            if not df.empty:
                df = df.drop_duplicates(subset=['code'], keep='first')
                df = pd.merge(df, valid_stock_df[['code', 'industry', 'market_cap']], left_on='code', right_on='code', how='left')
                df = df.dropna(subset=['market_cap']) 
                
                # Enrich Industry if missing
                from common.data_fetcher import fetch_specific_industries
                if 'industry' not in df.columns: df['industry'] = ''
                df['industry'] = df['industry'].fillna('')
                df = fetch_specific_industries(df) 
                
                # Parse pct locally if needed
                if 'change_pct_avg' not in df.columns:
                     def parse_avg(s):
                        try:
                            import re
                            nums = re.findall(r"[-+]?\d+\.?\d*", str(s))
                            if nums: return sum(map(float, nums)) / len(nums)
                        except: pass
                        return -9999.0
                     df['change_pct_avg'] = df['业绩变动幅度'].apply(parse_avg)

                df.sort_values('market_cap', ascending=False, inplace=True)
            return df

        today_df = get_disclosure_df(target_today_hyphen)
        
        print(f"Disclosures: Today={len(today_df)}")
        
        if today_df.empty:
             print("No disclosures found for today.")
             lines = [f"# {date_str} 今日业绩 - 无重要披露"]
             path = os.path.join(output_dir, "AI提示词", "今日业绩_Prompt.txt")
             with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
             return

        # Generate Prompt
        lines = []
        lines.append(f"# {date_str} 今日业绩披露 - AI绘图Prompt")
        lines.append("")
        lines.append("## 图片规格")
        lines.append("- 比例: 9:16 竖版")
        lines.append("- 风格: 手绘/手账风格 (Warm Scale)")
        lines.append("- 背景色: #F5E6C8 纸黄色")
        lines.append("- 字体: 手写体 (Handwritten Chinese)")
        lines.append("")
        lines.append("## 标题")
        lines.append(f'**{display_date} 业绩披露速递** (Big Bold Red/Black Brush)')
        lines.append("")

        # Function to format a list section (kept for reuse)
        def format_section(title, df):
            sec_lines = []
            sec_lines.append(f"### {title}")
            sec_lines.append("```")
            sec_lines.append(f"Header: [股票名称] [同比涨幅] (市值 | 净利润)")
            sec_lines.append("-" * 30)
            
            count = 0
            # Ensure we show as many as possible (Top 80 to avoid context limit, but usually <50/day)
            for _, row in df.head(80).iterrows(): 
                count += 1
                name = row['股票简称']
                pct = row['change_pct_avg']
                
                pct_str = f"+{pct:.0f}%" if pct > -9000 else "N/A"
                if pct > 0: pct_str = f"+{pct:.0f}%"
                elif pct > -9000 and pct < 0: pct_str = f"{pct:.0f}%"
                
                # Net Profit
                raw_val = row.get('预测数值', 0)
                profit_str = profit_fmt(raw_val) if profit_fmt else str(raw_val)
                
                if profit_str == "N/A": continue
                
                # Market Cap
                mcap = row.get('market_cap', 0)
                try:
                    mcap_val = float(mcap)
                    mcap_str = f"{mcap_val:.0f}亿"
                except: mcap_str = "-"

                # Compact Single Line
                # 锋龙股份 +50% (20亿 | 1.5亿)
                sec_lines.append(f"{name:<6} {pct_str:<6} (市值:{mcap_str} | 净利:{profit_str})")
            
            if count == 0:
                sec_lines.append("(无重点披露)")
                
            sec_lines.append("```")
            sec_lines.append("")
            return sec_lines

        # Section 1: Today Only
        lines.extend(format_section(f"📅 今日披露 ({len(today_df)}家)", today_df))
        
        lines.append("## 底部标语")
        lines.append("**总结不易，每天收盘后推送，点赞关注不迷路！**")
        lines.append("（居中显示，小字，温馨提示风格）")
        
        prompt_dir = os.path.join(output_dir, "AI提示词")
        os.makedirs(prompt_dir, exist_ok=True)
        # Revert filename to Today only
        output_path = os.path.join(prompt_dir, "今日业绩_Prompt.txt")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        print(f"Daily Prompt Generated: {output_path}")

    except Exception as e:
        print(f"Error generating daily prompt: {e}")

def generate_prompt_file(growth, turnaround, to_loss, loss, date_str, output_dir, profit_fmt=None, is_weekly=False):
    display_date = f"{date_str[4:6]}月{date_str[6:8]}日"
    
    lines = []
    lines.append(f"# {date_str} A股业绩掘金 - AI绘图Prompt (手绘风格版)")
    lines.append("")
    lines.append("## 图片规格")
    lines.append("- 比例: 9:16 竖版")
    lines.append("- 风格: 手绘/手账风格，暖色纸张质感 (Warm Scale)")
    lines.append("- 背景色: #F5E6C8 纸黄色")
    lines.append("- 字体: 手写体 (Handwritten Chinese)")
    lines.append("")
    lines.append("## 标题")
    lines.append(f'**{display_date} A股业绩风云榜** (Big Bold Red/Black Brush)')
    lines.append('副标题: "谁是预增王？谁是避雷区？"')
    lines.append("")
    
    lines.append("## 核心榜单 (Four Sections)")
    lines.append("> **版式要求**: 类似便利贴或手绘框的四个区域。")
    lines.append("")
    
    def format_section(title, df, theme_color, icon_mark):
        section_lines = []
        section_lines.append(f"### {title}")
        section_lines.append(f"**Theme Color**: {theme_color} (Border/Header)")
        section_lines.append("```")
        section_lines.append(f"Header: [股票名称] [涨幅] (行业 | 市值 | 净利润 | 上年同期)")
        section_lines.append("-" * 30)
        for _, row in df.iterrows():
            name = row['股票简称']
            pct = row['change_pct_avg']
            # Pct Color: Red for positive/Up, Green for negative/Down
            pct_str = f"+{pct:.0f}%" if pct > 0 else f"{pct:.0f}%"
            pct_mark = "[红]" if pct > 0 else "[绿]"
            
            # Net Profit
            raw_val = row.get('预测数值', 0)
            profit_str = profit_fmt(raw_val) if profit_fmt else str(raw_val)
            
            # Last Year
            raw_last = row.get('上年同期值', 0)
            last_str = profit_fmt(raw_last) if profit_fmt else str(raw_last)
            
            # Skip N/A as requested
            if profit_str == "N/A":
                continue
            
            industry = row.get('industry', '其他')
            if not industry: industry = '其他'
            
            # Market Cap
            mcap = row.get('market_cap', 0)
            try:
                mcap_val = float(mcap)
                mcap_str = f"{mcap_val:.0f}亿"
            except:
                mcap_str = "N/A"
            
            # Format:
            section_lines.append(f"{name} {pct_str}")
            section_lines.append(f"  └─ {industry} | {mcap_str} | {profit_str} | {last_str}")
            section_lines.append("")
        section_lines.append("```")
        section_lines.append("")
        return section_lines

    # 1. Growth
    lines.extend(format_section("🚀 盈利增速TOP5 (预增王)", growth, "Red/Orange", "🔥"))
    
    # 2. Turnaround
    lines.extend(format_section("🔄 扭亏为盈TOP5 (翻身仗)", turnaround, "Golden/Yellow", "💰"))
    
    # 3. Profit to Loss (New)
    lines.extend(format_section("📉 盈转亏TOP5 (业绩变脸)", to_loss, "Blue/Cold", "🌧️"))
    
    # 4. Loss Deepening
    lines.extend(format_section("💣 亏损扩大TOP5 (避雷区)", loss, "Green/Grey", "☠️"))
    
    lines.append("## 底部标语")
    lines.append("**总结不易，每天收盘后推送，点赞关注不迷路！**")
    lines.append("（居中显示，小字，温馨提示风格）")
    lines.append("")
    
    lines.append("---")
    lines.append("## AI Prompt (English)")
    lines.append("Hand-drawn infographic poster, vertical 9:16, warm beige paper texture (#F5E6C8).")
    lines.append("Four hand-sketched boxes (Sticky note style) containing lists.")
    lines.append("1. **Profit Growth** (Red outline): List of stocks with high +% numbers.")
    lines.append("2. **Turnaround** (Gold outline): List of stocks turning profitable.")
    lines.append("3. **Profit to Loss** (Blue outline): List of stocks turning to loss.")
    lines.append("4. **Loss Zone** (Green/Grey outline): List of stocks with negative -% numbers.")
    lines.append("**Typography**: Rough marker pen style, bold headers.")
    lines.append("**Visuals**: Cute doodle icons (Rocket, Gold bag, Cloud/Rain, Bomb).")
    
    # Path selection (Weekly vs Daily)
    if is_weekly:
        save_dir = os.path.join(output_dir, "AI提示词", "周刊")
    else:
        save_dir = os.path.join(output_dir, "AI提示词")
        
    os.makedirs(save_dir, exist_ok=True)
    output_path = os.path.join(save_dir, "业绩掘金_Prompt.txt")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    print(f"Prompt Generated: {output_path}")



if __name__ == "__main__":
    # Test
    run("20260126", "results/20260126")

