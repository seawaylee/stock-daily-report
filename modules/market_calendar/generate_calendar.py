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

def generate_tomorrow_prompt(date_str, output_dir):
    """Generate Tomorrow's Calendar Prompt"""
    print(f"Generating Tomorrow's Calendar for {date_str}...")
    
    # Calculate Tomorrow's date
    today = datetime.strptime(date_str, '%Y%m%d')
    tomorrow = today + timedelta(days=1)
    tomorrow_str = tomorrow.strftime('%Y%m%d')
    tomorrow_disp = tomorrow.strftime('%m月%d日 %A')
    
    # Fetch Data
    ipo_df = fetch_ipo_data()
    susp_df = fetch_suspension_data(tomorrow_str)
    
    # Process IPO
    ipo_text = "无"
    listing_text = "无"
    
    if not ipo_df.empty:
        # Check for IPO Subscription tomorrow
        sub_tomorrow = ipo_df[ipo_df['申购日期'] == tomorrow.strftime('%Y-%m-%d')]
        if not sub_tomorrow.empty:
            ipo_text = ""
            for _, row in sub_tomorrow.iterrows():
                ipo_text += f"**{row['股票简称']}** ({row['股票代码']})\n"
                
        # Check for Listing tomorrow (Note: '上市日期' might be NaN or future)
        # Using a loose check if column exists
        if '上市日期' in ipo_df.columns:
            list_tomorrow = ipo_df[ipo_df['上市日期'] == tomorrow.strftime('%Y-%m-%d')]
            if not list_tomorrow.empty:
                listing_text = ""
                for _, row in list_tomorrow.iterrows():
                    listing_text += f"**{row['股票简称']}** ({row['股票代码']}) - 发行价 {row['发行价格']}元\n"

    # Process Suspension
    susp_text = "无"
    resump_text = "无"
    if not susp_df.empty:
        # Filter Logic could be complex, simplifying for prompt generation
        # Just listing top 5 suspensions
        susp_text = ""
        for _, row in susp_df.head(5).iterrows():
            susp_text += f"- **{row['名称']}** ({row['代码']}) - {row['停牌原因']}\n"
            
        # Check resumption (if column exists or inferred)
        if '预计复牌时间' in susp_df.columns:
            resump = susp_df[susp_df['预计复牌时间'].astype(str).str.contains(tomorrow.strftime('%Y-%m-%d'), na=False)]
            if not resump.empty:
                resump_text = ""
                for _, row in resump.iterrows():
                    resump_text += f"**{row['名称']}** ({row['代码']})\n"

    # Create Prompt Content
    content = f"""# 明日A股日历 - AI绘图Prompt ({tomorrow_disp})

## 图片规格
- 比例: 9:16 竖版
- 风格: 手绘/手账风格，暖色纸张质感
- 背景色: #F5E6C8 纸黄色

## 标题
**📅 明日A股日历** （红色）
**{tomorrow.strftime('%m月%d日')}**（黑色小字）

---

## 日程内容

### 📢 重点关注

#### 💰 新股申购
{ipo_text}

#### 🎁 新股上市
{listing_text}

---

### ⏰ 停复牌信息

#### 🔴 停牌关注
{susp_text}

#### 🟢 复牌关注
{resump_text}

---

## AI绘图Prompt (English)

Hand-drawn calendar style infographic poster, Chinese A-share market tomorrow preview, {tomorrow_disp}.

**Style**: Warm cream paper texture (#F5E6C8), vintage notebook aesthetic, handwritten Chinese fonts.

**Layout**:
- Title: "📅 明日A股日历" (Red)
- Sections for IPO (Goal Icon 💰), Suspension (Red Dot 🔴), Resumption (Green Dot 🟢).
- Hand-drawn icons and borders.

(Optimized for hand-drawn calendar style)
"""
    
    # Save
    path = os.path.join(output_dir, "AI提示词", "明日A股日历_Prompt.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Saved: {path}")

def generate_next_week_prompt(date_str, output_dir):
    """Generate Next Week's Calendar Prompt (Only on Fridays)"""
    today = datetime.strptime(date_str, '%Y%m%d')
    if today.weekday() != 4: # Only run on Friday
        print("Not Friday, skipping Next Week Calendar.")
        return

    print(f"Generating Next Week's Calendar (Date: {date_str})...")
    
    # Logic similar to Tomorrow's prompt but aggregation for next week
    dates = get_next_week_dates(date_str)
    start_date = dates[0]
    end_date = dates[-1]
    
    content = f"""# 下周A股日历 - AI绘图Prompt ({start_date}-{end_date})

## 图片规格
- 比例: 9:16 竖版
- 风格: 手绘/手账风格，暖色纸张质感
- 背景色: #F5E6C8 纸黄色

## 标题
**📅 下周A股大事件前瞻** （红色）
**{start_date[4:]}-{end_date[4:]}**

---

## 周日历内容 (自动生成占位符，请人工补充大事件)

### 周一 {dates[0][4:6]}/{dates[0][6:]}
- 关注: 新股申购/停复牌

### 周二 {dates[1][4:6]}/{dates[1][6:]}
- 关注: 市场走势

### 周三 {dates[2][4:6]}/{dates[2][6:]}
- 关注: 行业动态

### 周四 {dates[3][4:6]}/{dates[3][6:]}
- 关注: 资金流向

### 周五 {dates[4][4:6]}/{dates[4][6:]}
- 关注: 周末效应

---

## AI绘图Prompt (English)

Hand-drawn weekly calendar style infographic, A-share next week preview.

**Style**: Warm cream paper texture (#F5E6C8), vintage notebook aesthetic.

**Layout**:
- 5 Day Columns (Mon-Fri)
- Hand-drawn icons for key events.

(Optimized for weekly planner style)
"""
    path = os.path.join(output_dir, "AI提示词", "下周A股日历_Prompt.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Saved: {path}")

def run(date_str, output_dir):
    generate_tomorrow_prompt(date_str, output_dir)
    generate_next_week_prompt(date_str, output_dir)
