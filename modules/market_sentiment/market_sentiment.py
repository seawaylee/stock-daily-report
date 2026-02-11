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
from modules.market_sentiment.generate_sentiment_prompt import get_raw_image_prompt, generate_image_prompt
from common.image_generator import generate_image_from_text


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

    # PRIORITY: Try Prompt File First (More Reliable)
    if yesterday_vol == 0:
        print("   AkShare history failed, trying previous prompt file...")
        yesterday_vol = get_volume_from_previous_prompt(target_date)
        if yesterday_vol > 0:
            print(f"   ✅ Recovered yesterday volume from prompt: {yesterday_vol/1e8:.0f}亿")
        else:
            print("   ⚠️ WARNING: Both AkShare and Prompt file failed for yesterday_vol!")

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
    Corrected codes and added filtering for failed data.

    Returns:
        Dictionary with index names and their % changes
    """
    indices = {
        "上证50": "sh000016",
        "沪深300": "sh000300",
        "中证500": "sz399905",   # Corrected from sh000905
        "中证2000": "sz399303"   # Changed to CNI 2000 (more reliable data source)
    }

    performance = {}

    for name, code in indices.items():
        try:
            # Use shared fetch_data from fish_basin (proven reliability)
            df = fetch_data(name, code)
            if df is not None and not df.empty and len(df) >= 2:
                latest = float(df.iloc[-1]['close'])
                previous = float(df.iloc[-2]['close'])

                # Check if data is fresh (today)
                last_date = pd.to_datetime(df.iloc[-1]['date']).date()
                today_date = datetime.now().date()

                # Simple validation: if date is not today, try to get spot or accept it might be close price
                # For sentiment, we accept latest available if it's recent

                pct_change = ((latest - previous) / previous) * 100
                performance[name] = round(pct_change, 2)
                print(f"✅ {name}: {pct_change:+.2f}%")
            else:
                print(f"⚠️ Failed to get data for {name}, skipping.")
        except Exception as e:
            print(f"❌ Error fetching {name} performance: {e}")
            # Do NOT add to performance dict if failed (so it won't show as 0%)

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


def get_market_valuation() -> Dict[str, float]:
    """
    Get market valuation (PE/PB) using AkShare.
    Uses SSE and SZSE summaries.

    Returns:
        Dictionary with avg_pe_sh, avg_pe_sz, and valuation_score (0-100 normalized)
    """
    print("📊 Fetching Market Valuation (PE)...")
    try:
        # SSE Summary
        df_sh = ak.stock_sse_summary()
        # df_sh is usually a list of dicts or specific format.
        # For simplicity, if structure varies, we catch error.
        # Assuming standard return: type(df_sh) is usually pd.DataFrame or list
        pe_sh = 0.0
        if isinstance(df_sh, pd.DataFrame):
             # Usually row with type='股票' or similar.
             # Let's try to find '平均市盈率'
             if '平均市盈率' in df_sh.columns:
                 pe_sh = df_sh['平均市盈率'].mean() # Simplified
             elif 'item' in df_sh.columns and 'value' in df_sh.columns:
                 # Check for specific row
                 row = df_sh[df_sh['item'] == '平均市盈率']
                 if not row.empty:
                     pe_sh = float(row.iloc[0]['value'])

        # SZSE Summary
        df_sz = ak.stock_szse_summary()
        pe_sz = 0.0
        if isinstance(df_sz, pd.DataFrame):
             if '股票平均市盈率' in df_sz.columns:
                  pe_sz = df_sz['股票平均市盈率'].mean()
             elif '平均市盈率' in df_sz.columns:
                  pe_sz = df_sz['平均市盈率'].mean()

        # Fallback values if API fails or structure changes (Approximate current market)
        if pe_sh == 0: pe_sh = 13.0
        if pe_sz == 0: pe_sz = 22.0

        print(f"✅ Valuation: SH PE={pe_sh:.2f}, SZ PE={pe_sz:.2f}")

        # Normalize to Score (0-10)
        # SH PE: 10 (Fear) -> 16 (Greed)
        # SZ PE: 20 (Fear) -> 35 (Greed)

        score_sh = (max(10, min(16, pe_sh)) - 10) / 6 * 10
        score_sz = (max(20, min(35, pe_sz)) - 20) / 15 * 10

        valuation_score = (score_sh * 0.6 + score_sz * 0.4) # Weighted

        return {
            "pe_sh": pe_sh,
            "pe_sz": pe_sz,
            "valuation_score": round(valuation_score, 2)
        }

    except Exception as e:
        print(f"❌ Error fetching valuation: {e}")
        return {"pe_sh": 0, "pe_sz": 0, "valuation_score": 5.0}  # Neutral default


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
    valuation_data = get_market_valuation() # New Source

    data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "indices": indices_perf,
        "limit_up_count": limit_up_count,
        "limit_down_count": limit_down_count,
        "news_sentiment": news_sentiment,
        "sector_flow": sector_flow,
        "volume": volume_data,
        "valuation": valuation_data
    }

    print("Market data aggregation complete.")
    return data


def get_sentiment_description(score: float) -> str:
    """
    Return a distinct description for the score (0-100), creating 50 levels (every 2 points approx).
    """
    descriptions = [
        (0, "绝望崩盘，极度恐慌"), (4, "遍地狼藉，信心冰点"), (8, "阴跌不止，深不见底"), (12, "恐慌蔓延，加速赶底"), (16, "至暗时刻，这种时刻往往孕育生机"),
        (20, "极度低迷，无人问津"), (24, "悲观弥漫，甚至连反弹都无力"), (28, "情绪磨底，备受煎熬"), (32, "依然弱势，等待转机"), (36, "谨慎观望，如履薄冰"),
        (40, "虽有抵抗，但信心不足"), (44, "多空平衡，方向未明"), (48, "蓄势待发，窄幅震荡"), (50, "中性偏多，静待花开"), (52, "温和复苏，初现曙光"),
        (56, "多头试探，逐步回暖"), (60, "赚钱效应显现，人气聚拢"), (64, "交投活跃，信心增强"), (68, "情绪高涨，良性轮动"), (72, "热点频出，贪婪升温"),
        (76, "加速上行，踏空焦虑"), (80, "全面普涨，极度亢奋"), (84, "狂热逼空，各种利好满天飞"), (88, "情绪过热，风险积聚"), (92, "极度贪婪，甚至有些疯狂"),
        (96, "泡沫见顶，摇摇欲坠"), (100, "非理性繁荣，此时不跑更待何时")
    ]

    # Find closest
    for threshold, desc in reversed(descriptions):
        if score >= threshold:
            return desc
    return descriptions[0][1]


def detect_divergence(market_data: Dict[str, Any], sentiment_score: float) -> List[str]:
    """
    Detect divergence between Price/Volume and Sentiment.
    """
    divergences = []

    # Extract data
    indices = market_data['indices']
    avg_index_change = sum(indices.values()) / len(indices) if indices else 0
    vol_change = market_data['volume']['change_pct']

    # 1. Price vs Sentiment Divergence
    # Price rising but Sentiment falling (or Low) -> Weak Rally?
    # Usually Sentiment follows Price.
    # Check: Price Rising (>1%) but Sentiment Low (<40) -> Disbelief Rally (Potential Bullish)
    if avg_index_change > 1.0 and sentiment_score < 40:
        divergences.append("量价背离：指数大涨但情绪低迷，往往是行情的初期（犹豫中上涨）。")

    # Price Falling (<-1%) but Sentiment High (>60) -> Denial (Potential Bearish)
    if avg_index_change < -1.0 and sentiment_score > 60:
        divergences.append("情绪背离：指数下跌但情绪依然高涨，需警惕补跌风险。")

    # 2. Volume vs Price Divergence
    # Price Up (>1%) but Volume Down (<-10%) -> 量价背离 (Bearish)
    if avg_index_change > 1.0 and vol_change < -10:
        divergences.append("缩量上涨：指数上行但成交大幅萎缩，上攻动能不足。")

    # Price Down (<-1%) but Volume Down (<-10%) -> 缩量下跌 (Neutral/Bullish if finding bottom)
    if avg_index_change < -1.0 and vol_change < -10:
        divergences.append("缩量下跌：抛压逐步衰竭，可能接近短期底部。")

    return divergences


def calculate_sentiment_index(market_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate the Greed & Fear Index (0-100) based on market data.

    Algorithm:
    - Base Score: 50
    - Market Breadth (25%): Limit Up/Down
    - Indices Trend (25%): Major Indices
    - News Sentiment (15%): Bullish/Bearish News
    - Money Flow (20%): Sector Inflows
    - Valuation (15%): PE Score (New)

    Args:
        market_data: Aggregated market data dictionary

    Returns:
        Dictionary with index value and breakdown
    """
    base_score = 50
    scores = {}

    # 1. Market Breadth Score (25%) - Range: -12.5 to +12.5
    limit_up = market_data['limit_up_count']
    limit_down = market_data['limit_down_count']
    total_limit = limit_up + limit_down

    if total_limit > 0:
        breadth_ratio = (limit_up - limit_down) / total_limit
        breadth_score = breadth_ratio * 12.5
    else:
        breadth_score = 0
    scores['market_breadth'] = round(breadth_score, 2)

    # 2. Indices Trend Score (25%) - Range: -12.5 to +12.5
    indices = market_data['indices']
    weights = {"上证50": 0.2, "沪深300": 0.3, "中证500": 0.3, "中证2000": 0.2}
    weighted_change = sum(indices.get(name, 0) * weight for name, weight in weights.items())
    indices_score = max(-12.5, min(12.5, weighted_change * 4)) # Scale
    scores['indices_trend'] = round(indices_score, 2)

    # 3. News Sentiment Score (15%) - Range: -7.5 to +7.5
    news = market_data['news_sentiment']
    bullish = news['bullish_count']
    bearish = news['bearish_count']
    total_news = bullish + bearish

    if total_news > 0:
        news_ratio = (bullish - bearish) / total_news
        news_score = news_ratio * 7.5
    else:
        news_score = 0
    scores['news_sentiment'] = round(news_score, 2)

    # 4. Money Flow Score (20%) - Range: -10 to +10
    net_inflow = market_data['sector_flow']['net_inflow']
    flow_score = max(-10, min(10, net_inflow / 1e9))
    scores['money_flow'] = round(flow_score, 2)

    # 5. Valuation Score (15%) - Range: -7.5 to +7.5
    # Valuation score from get_market_valuation is 0-10.
    # Center at 5. (Score - 5) * 1.5 -> Range approx -7.5 to +7.5
    val_data = market_data['valuation']
    raw_val_score = val_data.get('valuation_score', 5)
    val_score_centered = (raw_val_score - 5) * 1.5
    scores['valuation'] = round(val_score_centered, 2)

    # Calculate final index
    final_index = base_score + sum(scores.values())
    final_index = max(0, min(100, round(final_index, 1)))

    # Determine sentiment level and detailed description
    description = get_sentiment_description(final_index)

    if final_index >= 80:
        sentiment_level = "极度贪婪"
        color = "red"
    elif final_index >= 60:
        sentiment_level = "贪婪"
        color = "orange"
    elif final_index >= 40:
        sentiment_level = "中性"
        color = "yellow"
    elif final_index >= 20:
        sentiment_level = "恐惧"
        color = "blue"
    else:
        sentiment_level = "极度恐惧"
        color = "dark_blue"

    # Detect Divergences
    divergences = detect_divergence(market_data, final_index)

    return {
        "index": final_index,
        "sentiment_level": sentiment_level,
        "sentiment_description": description,
        "divergences": divergences,
        "color": color,
        "score_breakdown": scores,
        "raw_data": market_data
    }


def generate_prompt_content(result: Dict[str, Any], market_data: Dict[str, Any], date_str: str = None) -> str:
    """Generate AI Prompt content"""
    idx = result['index']
    level = result['sentiment_level']
    desc = result.get('sentiment_description', '')
    divergences = result.get('divergences', [])

    breadth = result['score_breakdown']['market_breadth']
    indices_trend = result['score_breakdown']['indices_trend']
    news_score = result['score_breakdown']['news_sentiment']
    flow_score = result['score_breakdown']['money_flow']
    val_score = result['score_breakdown']['valuation']

    limit_up = market_data['limit_up_count']
    limit_down = market_data['limit_down_count']

    bullish = market_data['news_sentiment']['bullish_count']
    bearish = market_data['news_sentiment']['bearish_count']

    net_inflow = market_data['sector_flow']['net_inflow'] / 1e8
    inflow_sectors = market_data['sector_flow']['inflow_sectors'][:3]
    outflow_sectors = market_data['sector_flow']['outflow_sectors'][:3]

    pe_sh = market_data['valuation']['pe_sh']
    pe_sz = market_data['valuation']['pe_sz']

    # Volume data
    vol_today = market_data['volume']['today_volume'] / 1e8
    vol_yesterday = market_data['volume']['yesterday_volume'] / 1e8
    vol_change = market_data['volume']['change_pct']

    if vol_today == 0:
        vol_desc = "暂无数据"
        vol_change_desc = "数据缺失"
        vol_trend_desc = "无法判断"
    elif vol_change == 0 and vol_yesterday == 0:
        # Yesterday data unavailable, don't show percentage
        vol_desc = ""
        vol_change_desc = ""
        vol_trend_desc = "成交额正常"
    else:
        vol_desc = f"放量{vol_change:.1f}%" if vol_change > 0 else f"缩量{abs(vol_change):.1f}%"
        vol_change_desc = "红色" if vol_change > 5 else "绿色" if vol_change < -5 else "黄色"
        vol_trend_desc = "成交额显著放大" if vol_change > 10 else "成交额小幅放大" if vol_change > 0 else "缩量震荡" if vol_change > -10 else "成交额大幅萎缩"

    # Conditional strings
    idx_color = "红色粗体" if idx >= 70 else "橙色粗体" if idx >= 55 else "黄色粗体"
    level_color = "橙红色标签" if idx >= 70 else "橙色标签"
    breadth_desc = "涨停家数远超跌停" if limit_up > limit_down * 3 else "涨跌停相对均衡"
    indices_desc = "主流指数全线飘红" if indices_trend > 2 else "指数整体平稳" if indices_trend > -2 else "指数集体调整"
    news_desc = "正面新闻占优" if news_score > 2 else "新闻情绪中性" if news_score > -2 else "负面新闻增多"

    warning_emoji = "⚠️" if flow_score < -5 else ""
    flow_desc = "净流出" if net_inflow < 0 else "净流入"
    flow_color = "红色警告" if net_inflow < -300 else "绿色" if net_inflow > 300 else "中性"

    # Build prompt
    prompt = f"""# 市场情绪指数 - AI绘图Prompt ({datetime.now().strftime("%m月%d日")})
# 数据来源: 恐贪指数模型 (5维度综合评分)

## 图片规格
- 比例: 9:16 竖版
- 风格: 手绘/手账风格，暖色纸张质感
- 背景色: #F5E6C8 纸黄色
- 配色: 贪婪=红色渐变, 恐惧=蓝色渐变

## 标题
**📊 A股恐贪指数 | Market Greed & Fear** (居中，手绘字体)
**{date_str or datetime.now().strftime("%Y-%m-%d")}**

---

## 核心指标 (大号显示)
**恐贪指数: {idx}/100** ({idx_color})
**情绪等级: {level}** ({level_color})
**市场状态: {desc}**

---

## 五维度评分可视化 (雷达图/进度条)

### 1. 市场宽度 (Breadth) {breadth:+.2f}
- 涨停: {limit_up} vs 跌停: {limit_down}
- 说明: {breadth_desc}

### 2. 指数趋势 (Trend) {indices_trend:+.2f}
"""

    for idx_name, change in market_data['indices'].items():
        arrow = "↑" if change > 0 else "↓" if change < 0 else "→"
        prompt += f"- {idx_name}: {change:+.2f}% {arrow}\n"

    prompt += f"- 说明: {indices_desc}\n\n"

    prompt += f"""### 3. 新闻情绪 (News) {news_score:+.2f}
- 利多: {bullish} vs 利空: {bearish}
- 说明: {news_desc}

### 4. 资金流向 (Flow) {flow_score:+.2f} {warning_emoji}
- {flow_desc}: **{abs(net_inflow):.2f} 亿** ({flow_color})
"""
    if inflow_sectors:
        sector_list = "、".join([f"{s['名称']}" for s in inflow_sectors])
        prompt += f"- 流入: {sector_list}\n"

    prompt += f"""
### 5. 市场估值 (Valuation) {val_score:+.2f}
- 上证PE: {pe_sh:.2f} | 深证PE: {pe_sz:.2f}
- 状态: {"估值偏高" if val_score > 3 else "估值偏低" if val_score < -3 else "估值适中"}

---

### 6. 成交额 (Volume)
- 今日: **{vol_today:.0f} 亿**{f' ({vol_desc})' if vol_desc else ''}
- 说明: {vol_trend_desc}
"""

    # Divergence section
    if divergences:
        prompt += "\n## ⚠️ 关键背离信号\n"
        for div in divergences:
            prompt += f"- **{div}**\n"

    prompt += f"""
---

## 情绪解读 (手写体文字框)
> **当前处于"{level}"区间**
> **"{desc}"**
"""

    # Interpretation
    if idx >= 80:
        interpretation = "市场极度亢奋，随时可能面临剧烈波动，切勿盲目追高。"
    elif idx >= 60:
        interpretation = f"市场情绪积极，{vol_desc}，赚钱效应较好。"
    elif idx <= 20:
        interpretation = "市场极度悲观，恐慌盘涌出，或是左侧布局良机。"
    else:
        interpretation = f"市场情绪相对平稳，{vol_desc}，结构性机会为主。"

    prompt += f"> {interpretation}\n"

    prompt += f"""
---

## 投资建议
✅ **操作**: {"观望为主 | 严控仓位" if net_inflow < -300 else "持股待涨 | 逢低吸纳" if idx < 40 else "去弱留强 | 顺势而为"}
⚠️ **风险**: {"资金大幅流出，小心回调" if net_inflow < -300 else "高位股分化风险" if idx > 70 else "底部震荡，耐心等待"}

---

## Footer
"每日恐贪指数 | AI量化情绪模型"

---

## AI绘图Prompt (Midjourney/SD)

(masterpiece, best quality), (vertical:1.2), (aspect ratio: 9:16), (sketch style), (hand drawn), (infographic)

Create a TALL VERTICAL PORTRAIT IMAGE (Aspect Ratio 9:16) HAND-DRAWN SKETCH style stock market sentiment infographic poster.

**Layout Structure**:
1. **Top Section**: A large vintage MAIN GAUGE (Speedometer style) pointing to {idx} ({level}).
2. **Middle Section**: A PROMINENT HEXAGONAL RADAR CHART (六边形雷达图) showing 5 dimensions:
   - Dimension 1 (Market Breadth): Score {breadth:+.1f} - {'Strong' if breadth > 5 else 'Weak' if breadth < -5 else 'Neutral'}
   - Dimension 2 (Index Trend): Score {indices_trend:+.1f} - {'Bullish' if indices_trend > 2 else 'Bearish' if indices_trend < -2 else 'Flat'}
   - Dimension 3 (Money Flow): Score {flow_score:+.1f} - {'Inflow' if flow_score > 0 else 'Outflow'}
   - Dimension 4 (News Sentiment): Score {news_score:+.1f} - {'Positive' if news_score > 2 else 'Negative' if news_score < -2 else 'Neutral'}
   - Dimension 5 (Valuation): Score {val_score:+.1f} - {'Expensive' if val_score > 3 else 'Cheap' if val_score < -3 else 'Fair'}
   - **Chart Style**: Hand-drawn hexagon with 5 axes radiating from center, filled area shows current scores
   - **Color**: Use {'fiery red' if idx >= 80 else 'warm orange' if idx >= 60 else 'calm yellow' if idx >= 40 else 'cool blue' if idx >= 20 else 'deep cold blue'} tones, with filled area showing intensity
3. **Background**: {'fiery red tones, burning background' if idx >= 80 else 'warm orange tones, bright background' if idx >= 60 else 'neutral yellow tones, balanced composition' if idx >= 40 else 'cool blue tones, calm background' if idx >= 20 else 'deep cold blue tones, icy background'}, aged paper texture, ink sketch lines.

**Visual Details**:
- Style: Da Vinci engineering sketch, complex mechanical details, infographic layout.
- **IMPORTANT**: The hexagonal radar chart MUST be the dominant visual element in the middle section.
- Color Palette: {'excitement, frenzy' if idx >= 80 else 'optimistic, positive' if idx >= 60 else 'calm, waiting' if idx >= 40 else 'cautious, worried' if idx >= 20 else 'panic, extreme pessimism'} tones on parchment paper.
- Textures: Crosshatching, ink splatters, rough paper grain.
- No digital text, just visual representations of data.

--ar 9:16 --style raw --v 6
"""
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

    # DISABLED: No longer generate intermediate files
    # The final 市场情绪_Prompt.txt now contains the complete Midjourney/SD prompt with hexagonal radar chart

    # Generate Image using API (Use Raw English Prompt)
    raw_image_prompt = get_raw_image_prompt(result)
    image_output_dir = os.path.join("results", date_s, "images")
    os.makedirs(image_output_dir, exist_ok=True)
    image_output_path = os.path.join(image_output_dir, "market_sentiment_cover.png")

    print("\n🎨 Generating Market Sentiment Cover Image...")
    generate_image_from_text(raw_image_prompt, image_output_path)

    return result


if __name__ == "__main__":
    # Run analysis and save results
    run_analysis()
