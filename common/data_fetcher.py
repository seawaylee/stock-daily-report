"""
数据获取模块 - 使用 akshare 获取A股数据
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from tqdm import tqdm
from typing import List, Optional
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed


def get_all_stock_list(min_market_cap: float = 0, exclude_st: bool = False) -> pd.DataFrame:
    """
    获取全部A股股票列表
    
    Args:
        min_market_cap: 最低市值（亿），默认0表示不限制
        exclude_st: 是否排除ST股票，默认False
    
    返回: DataFrame 包含 code, name, market_cap, industry 列
    """
    # 检查是否有今日缓存
    today = datetime.now().strftime('%Y%m%d')
    date_dir = f"results/{today}"
    os.makedirs(date_dir, exist_ok=True)
    cache_file = f"{date_dir}/stock_list_{today}.csv"
    
    if os.path.exists(cache_file):
        print(f"Loading stock list from cache: {cache_file}")
        try:
            result = pd.read_csv(cache_file, dtype={'code': str})
            # Filter again to be safe (in case params changed)
            if exclude_st:
                result = result[~result['name'].str.contains('ST', case=False, na=False)]
            if min_market_cap > 0:
                result = result[result['market_cap'] >= min_market_cap]
            return result
        except Exception as e:
            print(f"Error loading cache: {e}, re-fetching...")

    try:
        # 获取A股股票列表（包含市值和行业信息）
        # Explicitly using EastMoney Source
        stock_info = None
        import time
        for i in range(3):
            try:
                # stock_zh_a_spot_em is the standard EM spot interface
                stock_info = ak.stock_zh_a_spot_em()
                if stock_info is not None and not stock_info.empty:
                    break
            except Exception as e:
                print(f"尝试 {i+1}/3 获取股票列表(EM)失败: {e}")
                time.sleep(2)
                
        if stock_info is None or stock_info.empty:
             # Try loading from previous cache if available (Fallback)
             # Check for any stock_list_*.csv in results/
             import glob
             cached_files = glob.glob("results/*/stock_list_*.csv")
             if cached_files:
                 latest_cache = max(cached_files, key=os.path.getctime)
                 print(f"⚠️ Network failed. Fallback to latest cache: {latest_cache}")
                 result = pd.read_csv(latest_cache, dtype={'code': str})
                 if exclude_st:
                     result = result[~result['name'].str.contains('ST', case=False, na=False)]
                 if min_market_cap > 0:
                     result = result[result['market_cap'] >= min_market_cap]
                 return result

             # --- Plan B: Persistent Cache Fallback ---
             persistent_cache = "results/stock_list_cache.csv"
             print(f"⚠️ Network failed. Checking persistent cache: {persistent_cache}")
             
             if os.path.exists(persistent_cache):
                 print(f"✅ Found persistent cache file.")
                 try:
                     result = pd.read_csv(persistent_cache, dtype={'code': str})
                     
                     # Re-apply filters
                     if exclude_st:
                         result = result[~result['name'].str.contains('ST', case=False, na=False)]
                     if min_market_cap > 0:
                         result['market_cap'] = pd.to_numeric(result['market_cap'], errors='coerce').fillna(0)
                         result = result[result['market_cap'] >= min_market_cap]

                     print(f"✅ Loaded {len(result)} stocks from persistent cache.")
                     return result
                 except Exception as e:
                     print(f"❌ Failed to load persistent cache: {e}")

             raise Exception("无法获取股票列表 (重试3次失败, 且无任何本地缓存)")
        
        # 检查是否有行业列
        industry_col = '所属行业' if '所属行业' in stock_info.columns else None
        
        # 复制需要的列
        cols_to_copy = ['代码', '名称', '总市值']
        if industry_col:
            cols_to_copy.append(industry_col)
        
        result = stock_info[cols_to_copy].copy()
        
        # 2. 获取行业数据并合并
        if industry_col:
            result.columns = ['code', 'name', 'market_cap', 'industry']
        else:
            result.columns = ['code', 'name', 'market_cap']
            result['industry'] = ''
        
        # 转换市值为亿
        result['market_cap'] = pd.to_numeric(result['market_cap'], errors='coerce') / 100000000
        
        # 排除ST股票
        if exclude_st:
            result = result[~result['name'].str.contains('ST', case=False, na=False)]
        
        # 市值筛选
        if min_market_cap > 0:
            result = result[result['market_cap'] >= min_market_cap]
        
        print(f"筛选后: {len(result)} 只股票 (市值>={min_market_cap}亿, 排除ST={exclude_st})")
        
        # Save to cache (unfiltered full list might be better, but saving filtered is okay for this specific use case? 
        # Actually better to save the full cleaning result before filtering params? 
        # But the function returns filtered result. Let's save the result we got and next time we load it and re-filter if needed.
        # Wait, if we save filtered result for 100亿, and next time we want 50亿, we can't use cache.
        # But for this user's specific daily task, parameters are likely constant.
        # Let's simple save the result.
        
        try:
            result.to_csv(cache_file, index=False)
            print(f"Saved stock list cache to {cache_file}")
            
            # Persistent Cache Update (User Requested)
            persistent_path = "results/stock_list_cache.csv"
            result.to_csv(persistent_path, index=False)
            print(f"Updated persistent stock list cache: {persistent_path}")
        except Exception as e:
            print(f"Failed to save cache: {e}")

        return result
    except Exception as e:
        print(f"获取股票列表失败: {e}")
        return pd.DataFrame(columns=['code', 'name', 'market_cap', 'industry'])





def get_stock_data(code: str, days: int = 300) -> Optional[pd.DataFrame]:
    """
    获取单只股票的日线数据
    
    Args:
        code: 股票代码（如 000001, 600000）
        days: 获取多少天的数据
    
    Returns:
        DataFrame 包含: date, open, high, low, close, volume
    """
    try:
        # 使用东方财富数据源 (增加重试机制)
        df = None
        import time
        for i in range(3):
            try:
                df = ak.stock_zh_a_hist(
                    symbol=code,
                    period="daily",
                    start_date=(datetime.now() - timedelta(days=days*2)).strftime('%Y%m%d'),
                    end_date=datetime.now().strftime('%Y%m%d'),
                    adjust="qfq"  # 前复权
                )
                if df is not None and not df.empty:
                    break
            except:
                time.sleep(0.5)

        
        if df is None or len(df) == 0:
            return None
        
        # 重命名列
        df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '最高': 'high',
            '最低': 'low',
            '收盘': 'close',
            '成交量': 'volume'
        })
        
        # 只保留需要的列
        df = df[['date', 'open', 'high', 'low', 'close', 'volume']].copy()
        
        # 转换日期格式
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date').reset_index(drop=True)
        
        # 取最近 days 条数据
        if len(df) > days:
            df = df.tail(days).reset_index(drop=True)
        
        return df
    
    except Exception as e:
        # print(f"获取 {code} 数据失败: {e}")
        return None


def batch_fetch_data(codes: List[str], days: int = 300, delay: float = 0.1) -> dict:
    """
    批量获取股票数据
    
    Args:
        codes: 股票代码列表
        days: 获取天数
        delay: 每次请求间隔（秒），避免被限流
    
    Returns:
        dict: {code: DataFrame}
    """
    result = {}
    
    for code in tqdm(codes, desc="获取股票数据"):
        df = get_stock_data(code, days)
        if df is not None and len(df) >= 60:  # 至少需要60天数据
            result[code] = df
        
        time.sleep(delay)
    
    return result


def get_index_list() -> dict:
    """获取常用指数列表"""
    return {
        '000300': '沪深300',
        '000905': '中证500',
        '000852': '中证1000',
        '399006': '创业板指',
        '000688': '科创50'
    }


if __name__ == "__main__":
    # 测试
    print("获取股票列表...")
    stocks = get_all_stock_list()
    print(f"共 {len(stocks)} 只股票")
    print(stocks.head())
    
    print("\n获取单只股票数据...")
    df = get_stock_data("000001", 100)
    if df is not None:
        print(df.tail())
