"""
[Module 5] Market Calendar Generator
Generates:
1. Tomorrow's A-Share Calendar Prompt
2. Next Week's A-Share Calendar Prompt (if applicable, e.g., on Friday)
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import os
import sys

# Import Core News Module for Data Source
sys.path.append(os.getcwd())
try:
    from modules.core_news.core_news_monitor import fetch_eastmoney_data, filter_top_news
except ImportError:
    # Fallback if running standalone
    pass

def check_is_weekend(date_str):
    """Check if a date is Friday (4), Saturday (5), or Sunday (6)"""
    dt = datetime.strptime(date_str, '%Y%m%d')
    return dt.weekday() >= 4

def get_next_week_dates(date_str):
    """Get date strings for next Monday to Friday"""
    dt = datetime.strptime(date_str, '%Y%m%d')
    # Find next Monday
    days_ahead = 0 - dt.weekday() + 7 
    if dt.weekday() >= 5: # Sat or Sun
        days_ahead = 0 - dt.weekday() + 7 # Still next Mon
        
    next_mon = dt + timedelta(days=days_ahead)
    dates = [(next_mon + timedelta(days=i)).strftime('%Y%m%d') for i in range(5)]
    return dates

def fetch_ipo_data():
    """Fetch IPO calendar"""
    try:
        ipo = ak.stock_xgsglb_em(symbol="全部股票")
        return ipo
    except:
        return pd.DataFrame()

def fetch_suspension_data(date_str):
    """Fetch suspension data"""
    try:
        # AKShare date format might be YYYYMMDD or YYYY-MM-DD depending on version, 
        # stock_tfp_em usually takes YYYYMMDD
        suspend = ak.stock_tfp_em(date=date_str)
        return suspend
    except:
        return pd.DataFrame()

def get_event_content():
    """
    Fetch news and extract "Future/Tomorrow" related events, 
    or fallback to Top News as "Focus".
    """
    try:
        # Fetch last 24h news
        data = fetch_eastmoney_data(target_window_hours=24)
        top_news, bull_secs, bear_secs = filter_top_news(data, limit=20)
        
        # Filter for future events keywords
        future_keywords = ['明天', '明日', '即将', '召开', '发布', '举行', '开幕']
        
        macro_events = []
        sector_events = []
        
        for news_str in top_news:
             # news_str format: "[HH:MM]【Direction·Target】 Title"
             # We want to extract Title + Target
             
             # Simple heuristic classification based on tags
             if "宏观" in news_str or "央行" in news_str or "数据" in news_str:
                 macro_events.append(news_str)
             elif "【" in news_str and "】" in news_str:
                 # Check if it has specific sector tag like 【利多·半导体】
                 if "行业" not in news_str and "个股" not in news_str:
                     sector_events.append(news_str)
        
        # 1. Macro Content
        macro_text = ""
        if macro_events:
            for e in macro_events[:3]: # Top 3
                macro_text += f"- {e}\n"
        else:
            # Fallback to general top news if no macro specific found
            for e in top_news[:3]:
                 macro_text += f"- {e}\n"
                 
        # 2. Sector Content
        sector_text = ""
        if sector_events:
            dedupe_sectors = set()
            count = 0
            for e in sector_events:
                # Extract sector name from tag
                try:
                    sec_name = e.split('·')[1].split('】')[0]
                    if sec_name not in dedupe_sectors:
                        sector_text += f"- **{sec_name}**: {e.split('】')[1]}\n"
                        dedupe_sectors.add(sec_name)
                        count += 1
                        if count >= 3: break
                except:
                    continue
        else:
             sector_text = "关注资金流向靠前的热门板块 (请参考涨停天梯)"
             
        return macro_text, sector_text
        
    except Exception as e:
        print(f"Failed to fetch event content: {e}")
        return "暂无重点宏观消息", "暂无重点板块消息"

def generate_merged_tomorrow_prompt(date_str, output_dir):
    """
    Generate Merged Tomorrow's Calendar Prompt
    Includes:
    1. IPO/Listing (Data-driven)
    2. Suspensions (Data-driven)
    3. Macro/Sector Events (From News Source)
    """
    print(f"Generating Merged Tomorrow's Calendar for {date_str}...")
    
    # Calculate Tomorrow's date
    today = datetime.strptime(date_str, '%Y%m%d')
    tomorrow = today + timedelta(days=1)
    tomorrow_str = tomorrow.strftime('%Y%m%d')
    tomorrow_disp = tomorrow.strftime('%m月%d日 %A')
    
    # --- Part 1: Fetch Data (IPO/Suspensions) ---
    ipo_df = fetch_ipo_data()
    susp_df = fetch_suspension_data(tomorrow_str)
    
    # --- Part 2: Fetch News Events ---
    macro_text, sector_text = get_event_content()
    
    ipo_text = "无"
    listing_text = "无"
    
    if not ipo_df.empty:
        # IPO Subscription
        sub_tomorrow = ipo_df[ipo_df['申购日期'] == tomorrow.strftime('%Y-%m-%d')]
        if not sub_tomorrow.empty:
            ipo_text = ""
            for _, row in sub_tomorrow.iterrows():
                ipo_text += f"**{row['股票简称']}** ({row['股票代码']})\n"
                
        # IPO Listing
        if '上市日期' in ipo_df.columns:
            list_tomorrow = ipo_df[ipo_df['上市日期'] == tomorrow.strftime('%Y-%m-%d')]
            if not list_tomorrow.empty:
                listing_text = ""
                for _, row in list_tomorrow.iterrows():
                    listing_text += f"**{row['股票简称']}** ({row['股票代码']}) - 发行价 {row['发行价格']}元\n"

    susp_text = "无"
    resump_text = "无"
    if not susp_df.empty:
        susp_text = ""
        for _, row in susp_df.head(5).iterrows():
            susp_text += f"- **{row['名称']}** ({row['代码']}) - {row['停牌原因']}\n"
            
        if '预计复牌时间' in susp_df.columns:
            resump = susp_df[susp_df['预计复牌时间'].astype(str).str.contains(tomorrow.strftime('%Y-%m-%d'), na=False)]
            if not resump.empty:
                resump_text = ""
                for _, row in resump.iterrows():
                    resump_text += f"**{row['名称']}** ({row['代码']})\n"

    # --- Part 3: Generate Merged Content ---
    content = f"""(masterpiece, best quality), (vertical:1.2), (aspect ratio: 10:16), (sketch style), (hand drawn), (infographic)

A TALL VERTICAL PORTRAIT IMAGE (Aspect Ratio 10:16) HAND-DRAWN SKETCH style tomorrow events preview infographic poster.

**LAYOUT & COMPOSITION:**
- **Canvas**: 1600x2560 vertical.
- **Background**: Hand-drawn warm paper texture (#F5E6C8).
- **Header**: 
  - Title: "明日A股日历" (Tomorrow's A-Share Calendar)
  - Date: "{tomorrow_disp}"
  - Icon: A hand-sketched calendar or sunrise icon.

**MAIN CONTENT - EVENT SECTIONS:**

### 1. 📢 宏观/消息面 (Macro & News)
{macro_text}

### 2. 📊 行业/板块焦点 (Sector Focus)
{sector_text}

### 3. 💰 新股/交易 (IPO & Market)
   - **IPO Subscription (申购)**: 
{ipo_text}
   - **IPO Listing (上市)**: 
{listing_text}
   - **Suspension (停牌)**: 
{susp_text}
   - **Resumption (复牌)**: 
{resump_text}

### 4. 📢 个股/业绩 (Stock Events)
   - 关注晚间公告与业绩披露 (详见业绩模块)

**FOOTER SECTION:**
- **Strategy**: "策略建议: 关注宏观政策落地与热门板块轮动"
- **CTA**: "每日盘前更新，点赞关注不迷路"

**ART STYLE DETAILS:**
- **Lines**: Charcoal and graphite pencil strokes.
- **Color Palette**: Vintage hues - faded blue, deep gold, warm yellow.
- **Icons**: Hand-drawn icons for each section.

(Optimized for high-quality vector-style sketch render)
"""
    
    path = os.path.join(output_dir, "AI提示词", "明日A股日历_Prompt.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Saved Merged Prompt: {path}")


def run(date_str, output_dir, run_weekly=False):
    # 1. Merged Calendar (Events + IPO/Suspension)
    generate_merged_tomorrow_prompt(date_str, output_dir)
    
    # 2. Next Week (if Friday)
    # generate_next_week_prompt(date_str, output_dir, force_run=run_weekly)
    pass


