"""
[Module 7] Economic Monitor (Source: EastMoney 7x24)
Generates:
1. Economic Brief Prompt (Daily Top 10 + Targeted Sentiment)
2. Weekly Core Summary (Weekly Top 10 + Targeted Sentiment)
Source: EastMoney (东方财富) 7x24 Global Live Feed
Features: 24h/7d Deep Fetch + Sector-Level Sentiment + Dynamic Footer Summary
"""
import requests
import json
from datetime import datetime, timedelta
import os
import re
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def fetch_eastmoney_data(target_window_hours=24):
    """Fetch 7x24 news from EastMoney until target window covered"""
    base_url = "https://newsapi.eastmoney.com/kuaixun/v1/getlist_102_ajaxResult_50_{}_.html"
    
    all_data = []
    cutoff_time = datetime.now() - timedelta(hours=target_window_hours)
    
    max_pages = 150 if target_window_hours > 24 else 20
    
    for page in range(1, max_pages + 1):
        url = base_url.format(page)
        try:
            r = requests.get(url, headers=HEADERS, timeout=5)
            if r.status_code == 200:
                text = r.text
                if "var ajaxResult=" in text:
                    json_str = text.split("var ajaxResult=")[1].strip().rstrip(";")
                    data = json.loads(json_str)
                    items = data.get('LivesList', [])
                    
                    if not items: break
                        
                    for item in items:
                        showtime = item.get('showtime', '')
                        try:
                            item_dt = datetime.strptime(showtime, "%Y-%m-%d %H:%M:%S")
                        except:
                            continue
                            
                        if item_dt < cutoff_time:
                            # Reached limit
                            all_data.append({'time': item_dt, 'title': item.get('digest', ''), 'code': item.get('code', '')})
                            return all_data
                            
                        all_data.append({
                            'time': item_dt, 
                            'title': item.get('digest', ''),
                            'code': item.get('code', '')
                        })
                else:
                    break
            else:
                break
        except Exception as e:
            print(f"Error: {e}")
            break
            
        time.sleep(0.1)
        
    return all_data

def get_sentiment_and_target(text):
    """Analyze Sentiment AND Target Sector"""
    direction = ""
    bullish_kw = ['增长', '大增', '倍增', '突破', '新高', '获批', '中标', '回购', '增持', '分红', '利好', '落地', '印发', '通过', '复苏', '上调', '买入', '增仓', '解禁', '上市', 'IPO', '大涨', '涨停']
    bearish_kw = ['下跌', '大跌', '新低', '亏损', '立案', '调查', '处罚', '警示', '退市', '减持', '抛售', '下调', '放缓', '萎缩', '违约', '暴雷', '监管', '烂尾']
    
    score = 0
    for k in bullish_kw:
        if k in text: score += 1
    for k in bearish_kw:
        if k in text: score -= 1
        
    if score > 0: direction = "利多"
    if score < 0: direction = "利空"
    
    # 2. Determine Target Sector
    target = ""
    sector_map = {
        '电子': ['芯片', '半导体', '集成电路', '华为', '苹果', '手机', '消费电子', '面板'],
        'AI': ['人工智能', 'AI', '大模型', '算力', '英伟达', 'OpenAI', 'Sora'],
        '新能源': ['光伏', '电池', '锂', '宁德时代', '储能', '风电'],
        '汽车': ['汽车', '比亚迪', '问界', '理想', '特斯拉', '自动驾驶'],
        '地产': ['房地产', '楼市', '万科', '保利', '恒大', '销售面积', '拿地', '物业'],
        '金融': ['银行', '券商', '证券', '保险', '社融', '信贷', 'LPR', '降准', '降息', '货币'],
        '医药': ['药', '医疗', '器械', '获批', '临床'],
        '白酒': ['白酒', '茅台', '五粮液'],
        '低空': ['低空经济', '飞行汽车', '无人机'],
        '航天': ['航天', '卫星', '火箭'],
        '宏观': ['GDP', 'CPI', 'PPI', 'PMI', '央行', '财政部', '发改委', '统计局', '进出口']
    }
    
    for sector, kws in sector_map.items():
        if any(k in text for k in kws):
            target = sector
            break
    
    # Fallback targets
    if not target:
        if '公司' in text or '股份' in text: target = "个股"
        elif direction: target = "行业"
            
    return direction, target

def clean_text_gentle(text):
    """
    Remove bureaucratic headers/dates but keep full semantic meaning.
    Do NOT truncate aggressively.
    """
    # 1. Clean Garbage Headers
    text = re.sub(r'^.*?[:：]', '', text) 
    text = re.sub(r'【.*?】', '', text)
    text = re.sub(r'\(\d{6}\)', '', text)
    text = re.sub(r'据报道[，,]', '', text)
    text = re.sub(r'据.*?消息[，,]', '', text)
    text = re.sub(r'消息称[，,]', '', text)
    text = re.sub(r'数据显示[，,]', '', text)
    text = re.sub(r'记者获悉[，,]', '', text)
    text = re.sub(r'财联社\d+月\d+日电', '', text)
    
    # Text specific fixes
    text = re.sub(r'\d+月\d+日[晚早午]?[，,]', '', text) 
    text = re.sub(r'\d+月\d+日', '', text) 
    
    # 2. Simplify Numbers (Gentle)
    text = text.replace("亿元", "亿").replace("万元", "万")
    text = text.replace("人民币", "")
    text = text.replace("股份有限公司", "")
    text = text.replace("有限责任公司", "")
    
    # 3. Strip dangling brackets
    text = text.replace('】', '').replace('【', '')
    
    # 4. Strip
    final = text.strip()
    # Remove leading punctuation/garbage words
    final = re.sub(r'^[晚早午日][，,]', '', final)
    final = final.lstrip('，,。.:')
    
    return final

def calculate_importance(title):
    """Score logic: Kill International, Kill Index, Boost A-Share"""
    score = 0
    text = title
    
    # 0. STRICT BLACKLIST (International / Noise)
    blacklist = [
        '美联储', '纳斯达克', '道琼斯', '标普', '拜登', '美元', '欧元', '日元', '英镑', '韩元',
        '欧央行', 'WTI', '布伦特', '比特币', '以太坊', 
        '英国', '德国', '法国', '日本', '韩国', '印度', '越南', '委内瑞拉', '伊朗',
        '收盘', '开盘', '早盘', '午盘', '尾盘', '三大指数', '两市', '北向资金', '成交额'
    ]
    
    # Allow logic
    has_china = any(kw in text for kw in ['中国', '央行', 'A股', '中概', '对华', '制裁', '驻华'])
    
    for bad in blacklist:
        if bad in text and not has_china:
            return -100 
            
    if len(text) < 5: return -100

    # 1. Critical Policy
    critical_keywords = [
        '中共中央', '国务院', '政治局', '证监会', '央行', '人民银行', '习近平', '李强', 
        '印花税', '降准', '降息', '社融', '信贷', 'LPR', 'IPO', '平准基金', '国家队',
        '中央汇金', '国新投资', '发改委', '统计局', '财政部', '工信部', '国资委', '金融监管总局'
    ]
    for kw in critical_keywords:
        if kw in text: score += 15
            
    # 2. A-Share Themes
    market_keywords = [
        'A股', '获批', '中标', '回购', '增持', '分红', '业绩', '发布', '印发', '通过',
        '新能源', '光伏', '半导体', '芯片', '人工智能', 'AI', '算力', '华为', '房地产', '楼市',
        '低空经济', '商业航天', '医药', '白酒', '银行', '券商', '保险', '汽车', '电池'
    ]
    for kw in market_keywords:
        if kw in text: score += 5

    score += 1 
    return score

def filter_top_news(data, limit=10, is_weekly=False):
    """Select Top N items and Return (List, BullishSectors, BearishSectors)"""
    candidates = []
    unique_titles = set()
    
    for item in data:
        full_text = item['title']
        clean_text = clean_text_gentle(full_text)
        
        # Dedupe
        clean_key = re.sub(r'[^\w]', '', clean_text)[:8]
        if clean_key in unique_titles: continue
        unique_titles.add(clean_key)
        
        score = calculate_importance(full_text)
        
        if score > 0:
            direction, target = get_sentiment_and_target(full_text)
            
            # STRICT FILTER
            if not direction:
                continue
            
            if len(clean_text) < 4: continue
            
            candidates.append({
                'time': item['time'],
                'title': clean_text,
                'score': score,
                'direction': direction,
                'target': target
            })
            
    # Sort
    candidates.sort(key=lambda x: (x['score'], x['time']), reverse=True)
    top_items = candidates[:limit]
    top_items.sort(key=lambda x: x['time'], reverse=True)
    
    formatted_list = []
    
    # Weekday Map
    wd_map = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    
    # Net Score Logic
    sector_scores = {}
    
    for item in top_items:
        if is_weekly:
            wd_idx = item['time'].weekday()
            t_str = wd_map[wd_idx]
        else:
            t_str = item['time'].strftime('%H:%M')
            
        # Display Tag: Hide generic targets
        generic_targets = ["行业", "宏观", "个股"]
        target_display = ""
        if item['target'] and item['target'] not in generic_targets:
            target_display = item['target']
            sem_tag = f"【{item['direction']}·{item['target']}】"
        else:
            sem_tag = f"【{item['direction']}】"
        
        formatted_list.append(f"[{t_str}]{sem_tag} {item['title']}")
        
        # Accumulate Net Score for Footer
        if target_display:
            curr = sector_scores.get(target_display, 0)
            if item['direction'] == "利多":
                sector_scores[target_display] = curr + 1
            elif item['direction'] == "利空":
                sector_scores[target_display] = curr - 1

    # Separate by Net Score > 0 (Bullish) or < 0 (Bearish)
    bullish_list = [k for k, v in sector_scores.items() if v > 0]
    bearish_list = [k for k, v in sector_scores.items() if v < 0]
    
    return formatted_list, bullish_list, bearish_list

def save_prompt(content, filename, output_dir):
    path = os.path.join(output_dir, "AI提示词", filename)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Saved: {path}")



def run(date_str, output_dir, run_weekly=False):
    date_disp = datetime.strptime(date_str, '%Y%m%d').strftime('%m月%d日')
    
    # 1. Daily Summary
    daily_data = fetch_eastmoney_data(target_window_hours=24)
    daily_top, d_bull, d_bear = filter_top_news(daily_data, limit=10, is_weekly=False)
    
    daily_txt = "\n".join([f"- {news}" for news in daily_top]) or "- [暂无重大A股题材消息]"
    
    d_bull_str = "、".join(d_bull) if d_bull else "无"
    d_bear_str = "、".join(d_bear) if d_bear else "无"
    
    daily_content = f"""# A股财经日历 24h - AI绘图Prompt ({date_disp})
# 数据来源: 东方财富 (Top 10 题材精选)

## 图片规格
- 比例: 9:16 竖版
- 风格: 手绘/手账风格，暖色纸张质感
- 背景色: #F5E6C8 纸黄色
- 配色: 利多=红色, 利空=绿色 (中国A股红涨绿跌)

## 标题
**📅 A股24小时重要资讯精选** (红色)
**A-Share Daily Focus | {date_disp}**

---

## 🇨🇳 A股/题材/政策 (Top 10)

{daily_txt}

---

## 💡 交易提醒
- **利多** (红色)：{d_bull_str}
- **利空** (绿色)：{d_bear_str}
- 总结不易，每天收盘后推送，点赞关注不迷路！

## AI绘图Prompt (English)

Hand-drawn financial infographic poster, China A-share market news, 24h summary {date_disp}.

**Style**: Warm cream paper texture (#F5E6C8), vintage notebook aesthetic, handwritten Chinese fonts.
**Color Coding**: Tags "利多" MUST be RED. Tags "利空" MUST be GREEN.

**Layout**:
- Title: "Important Selection" hand-drawn style.
- Section 1: Top 10 News List with Sector Tags.
- Footer: "Like & Follow".
"""
    save_prompt(daily_content, "核心要闻_Prompt.txt", output_dir)
    
    # 2. Weekly Summary
    if run_weekly:
        print("Generating Weekly Summary...")
        weekly_data = fetch_eastmoney_data(target_window_hours=168)
        weekly_top, w_bull, w_bear = filter_top_news(weekly_data, limit=10, is_weekly=True)
        
        weekly_txt = "\n".join([f"- {news}" for news in weekly_top])
        w_bull_str = "、".join(w_bull) if w_bull else "无"
        w_bear_str = "、".join(w_bear) if w_bear else "无"
        
        weekly_content = f"""# A股本周核心回顾 - AI绘图Prompt
# 数据来源: 东方财富 (7天 Top 10)

## 图片规格
- 比例: 9:16 竖版
- 风格: 手绘/手账风格，暖色纸张质感
- 背景色: #F5E6C8 纸黄色
- 配色: 利多=红色, 利空=绿色 (中国A股红涨绿跌)

## 标题
**📅 A股本周重要回顾** (红色)
**A-Share Weekly Review**

---

## 🇨🇳 本周重磅 (Top 10)
> 过去7天 政策/行业 核心事件

{weekly_txt}

---

## 💡 投资笔记
- **利多** (红色)：{w_bull_str}
- **利空** (绿色)：{w_bear_str}
- 总结不易，每天收盘后推送，点赞关注不迷路！

## AI绘图Prompt (English)

Hand-drawn financial infographic poster, China A-share weekly summary.

**Style**: Warm cream paper texture (#F5E6C8), vintage notebook aesthetic, handwritten Chinese fonts.
**Color Coding**: Tags "利多" MUST be RED. Tags "利空" MUST be GREEN.

**Layout**:
- Title: "Weekly Focus" hand-drawn style.
- Section 1: Top 10 Weekly News List.
- Footer: "Like & Follow".
"""
        save_prompt(weekly_content, "本周要闻_Prompt.txt", output_dir)
