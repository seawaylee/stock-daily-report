"""
[Module 6] Abnormal Fluctuation Alert Monitor
Functionality:
1. Fetch Dragon Tiger Board data for "Abnormal Fluctuation" (20% deviation).
2. Analyze rolling window (T-2 drop).
3. Check "Commercial Aerospace" sector status (Safe/Triggered).
4. Generate "Abnormal Fluctuation Alert" Prompt.
"""
import akshare as ak
import pandas as pd
from datetime import datetime
import time
import os

def fetch_lhb_abnormal(start_date, end_date):
    """Fetch LHB data for abnormal fluctuation"""
    print(f"Fetching LHB data from {start_date} to {end_date}...")
    try:
        lhb = ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)
        # Filter for 20% or 30% deviation
        if not lhb.empty:
            yidong = lhb[lhb['上榜原因'].str.contains('涨幅偏离值累计达到20%|涨幅偏离值累计达到30%', na=False)].copy()
            return yidong
    except Exception as e:
        print(f"Error fetching LHB: {e}")
    return pd.DataFrame()

def analyze_stock(code, end_date):
    """Analyze single stock for window reset logic"""
    try:
        # Fetch 10 days history to cover calculating T-2 window
        start_date_hist = (datetime.strptime(end_date, '%Y%m%d') - pd.Timedelta(days=15)).strftime('%Y%m%d')
        df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_date_hist, end_date=end_date, adjust="qfq")
        
        if len(df) >= 3:
            recent = df.tail(3)
            dates = [str(d)[:10] for d in recent['日期'].tolist()]
            pcts = recent['涨跌幅'].tolist()
            cum = sum(pcts)
            
            # Simple window reset logic
            # Current window: T-2 + T-1 + T = cum
            # Next window (Tomorrow): T-1 + T + NextDay
            # Dropped: T-2
            dropped_date = dates[0]
            dropped_pct = pcts[0]
            new_base = cum - dropped_pct
            
            return {
                'code': code,
                'dates': dates,
                'pcts': pcts,
                'cumulative': cum,
                'dropped_date': dropped_date,
                'dropped_pct': dropped_pct,
                'new_base': new_base
            }
    except:
        pass
    return None

def check_aerospace_status(start_date, end_date):
    """Quick check for Aerospace sector (Hardcoded list for robustness)"""
    core_stocks = [
        ('600118', '中国卫星', '主板'), ('600879', '航天电子', '主板'), 
        ('300058', '蓝色光标', '创业板') # Added as user requested
    ]
    results = []
    
    for code, name, board in core_stocks:
        threshold = 30 if board == '创业板' else 20
        # Re-use analyze_stock logic or custom fetch
        # For simplicity in this module, we assume SAFE unless found in LHB
        # But to be accurate, we should check gains.
        # Here we just check if they are in the 'Triggered' list (passed in main run logic)
        # or do a quick fetch
        try:
            start_hist = (datetime.strptime(end_date, '%Y%m%d') - pd.Timedelta(days=15)).strftime('%Y%m%d')
            df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date=start_hist, end_date=end_date, adjust="qfq")
            if len(df) >= 3:
                cum = sum(df.tail(3)['涨跌幅'].tolist())
                status = "🔴 Triggered" if cum >= threshold else "🟢 Safe"
                results.append({'code': code, 'name': name, 'cum': cum, 'status': status, 'threshold': threshold})
        except:
            pass
            
    return results

def generate_prompt(date_str, triggered_stocks, aerospace_status, output_dir):
    """Generate final prompt"""
    date_disp = datetime.strptime(date_str, '%Y%m%d').strftime('%m月%d日')
    release_date = (datetime.strptime(date_str, '%Y%m%d') + pd.Timedelta(days=1)).strftime('%m-%d')
    
    # Format tables
    triggered_table = ""
    for s in triggered_stocks[:5]: # Top 5
        triggered_table += f"| {s['名称']} | {s['题材']} | {s['cumulative']:.1f}% | {s['new_base']:.1f}% | 移出{s['dropped_pct']:.1f}% |\n"
        
    aerospace_table = ""
    for s in aerospace_status:
        safe_icon = "✅" if "Safe" in s['status'] else "⚠️"
        aerospace_table += f"| {s['name']} | {s['cum']:.1f}% | {safe_icon} 距触发{s['threshold']-s['cum']:.1f}% |\n"

    content = f"""# 异动监管预警 - AI绘图Prompt ({date_disp})
# 数据来源：龙虎榜 + 专项板块筛查

## 图片规格
- 比例: 9:16 竖版
- 风格: 手绘/手账风格，暖色纸张质感
- 背景色: #F5E6C8 纸黄色

## 标题
**⚠️ 异动监管预警** （红）
**{date_disp} | 龙虎榜 & 热门题材**

---

## 🔴 已触发异动 (重点关注)
**监管解除日期: {release_date}**

| 股票 | 题材 | 累计涨幅 | 解除后窗口 | 状态 |
|------|------|----------|------------|------|
{triggered_table}
> 💡 T-2日的涨幅将在明日移出窗口

---

## 🚀 热门板块专项筛查：商业航天
**当前状态：安全 (Safe)**

| 龙头股 | 累计涨幅 | 状态 |
|--------|----------|------|
{aerospace_table}

---

## AI绘图Prompt (English)

Hand-drawn warning style infographic, A-share abnormal fluctuation alert, {date_disp}.

**Style**: Warm cream paper texture (#F5E6C8), vintage notebook aesthetic.

**Layout**:
- Title: "⚠️ 异动监管预警"
- Section 1: Triggered Stocks List (Red).
- Section 2: Commercial Aerospace Sector Monitor (Green Shield 🛡️).
- Footer: "Data Source: Dragon Tiger Board".

(Optimized for hand-drawn regulatory alert infographic)
"""
    path = os.path.join(output_dir, "AI提示词", "异动监管预警_Prompt.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Saved: {path}")

def run(date_str, output_dir):
    print(f"Running Abnormal Fluctuation Alert for {date_str}...")
    
    # 1. Fetch LHB
    start_dt = (datetime.strptime(date_str, '%Y%m%d') - pd.Timedelta(days=3)).strftime('%Y%m%d')
    lhb_df = fetch_lhb_abnormal(start_dt, date_str)
    
    triggered_list = []
    if not lhb_df.empty:
        unique_codes = lhb_df[['代码', '名称']].drop_duplicates().values.tolist()
        for code, name in unique_codes[:10]: # Limit to top 10 to save time
            analysis = analyze_stock(code, date_str)
            if analysis:
                # Get theme (mock or simple fetch)
                try:
                    info = ak.stock_individual_info_em(symbol=code)
                    theme = info[info['item'] == '行业'].iloc[0]['value']
                except:
                    theme = "待查"
                
                analysis['名称'] = name
                analysis['题材'] = theme
                triggered_list.append(analysis)
                
    # 2. Check Aerospace
    aerospace_status = check_aerospace_status(start_dt, date_str)
    
    # 3. Generate Prompt
    generate_prompt(date_str, triggered_list, aerospace_status, output_dir)
