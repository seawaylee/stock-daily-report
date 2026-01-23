"""
[Module 7] Jin10 Economic Monitor - Real Data Version
Generates:
1. Jin10 Economic Brief Prompt (Major Events & Economic Calendar)
Using: EastMoney Big Events & Cailianpress Global News as reliable proxies
"""
import akshare as ak
import pandas as pd
from datetime import datetime
import os
import re

def fetch_major_events(target_date):
    """Fetch Major Economic News (EastMoney) and filter by date"""
    print(f"Fetching Major Events (EastMoney) for {target_date}...")
    try:
        df = ak.stock_news_em(symbol="大事提醒")
        if not df.empty and '发布时间' in df.columns:
            # Filter by date (target_date format YYYYMMDD -> YYYY-MM-DD)
            target_fmt = datetime.strptime(target_date, '%Y%m%d').strftime('%Y-%m-%d')
            # Check if 发布时间 contains date string
            filtered = df[df['发布时间'].astype(str).str.contains(target_fmt)]
            if not filtered.empty:
                return filtered.head(10)
            else:
                # If exact date matched nothing (maybe API delay or only today's data), 
                # fallback to just returning head if date is very recent, or return none
                # For historical query (like '22nd'), we rely on what API returns.
                # stock_news_em typically returns recent 100 items. 
                # If date is not found, print warning.
                print(f"No events found for {target_fmt} in recent list.")
                return pd.DataFrame()
        return df
    except:
        return pd.DataFrame()

def fetch_global_news(target_date):
    """Fetch Global Macro News (Cailianpress) and filter by date"""
    print(f"Fetching Global News (Cailianpress) for {target_date}...")
    try:
        df = ak.stock_info_global_cls(symbol="美国") 
        if not df.empty and '发布日期' in df.columns:
             target_fmt = datetime.strptime(target_date, '%Y%m%d').strftime('%Y-%m-%d')
             filtered = df[df['发布日期'].astype(str) == target_fmt]
             return filtered.head(15)
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def generate_prompt(date_str, output_dir):
    """Generate Jin10 Prompt with Real Data"""
    date_disp = datetime.strptime(date_str, '%Y%m%d').strftime('%m月%d日')
    
    # 1. Fetch Real Data
    events_df = fetch_major_events(date_str)
    news_df = fetch_global_news(date_str)
    
    # 2. Process Content
    # Macro Events (EastMoney)
    macro_content = ""
    if not events_df.empty:
        count = 0
        for _, row in events_df.iterrows():
            title = row['新闻标题']
            title = re.sub(r'【.*?】', '', title).strip()
            if len(title) > 5 and count < 6:
                macro_content += f"- {title}\n"
                count += 1
    else:
        macro_content = "- [当日无重大财经事件提醒或数据未抓取到]"

    # Global News (Cailianpress)
    global_content = ""
    if not news_df.empty:
        count = 0
        for _, row in news_df.iterrows():
            title = row['标题']
            # Clean title: remove "财联社XX月XX日电"
            title = re.sub(r'^财联社\d+月\d+日电，?', '', title)
            if len(title) > 10 and count < 8:
                global_content += f"- {title}\n"
                count += 1
    else:
        global_content = "- [当日无重磅宏观消息抓取]"
    
    content = f"""# 金十数据财经日历 - AI绘图Prompt ({date_disp})
# 数据来源: 东方财富 / 财联社 (已按日期筛选)

## 图片规格
- 比例: 9:16 竖版
- 风格: 手绘/手账风格，暖色纸张质感
- 背景色: #F5E6C8 纸黄色

## 标题
**📅 全球财经大事件** (红色)
**Jin10 Data | {date_disp}**

---

## 🌍 全球宏观 (Macro)

### 🇺🇸 全球/美国动态
{global_content}

### 🇨🇳 国内大事
{macro_content}

---

## 📊 市场异动 (Market Movers)

| 资产 | 关注点 |
|------|--------|
| 黄金 | 关注地缘局势 |
| 原油 | 关注库存数据 |
| 美股 | 关注科技股财报 |

---

## 💡 交易提醒
- 密切关注上述宏观事件发布
- ⚠️ 市场波动可能加剧，注意风控

## AI绘图Prompt (English)

Hand-drawn financial infographic poster, Jin10 Data content, global economic calendar {date_disp}.

**Style**: Warm cream paper texture (#F5E6C8), vintage notebook aesthetic, handwritten Chinese fonts.

**Layout**:
- Title: "Jin10 Data" in hand-drawn style.
- Section 1: Global News List (Hand-drawn flag icons).
- Section 2: Market Movers Table (Hand-drawn borders).
- Footer: "Jin10".

(Optimized for hand-drawn financial briefing)
"""
    path = os.path.join(output_dir, "AI提示词", "金十数据_Prompt.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Saved: {path}")

def run(date_str, output_dir):
    generate_prompt(date_str, output_dir)
