"""
Market Sentiment Analysis - Core Logic
Aggregates market data and calculates Greed & Fear Index (0-100).
"""

import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any
import sys
import os
import requests
import re

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from modules.fish_basin.fish_basin import fetch_data
from modules.market_ladder.limit_up_ladder import get_limit_up_data
from modules.core_news.core_news_monitor import fetch_eastmoney_data


def get_limit_down_count(date_str: str = None) -> int:
    """
    Get the count of limit down stocks for a given date.

    Args:
        date_str: Date string in YYYYMMDD format. If None, uses today.

    Returns:
        Count of limit down stocks
    """
    try:
        # Get limit down pool from akshare
        df = ak.stock_zt_pool_dtgc_em(date=date_str or datetime.now().strftime("%Y%m%d"))
        return len(df) if df is not None and not df.empty else 0
    except Exception as e:
        print(f"Error fetching limit down data: {e}")
        return 0


def get_volume_from_previous_prompt(date_str: str) -> float:
    """
    Try to get volume from previous day's prompt file.

    Args:
        date_str: Date string in YYYYMMDD format.

    Returns:
        Volume in Yuan (float) or 0.0 if not found
    """
    try:
        if not date_str:
            date_str = datetime.now().strftime("%Y%m%d")

        current_date = datetime.strptime(date_str, "%Y%m%d")
        prev_date = current_date - timedelta(days=1)
        prev_date_str = prev_date.strftime("%Y%m%d")

        file_path = os.path.join("results", prev_date_str, "AI提示词", "市场情绪_Prompt.txt")

        if not os.path.exists(file_path):
            # Try checking absolute path if relative path fails or debug info
            # print(f"   Previous prompt file not found: {file_path}")
            return 0.0

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Regex search for 今日成交: **(\d+) 亿**
        match = re.search(r"今日成交: \*\*(\d+) 亿\*\*", content)
        if match:
            vol_yi = float(match.group(1))
            print(f"   Recovered volume from file ({prev_date_str}): {vol_yi}亿")
            return vol_yi * 1e8

        return 0.0
    except Exception as e:
        print(f"   Error reading previous prompt: {e}")
        return 0.0



def get_market_volume_sina() -> float:
    """
    Fetch real-time market volume (SH + SZ) from Sina Finance.
    Returns total volume in Yuan (float).
    Returns 0.0 if failed.
    """
    url = "http://hq.sinajs.cn/list=s_sh000001,s_sz399001"
    headers = {"Referer": "https://finance.sina.com.cn/"}
    
    print("📊 Fetching Real-time Volume from Sina Finance...")
    try:
        response = requests.get(url, headers=headers, timeout=5)
        response.encoding = 'gbk'
        data = response.text
        
        # Parse response
        # var hq_str_s_sh000001="Name,Price,Chg,Pct,Vol,Turnover(Wan)";
        total_volume = 0.0
        parsed_count = 0
        
        lines = data.strip().split('\n')
        for line in lines:
            if 'hq_str_s_' not in line:
                continue
            
            parts = line.split('=')
            if len(parts) < 2:
                continue
                
            content = parts[1].strip('";')
            fields = content.split(',')
            
            if len(fields) >= 6:
                # Index 5 is Turnover in Wan
                try:
                    vol_wan = float(fields[5])
                    vol_yuan = vol_wan * 10000
                    total_volume += vol_yuan
                    parsed_count += 1
                except ValueError:
                    continue
        
        if parsed_count == 2: # Should have both SH and SZ
            print(f"✅ Sina Volume: {total_volume/1e8:.0f}亿")
            return total_volume
        else:
            print(f"⚠️ Sina data incomplete (parsed {parsed_count} indices)")
            return 0.0
            
    except Exception as e:
        print(f"❌ Error fetching Sina volume: {e}")
        return 0.0


def get_market_volume(date_str: str = None) -> Dict[str, float]:
    """
    Get market turnover volume for today and yesterday.
    Primary: Sina (for Today) + AkShare (for Yesterday).
    Fallback: AkShare (for both).

    Returns:
        Dictionary with today_volume, yesterday_volume, change_pct (Volumes in Yuan)
    """
    target_date = date_str or datetime.now().strftime("%Y%m%d")
    is_today = (target_date == datetime.now().strftime("%Y%m%d"))
    
    # 1. Fetch Historical Data (AkShare) to get Yesterday's volume
    # We always need this for comparison
    end_dt = datetime.strptime(target_date, "%Y%m%d")
    start_dt = end_dt - timedelta(days=15) # 15 days back to be safe
    start_date_s = start_dt.strftime("%Y%m%d")
    
    yesterday_vol = 0.0
    ak_today_vol = 0.0
    
    print(f"📊 Fetching History for comparison ({start_date_s} - {target_date})...")
    
    try:
        df_sh = ak.index_zh_a_hist(symbol="000001", period="daily", start_date=start_date_s, end_date=target_date)
        df_sz = ak.index_zh_a_hist(symbol="399001", period="daily", start_date=start_date_s, end_date=target_date)
        
        if df_sh is not None and not df_sh.empty and df_sz is not None and not df_sz.empty:
             # Standardize dates
            df_sh['date_str'] = pd.to_datetime(df_sh['日期']).dt.strftime("%Y%m%d")
            df_sz['date_str'] = pd.to_datetime(df_sz['日期']).dt.strftime("%Y%m%d")

            # Merge
            df = pd.merge(df_sh[['date_str', '成交额']], df_sz[['date_str', '成交额']], on='date_str', suffixes=('_sh', '_sz'))
            df['total_vol'] = df['成交额_sh'] + df['成交额_sz']
            df = df.sort_values('date_str')
            
            # Identify Yesterday
            # If target_date is in df, yesterday is the row before it
            # If target_date is NOT in df (e.g. today during trading), yesterday is the last row
            
            row_target = df[df['date_str'] == target_date]
            
            if not row_target.empty:
                # Target date exists in history (e.g. backtesting or after close)
                ak_today_vol = float(row_target.iloc[0]['total_vol'])
                
                # Get previous row
                idx = df.index[df['date_str'] == target_date].tolist()[0]
                # Since we sorted by date_str, but the index might not be sequential integers if we didn't reset
                # Let's rely on position
                pos = df.index.get_loc(idx)
                if pos > 0:
                    yesterday_vol = float(df.iloc[pos - 1]['total_vol'])
            else:
                # Target date not in history (likely today during trading)
                # Then the last row in df is the most recent trading day (Yesterday)
                if not df.empty:
                    yesterday_vol = float(df.iloc[-1]['total_vol'])
                    print(f"   Using latest history ({df.iloc[-1]['date_str']}) as Yesterday.")
                    
    except Exception as e:
        print(f"⚠️ Error fetching history from AkShare: {e}")

    # Fallback if yesterday_vol is still 0
    if yesterday_vol == 0:
        print("   Trying to fetch yesterday's volume from previous prompt...")
        yesterday_vol = get_volume_from_previous_prompt(target_date)

    # 2. Get Today's Volume
    today_vol = 0.0
    
    if is_today:
        # Try Sina First
        sina_vol = get_market_volume_sina()
        if sina_vol > 0:
            today_vol = sina_vol
        else:
            print("   Sina failed, falling back to AkShare for today...")
            today_vol = ak_today_vol
    else:
        # Not today (Backtesting), must use AkShare
        today_vol = ak_today_vol

    # 3. Calculate Change
    change_pct = 0.0
    if yesterday_vol > 0:
        change_pct = ((today_vol - yesterday_vol) / yesterday_vol) * 100
        
    print(f"✅ Final Volume: Today={today_vol/1e8:.0f}亿, Yesterday={yesterday_vol/1e8:.0f}亿, Change={change_pct:+.2f}%")
    
    return {
        "today_volume": today_vol,
        "yesterday_volume": yesterday_vol,
        "change_pct": round(change_pct, 2)
    }


def get_indices_performance() -> Dict[str, float]:
    """
    Get performance (% change) for major indices.
    
    Returns:
        Dictionary with index names and their % changes
    """
    indices = {
        "上证50": "sh000016",
        "沪深300": "sh000300",
        "中证500": "sh000905",
        "中证2000": "sh932000"
    }
    
    performance = {}
    
    for name, code in indices.items():
        try:
            df = fetch_data(name, code)
            if df is not None and not df.empty and len(df) >= 2:
                latest = df.iloc[-1]['close']
                previous = df.iloc[-2]['close']
                pct_change = ((latest - previous) / previous) * 100
                performance[name] = round(pct_change, 2)
            else:
                performance[name] = 0.0
        except Exception as e:
            print(f"Error fetching {name} performance: {e}")
            performance[name] = 0.0
    
    return performance


def get_market_news_sentiment() -> Dict[str, Any]:
    """
    Analyze news sentiment from core news.
    
    Returns:
        Dictionary with bullish/bearish counts and sample headlines
    """
    try:
        # Fetch news from last 24 hours
        news_data = fetch_eastmoney_data(target_window_hours=24)
        
        if not news_data:
            return {
                "bullish_count": 0,
                "bearish_count": 0,
                "neutral_count": 0,
                "bullish_news": [],
                "bearish_news": []
            }
        
        # Simple sentiment classification based on keywords
        bullish_keywords = ['上涨', '利好', '突破', '创新高', '大涨', '暴涨', '涨停', '牛市', '看多']
        bearish_keywords = ['下跌', '利空', '跌破', '创新低', '大跌', '暴跌', '跌停', '熊市', '看空']
        
        bullish_news = []
        bearish_news = []
        neutral_count = 0
        
        for item in news_data:
            title = item.get('title', '')
            
            is_bullish = any(kw in title for kw in bullish_keywords)
            is_bearish = any(kw in title for kw in bearish_keywords)
            
            if is_bullish and not is_bearish:
                bullish_news.append(title)
            elif is_bearish and not is_bullish:
                bearish_news.append(title)
            else:
                neutral_count += 1
        
        return {
            "bullish_count": len(bullish_news),
            "bearish_count": len(bearish_news),
            "neutral_count": neutral_count,
            "bullish_news": bullish_news[:5],  # Top 5
            "bearish_news": bearish_news[:5]   # Top 5
        }
    
    except Exception as e:
        print(f"Error analyzing news sentiment: {e}")
        return {
            "bullish_count": 0,
            "bearish_count": 0,
            "neutral_count": 0,
            "bullish_news": [],
            "bearish_news": []
        }


def get_sector_flow() -> Dict[str, Any]:
    """
    Get sector fund flow data.
    Multi-source: 东财 API → 同花顺 → 文件解析
    
    Returns:
        Dictionary with net inflow and top flowing sectors
    """
    # Source 1: 东财 (Eastmoney) API
    try:
        print("💰 Trying Source 1: Eastmoney API for money flow...")
        df = ak.stock_sector_fund_flow_rank(indicator="今日")
        
        if df is None or df.empty:
            raise Exception("API returned empty data")
        
        # Calculate total net inflow
        net_inflow = df['净额'].sum() if '净额' in df.columns else 0
        
        # Get top 3 inflow and outflow sectors
        df_sorted = df.sort_values('净额', ascending=False)
        inflow_sectors = df_sorted.head(3)[['名称', '净额']].to_dict('records') if len(df_sorted) > 0 else []
        outflow_sectors = df_sorted.tail(3)[['名称', '净额']].to_dict('records') if len(df_sorted) > 0 else []
        
        print(f"✅ Eastmoney money flow: Net {net_inflow/1e8:.0f}亿, {len(inflow_sectors)} inflows, {len(outflow_sectors)} outflows")
        return {
            "net_inflow": net_inflow,
            "inflow_sectors": inflow_sectors,
            "outflow_sectors": outflow_sectors
        }
    except Exception as e:
        print(f"❌ Eastmoney API failed: {e}")
    
    # Source 2: 同花顺 (Tonghuashun) - try alternative approach
    try:
        print("💰 Trying Source 2: Tonghuashun for money flow...")
        # Use stock_sector_fund_flow_rank with alternative params
        df = ak.stock_fund_flow_individual(symbol="000001")
        if df is not None and not df.empty:
            # This is a fallback, data might not be perfect
            print(f"⚠️ Tonghuashun returned limited data, trying file parsing...")
            raise Exception("Tonghuashun data insufficient")
    except Exception as e:
        print(f"❌ Tonghuashun failed: {e}")
    
    # Source 3: 文件解析 (File parsing from existing prompt)
    try:
        print("💰 Trying Source 3: File parsing for money flow...")
        import re
        today = datetime.now().strftime("%Y%m%d")
        prompt_file = os.path.join("results", today, "AI提示词", "资金流向_Prompt.txt")
        
        if not os.path.exists(prompt_file):
            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")
        
        with open(prompt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract inflow sectors and amounts
        # Extract inflow sectors and amounts
        # Improved Regex to capture Clean Names:  **"银行"** or "银行"
        sector_pattern = r'["\']?([\u4e00-\u9fa5]+)["\']?[^+]*?\+([0-9.]+)亿'
        sector_matches = re.findall(sector_pattern, content)
        
        # Extract outflow data
        outflow_pattern = r'([\u4e00-\u9fa5]+)\s*\(-([0-9.]+)亿\)'
        outflow_matches = re.findall(outflow_pattern, content)
        
        inflow_sectors = [{'名称': name.strip(), '净额': float(val) * 1e8} for name, val in sector_matches if name.strip()][:3]
        outflow_sectors = [{'名称': name.strip(), '净额': -float(val) * 1e8} for name, val in outflow_matches if name.strip()][:3]
        
        # Calculate net inflow
        net_inflow = sum(s['净额'] for s in inflow_sectors) + sum(s['净额'] for s in outflow_sectors)
        
        print(f"✅ File parsing: Net {net_inflow/1e8:.0f}亿, {len(inflow_sectors)} inflows, {len(outflow_sectors)} outflows")
        if inflow_sectors:
            print(f"   Inflows: {[s['名称'] for s in inflow_sectors]}")
        if outflow_sectors:
            print(f"   Outflows: {[s['名称'] for s in outflow_sectors]}")
        
        return {
            "net_inflow": net_inflow,
            "inflow_sectors": inflow_sectors,
            "outflow_sectors": outflow_sectors
        }
    
    except Exception as e2:
        print(f"❌ File parsing also failed: {e2}")
    
    print("❌ All money flow sources failed, returning zeros")
    return {
        "net_inflow": 0,
        "inflow_sectors": [],
        "outflow_sectors": []
    }


def aggregate_market_data(date_str: str = None) -> Dict[str, Any]:
    """
    Aggregate all market data needed for sentiment analysis.
    
    Returns:
        Dictionary containing all aggregated market data
    """
    print("Aggregating market data...")
    
    # Get all data sources
    indices_perf = get_indices_performance()
    
    # Limit Up
    df_zt, _, _ = get_limit_up_data(date_str or datetime.now().strftime("%Y%m%d"))
    limit_up_count = len(df_zt) if df_zt is not None else 0
    
    limit_down_count = get_limit_down_count(date_str)
    news_sentiment = get_market_news_sentiment()
    sector_flow = get_sector_flow()
    volume_data = get_market_volume(date_str)
    
    data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "indices": indices_perf,
        "limit_up_count": limit_up_count,
        "limit_down_count": limit_down_count,
        "news_sentiment": news_sentiment,
        "sector_flow": sector_flow,
        "volume": volume_data
    }
    
    print("Market data aggregation complete.")
    return data


def calculate_sentiment_index(market_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate the Greed & Fear Index (0-100) based on market data.
    
    Algorithm:
    - Base Score: 50
    - Market Breadth (30%): Based on limit up/down ratio
    - Indices Trend (30%): Weighted average of major indices
    - News Sentiment (20%): Balance of bullish/bearish news
    - Money Flow (20%): Net sector inflows
    
    Args:
        market_data: Aggregated market data dictionary
    
    Returns:
        Dictionary with index value and breakdown
    """
    base_score = 50
    scores = {}
    
    # 1. Market Breadth Score (30%) - Range: -15 to +15
    limit_up = market_data['limit_up_count']
    limit_down = market_data['limit_down_count']
    total_limit = limit_up + limit_down
    
    if total_limit > 0:
        breadth_ratio = (limit_up - limit_down) / total_limit
        breadth_score = breadth_ratio * 15  # Scale to -15 to +15
    else:
        breadth_score = 0
    
    scores['market_breadth'] = round(breadth_score, 2)
    
    # 2. Indices Trend Score (30%) - Range: -15 to +15
    indices = market_data['indices']
    weights = {
        "上证50": 0.2,
        "沪深300": 0.3,
        "中证500": 0.3,
        "中证2000": 0.2
    }
    
    weighted_change = sum(indices.get(name, 0) * weight for name, weight in weights.items())
    # Normalize: assume -3% to +3% maps to -15 to +15
    indices_score = max(-15, min(15, weighted_change * 5))
    scores['indices_trend'] = round(indices_score, 2)
    
    # 3. News Sentiment Score (20%) - Range: -10 to +10
    news = market_data['news_sentiment']
    bullish = news['bullish_count']
    bearish = news['bearish_count']
    total_news = bullish + bearish
    
    if total_news > 0:
        news_ratio = (bullish - bearish) / total_news
        news_score = news_ratio * 10
    else:
        news_score = 0
    
    scores['news_sentiment'] = round(news_score, 2)
    
    # 4. Money Flow Score (20%) - Range: -10 to +10
    net_inflow = market_data['sector_flow']['net_inflow']
    # Normalize: assume -100亿 to +100亿 maps to -10 to +10
    flow_score = max(-10, min(10, net_inflow / 1e9))
    scores['money_flow'] = round(flow_score, 2)
    
    # Calculate final index
    final_index = base_score + sum(scores.values())
    final_index = max(0, min(100, round(final_index, 1)))  # Clamp to 0-100
    
    # Determine sentiment level
    if final_index >= 70:
        sentiment_level = "极度贪婪"
        color = "red"
    elif final_index >= 55:
        sentiment_level = "贪婪"
        color = "orange"
    elif final_index >= 45:
        sentiment_level = "中性"
        color = "yellow"
    elif final_index >= 30:
        sentiment_level = "恐惧"
        color = "blue"
    else:
        sentiment_level = "极度恐惧"
        color = "dark_blue"
    
    return {
        "index": final_index,
        "sentiment_level": sentiment_level,
        "color": color,
        "score_breakdown": scores,
        "raw_data": market_data
    }


def generate_prompt_content(result: Dict[str, Any], market_data: Dict[str, Any], date_str: str = None) -> str:
    """Generate AI Prompt content"""
    idx = result['index']
    level = result['sentiment_level']
    breadth = result['score_breakdown']['market_breadth']
    indices_trend = result['score_breakdown']['indices_trend']
    news_score = result['score_breakdown']['news_sentiment']
    flow_score = result['score_breakdown']['money_flow']
    
    limit_up = market_data['limit_up_count']
    limit_down = market_data['limit_down_count']
    
    bullish = market_data['news_sentiment']['bullish_count']
    bearish = market_data['news_sentiment']['bearish_count']
    
    net_inflow = market_data['sector_flow']['net_inflow'] / 1e8
    inflow_sectors = market_data['sector_flow']['inflow_sectors'][:3]
    outflow_sectors = market_data['sector_flow']['outflow_sectors'][:3]
    
    # Volume data
    vol_today = market_data['volume']['today_volume'] / 1e8
    vol_yesterday = market_data['volume']['yesterday_volume'] / 1e8
    vol_change = market_data['volume']['change_pct']
    
    if vol_today == 0:
        vol_desc = "暂无数据 (接口异常)"
        vol_change_desc = "数据缺失"
        vol_trend_desc = "无法判断"
    else:
        vol_desc = f"放量{vol_change:.1f}%" if vol_change > 0 else f"缩量{abs(vol_change):.1f}%"
        vol_change_desc = "红色" if vol_change > 5 else "绿色" if vol_change < -5 else "黄色"
        vol_trend_desc = "成交额显著放大，市场活跃度提升" if vol_change > 10 else "成交额小幅放大" if vol_change > 0 else "缩量震荡，观望情绪浓厚" if vol_change > -10 else "成交额大幅萎缩，市场谨慎"
    
    # Conditional strings (避免f-string嵌套)
    idx_color = "红色粗体" if idx >= 70 else "橙色粗体" if idx >= 55 else "黄色粗体"
    level_color = "橙红色标签" if idx >= 70 else "橙色标签"
    breadth_desc = "涨停家数远超跌停,市场赚钱效应强" if limit_up > limit_down * 3 else "市场分化，涨跌停相对均衡"
    indices_desc = "主流指数全线飘红" if indices_trend > 2 else "指数整体平稳" if indices_trend > -2 else "指数集体调整"
    news_desc = "正面新闻占优,市场情绪活跃" if news_score > 2 else "新闻情绪中性" if news_score > -2 else "负面新闻增多"
    
    warning_emoji = "⚠️" if flow_score < -5 else ""
    flow_desc = "净流出" if net_inflow < 0 else "净流入"
    flow_color = "红色警告" if net_inflow < -300 else "绿色" if net_inflow > 300 else "中性"
    
    # Build prompt
    prompt = f"""# 市场情绪指数 - AI绘图Prompt ({datetime.now().strftime("%m月%d日")})
# 数据来源: 恐贪指数模型 (4维度综合评分)

## 图片规格
- 比例: 9:16 竖版
- 风格: 手绘/手账风格，暖色纸张质感
- 背景色: #F5E6C8 纸黄色
- 配色: 贪婪=红色渐变, 恐惧=蓝色渐变

## 标题
**📊 A股恐贪指数 | Market Greed & Fear** (居中，手绘字体)
**{datetime.now().strftime("%Y-%m-%d")}**

---

## 核心指标 (大号显示)
**恐贪指数: {idx}/100** ({idx_color})
**情绪等级: {level}** ({level_color})

---

## 四维度评分可视化 (进度条/雷达图)

### 1. 市场宽度 (Market Breadth) {breadth:+.2f}
- 涨停: {limit_up} 只 (红色)
- 跌停: {limit_down} 只 (绿色)
- 说明: {breadth_desc}

### 2. 指数趋势 (Indices Trend) {indices_trend:+.2f}
"""
    
    for idx_name, change in market_data['indices'].items():
        arrow = "↑" if change > 0 else "↓" if change < 0 else "→"
        prompt += f"- {idx_name}: {change:+.2f}% {arrow}\n"
    
    prompt += f"- 说明: {indices_desc}\n\n"
    
    prompt += f"""### 3. 新闻情绪 (News Sentiment) {news_score:+.2f}
- 利多消息: {bullish} 条 (红色)
- 利空消息: {bearish} 条 (绿色)
- 说明: {news_desc}

### 4. 资金流向 (Money Flow) {flow_score:+.2f} {warning_emoji}
- {flow_desc}: **{abs(net_inflow):.2f} 亿** ({flow_color})
"""
    
    if inflow_sectors:
        sector_list = "、".join([f"{s['名称']} +{s['净额']/1e8:.0f}亿" for s in inflow_sectors])
        prompt += f"- 流入板块: {sector_list}\n"
    
    if outflow_sectors:
        sector_list = "、".join([f"{s['名称']} {s['净额']/1e8:.0f}亿" for s in outflow_sectors])
        prompt += f"- 流出板块: {sector_list}\n"
    
    if net_inflow < -300:
        prompt += "- 说明: **大量资金撤离，市场避险情绪升温**\n"
    elif net_inflow > 300:
        prompt += "- 说明: **资金大幅流入，市场做多意愿强烈**\n"
    else:
        prompt += "- 说明: 资金观望，板块轮动\n"
    
    # Volume section
    prompt += f"""
### 5. 成交额 (Market Volume)
- 今日成交: **{vol_today:.0f} 亿**
- 昨日成交: **{vol_yesterday:.0f} 亿**
- 对比昨日: **{vol_desc}** ({vol_change_desc})
- 说明: {vol_trend_desc}

---
"""
    
    # AI Trend Content
    ai_trend_content = ""
    if date_str:
        try:
            trend_path = os.path.join("results", date_str, "agent_outputs", "result_trend_summary.txt")
            if os.path.exists(trend_path):
                with open(trend_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                if content:
                    ai_trend_content = f"\n> \n> {content}"
        except Exception:
            pass

    # Interpretation
    if idx >= 70 and net_inflow < -300:
        interpretation = f"虽然涨停家数领先，但资金净流出超{abs(net_inflow):.0f}亿且{vol_desc}，显示机构在高位减仓。短期谨防追高风险！"
    elif idx >= 55:
        interpretation = f"市场情绪偏乐观，{vol_desc}。但需关注资金流向变化。"
    else:
        interpretation = f"市场情绪谨慎，{vol_desc}，建议控制仓位。"

    advice = "观望为主 | 严控仓位" if net_inflow < -300 else "逢低布局 | 控制仓位"
    risk = f"资金大幅流出{abs(net_inflow):.0f}亿且{vol_desc}" if net_inflow < -300 else f"指数{idx:.1f}，注意回调风险"

    prompt += f"""
## 情绪解读 (手写体文字框)
> **当前处于"{level}"区间{"，但需警惕！" if idx >= 70 and net_inflow < -300 else ""}**
> {interpretation}{ai_trend_content}

---

## 投资建议 (红色标签提示框)
✅ **操作建议**: {advice}  
⚠️ **风险提示**: {risk}

---

## Footer
"每日恐贪指数 | AI量化情绪模型 | 点赞关注不迷路"

---

## AI绘图Prompt (English)

Hand-drawn financial infographic poster, China A-share Market Greed & Fear Index.

**Style**: Warm cream paper texture (#F5E6C8), vintage notebook aesthetic, hand-drawn Chinese fonts.

**Color Coding**: 
- Greed Level ({idx}) = {"RED gradient" if idx >= 70 else "ORANGE gradient"}
- Progress bars: Bullish = RED fill, Bearish = GREEN fill

**Layout (Vertical 9:16)**:
1. Title: "恐贪指数 {idx}" (large {"red" if idx >= 70 else "orange"} number, hand-drawn style)
2. Sentiment Level Badge: "{level}" ({"orange-red" if idx >= 70 else "orange"} tag)
3. Five Dimensions Section:
   - Market Breadth: {limit_up}涨停 vs {limit_down}跌停 (red vs green comparison bar)
   - Indices Trend: Mini arrow chart
   - News Sentiment: {bullish} bullish vs {bearish} bearish
   - Money Flow: {"**CRITICAL**" if net_inflow < -300 else ""} {net_inflow:.2f}亿 ({"RED WARNING with downward arrow" if net_inflow < -300 else "GREEN upward arrow" if net_inflow > 300 else "gray neutral bar"})
   - Volume: {vol_desc}, Today {vol_today:.0f}亿 vs Yesterday {vol_yesterday:.0f}亿
4. Interpretation Box: Hand-written style text
5. Footer: "每日恐贪指数 | AI量化情绪模型"

**Visual Emphasis**:
- Large "{idx}" with {"red" if idx >= 70 else "orange"} glow
- Progress bars with paper texture
- Hand-drawn icons: 📊📈⚠️
"""
    
    if net_inflow < -300:
        prompt += "- **Money Flow section**: Red warning badge with downward arrows\n"
    
    if abs(vol_change) > 10:
        prompt += f"- **Volume section**: Highlight {vol_desc} with {'red' if vol_change > 10 else 'green'} emphasis\n"
    
    return prompt


def run_analysis(date_str: str = None) -> Dict[str, Any]:
    """
    Main entry point for market sentiment analysis.

    Args:
        date_str: Date string in YYYYMMDD format. If None, uses today.

    Returns:
        Sentiment analysis result dictionary
    """
    print(f"Running market sentiment analysis for {date_str or 'today'}...")

    # Aggregate market data
    market_data = aggregate_market_data(date_str)

    # Calculate sentiment index
    result = calculate_sentiment_index(market_data)

    # Generate and save prompt
    date_s = date_str or datetime.now().strftime("%Y%m%d")
    output_dir = os.path.join("results", date_s, "AI提示词")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "市场情绪_Prompt.txt")
    
    prompt_content = generate_prompt_content(result, market_data, date_s)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(prompt_content)
    
    print(f"\n✅ Analysis complete: {result['index']}/100 ({result['sentiment_level']})")
    print(f"📄 Prompt saved to: {output_path}")

    return result


if __name__ == "__main__":
    # Run analysis and save results
    run_analysis()
