"""
[Module 7] Economic Monitor (Source: Cailianpress 24h)
Generates:
1. Economic Brief Prompt (Major Events & Market Movers)
Source: Cailianpress (CLS) 24h Rolling Telegraphs
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import re
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def fetch_cls_telegraphs(limit=100):
    """Fetch latest telegraphs from Cailianpress"""
    url = "https://www.cls.cn/nodeapi/telegraphList"
    params = {
        'rn': limit,
        'sv': '7.7.5',
    }
    print(f"Fetching CLS Telegraphs (Top {limit})...")
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            data = r.json().get('data', {}).get('roll_data', [])
            return data
    except Exception as e:
        print(f"Error fetching CLS: {e}")
    return []

def filter_last_24h_highlights(data):
    """Filter news from last 24h and select highlights"""
    now = datetime.now()
    cutoff = now - timedelta(hours=24) # 24h window
    
    highlights = {
        'global': [], # US/EU/Global Macro
        'china': [],  # China/Policy
        'market': []  # Assets/Stocks
    }
    
    # Keywords for simple categorization
    kw_global = ['美联储', '美元', '欧央行', '降息', 'CPI', 'GDP', '拜登', '特朗普', '美国', '欧盟']
    kw_market = ['黄金', '原油', '比特币', '纳指', '标普', '股价', '财报', '业绩', '涨停', '大跌', '新高']
    kw_china = ['央行', '证监会', 'A股', '国务院', '发改委', '统计局', 'LPR', '社融', 'M2']

    unique_titles = set()

    for item in data:
        timestamp = item.get('ctime', 0)
        item_time = datetime.fromtimestamp(timestamp)
        
        # 1. Check Time Window (24h)
        if item_time < cutoff:
            continue
            
        time_str = item_time.strftime('%H:%M')
        title = item.get('title', '') or item.get('content', '')[:50]
        # Clean title
        title = re.sub(r'【.*?】', '', title).strip()
        # Remove brief or empty
        if len(title) < 8: 
            continue
        
        # Deduplicate
        if title in unique_titles:
            continue
        unique_titles.add(title)
        
        full_content = item.get('content', '')
        
        # 2. Categorize
        if '财联社' in title and '电' in title: # Clean up standard prefix
            title = re.sub(r'^财联社\d+月\d+日电，?', '', title)

        # Skip boring items
        if "日元" in title and "汇率" in title: pass # Keep?
        
        # Score importance (heuristic)
        is_important = False
        
        # Create display string with time
        display_str = f"[{time_str}] {title}"
        
        if any(k in title or k in full_content for k in kw_global):
            highlights['global'].append(display_str)
        elif any(k in title or k in full_content for k in kw_china):
            highlights['china'].append(display_str)
        elif any(k in title or k in full_content for k in kw_market):
            highlights['market'].append(display_str) # For market table, we might process differently, but string layout is flexible
        else:
            # Fallback for generic high impact?
            pass
            
    # Limit counts
    return {k: v[:8] for k, v in highlights.items()}

def generate_prompt(date_str, output_dir):
    """Generate Prompt with CLS 24h Data"""
    date_disp = datetime.strptime(date_str, '%Y%m%d').strftime('%m月%d日')
    
    # 1. Fetch & Process
    raw_data = fetch_cls_telegraphs(limit=150) # Fetch more to ensure coverage
    data = filter_last_24h_highlights(raw_data)
    
    # 2. Format
    # Global
    global_txt = ""
    for t in data['global'][:6]:
        global_txt += f"- {t}\n"
    if not global_txt: global_txt = "- [暂无重大全球消息]"
        
    # China
    china_txt = ""
    for t in data['china'][:6]:
        china_txt += f"- {t}\n"
    if not china_txt: china_txt = "- [暂无重大国内政策]"
        
    # Market
    market_txt = ""
    for t in data['market'][:5]:
        # t is "[HH:MM] Title..."
        # We want to extract time and title for table
        # Simple split, assuming format hasn't changed
        try:
            time_part = t[1:6] # HH:MM
            content_part = t[8:]
            market_txt += f"| {time_part} | {content_part[:10]}.. | 关注 |\n"
        except:
             market_txt += f"| --:-- | {t[:10]}.. | 关注 |\n"
             
    if not market_txt: market_txt = "| --:-- | 暂无异动 | -- |\n"

    content = f"""# 全球财经日历 24h - AI绘图Prompt ({date_disp})
# 数据来源: 财联社 (近24小时滚动聚合)

## 图片规格
- 比例: 9:16 竖版
- 风格: 手绘/手账风格，暖色纸张质感
- 背景色: #F5E6C8 纸黄色

## 标题
**📅 财联社 24h 核心精选** (红色)
**CLS Telegraph | {date_disp}**

---

## 🌍 全球宏观 (Global & Macro)

### 🇺🇸 国际/美元
{global_txt}

### 🇨🇳 中国/政策
{china_txt}

---

## 📊 市场热点 (Market Movers)

| 时间 | 热点事件 | 状态 |
|------|----------|------|
{market_txt}

---

## 💡 交易提醒
- 这里汇总了过去24小时最重要的财经新闻
- ⚠️ 重点关注上述政策对A股的影响

## AI绘图Prompt (English)

Hand-drawn financial infographic poster, Cailianpress news, Global market summary {date_disp}.

**Style**: Warm cream paper texture (#F5E6C8), vintage notebook aesthetic, handwritten Chinese fonts.

**Layout**:
- Title: "CLS News" hand-drawn style.
- Section 1: Global/China News List (Hand-drawn flags).
- Section 2: Market Events Table.
- Footer: "CLS.cn".

(Optimized for hand-drawn financial briefing)
"""
    path = os.path.join(output_dir, "AI提示词", "金十数据_Prompt.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Saved: {path}")

def run(date_str, output_dir):
    generate_prompt(date_str, output_dir)
