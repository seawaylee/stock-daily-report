"""
数据获取模块 - 使用 akshare 获取A股数据
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from tqdm import tqdm
from typing import List, Optional, Callable, Any
import time
import os
import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed
from .tushare_manager import TushareManager

CACHE_DIR = "results/cache"
os.makedirs(CACHE_DIR, exist_ok=True)

def fetch_data_with_cache(
    func: Callable,
    cache_key: str,
    date_str: str = None,
    cache_type: str = 'pickle',
    refresh: bool = False,
    **kwargs
) -> Any:
    """
    General purpose data fetching with caching support.

    Args:
        func: The data fetching function to execute
        cache_key: Unique identifier for the cache file
        date_str: Date string for versioning (default: today)
        cache_type: 'pickle', 'csv', or 'parquet'
        refresh: Force refresh data ignoring cache
        **kwargs: Arguments to pass to func

    Returns:
        The data returned by func (or loaded from cache)
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y%m%d")

    # Create specific cache directory based on type/category if needed
    # For now, put everything in results/cache

    filename = f"{cache_key}_{date_str}.{cache_type}"
    file_path = os.path.join(CACHE_DIR, filename)

    if not refresh and os.path.exists(file_path):
        try:
            # print(f"Loading cached data: {file_path}")
            if cache_type == 'pickle':
                with open(file_path, 'rb') as f:
                    return pickle.load(f)
            elif cache_type == 'csv':
                return pd.read_csv(file_path, dtype={'code': str})
            elif cache_type == 'parquet':
                return pd.read_parquet(file_path)
        except Exception as e:
            print(f"Error loading cache {file_path}: {e}")
            # Fallthrough to fetch

    # Fetch data
    try:
        data = func(**kwargs)

        # Save cache if data is valid
        if data is not None:
            if isinstance(data, pd.DataFrame) and data.empty:
                return data # Don't cache empty dataframe? Or maybe do?

            try:
                if cache_type == 'pickle':
                    with open(file_path, 'wb') as f:
                        pickle.dump(data, f)
                elif cache_type == 'csv' and isinstance(data, pd.DataFrame):
                    data.to_csv(file_path, index=False)
                elif cache_type == 'parquet' and isinstance(data, pd.DataFrame):
                    data.to_parquet(file_path)
            except Exception as e:
                print(f"Error saving cache {file_path}: {e}")

        return data
    except Exception as e:
        print(f"Error fetching data for {cache_key}: {e}")
        return None


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

        except Exception as e:
            print(f"Error loading cache: {e}, re-fetching...")

    # --- Optim: Check persistent cache BEFORE network ---
    persistent_cache = "results/stock_list_cache.csv"
    if os.path.exists(persistent_cache):
        print(f"Loading from persistent cache: {persistent_cache}")
        try:
            result = pd.read_csv(persistent_cache, dtype={'code': str})
            if exclude_st:
                result = result[~result['name'].str.contains('ST', case=False, na=False)]
            if min_market_cap > 0:
                result['market_cap'] = pd.to_numeric(result['market_cap'], errors='coerce').fillna(0)
                result = result[result['market_cap'] >= min_market_cap]
            print(f"✅ Loaded {len(result)} stocks from persistent cache (Skipping Network).")
            return result
        except Exception as e:
            print(f"Persistent cache load failed: {e}")

    # --- Optim: Try Tushare first ---
    ts_manager = TushareManager()
    if ts_manager.is_ready:
        print("尝试使用 Tushare 获取股票列表...")
        ts_df = ts_manager.get_stock_list()
        if ts_df is not None and not ts_df.empty:
            # Apply filters
            if exclude_st:
                ts_df = ts_df[~ts_df['name'].str.contains('ST', case=False, na=False)]
            if min_market_cap > 0:
                ts_df = ts_df[ts_df['market_cap'] >= min_market_cap]

            print(f"✅ Tushare 获取成功: {len(ts_df)} 只股票 (市值>={min_market_cap}亿, 排除ST={exclude_st})")

            # Save to cache
            try:
                ts_df.to_csv(cache_file, index=False)
                ts_df.to_csv(persistent_cache, index=False)
                print(f"Saved stock list cache to {cache_file} and {persistent_cache}")
            except Exception as e:
                print(f"Failed to save cache: {e}")

            return ts_df

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
                time.sleep(1)
                
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
        
        # 检查是否有行业列 (自2024年起，EM接口已不再返回此字段)
        industry_col = '所属行业' if '所属行业' in stock_info.columns else None
        
        # 复制需要的列
        cols_to_copy = ['代码', '名称', '总市值']
        if industry_col:
            cols_to_copy.append(industry_col)
        
        result = stock_info[cols_to_copy].copy()
        
        # 2. 获取行业数据
        if industry_col:
            result.columns = ['code', 'name', 'market_cap', 'industry']
        else:
            result.columns = ['code', 'name', 'market_cap']
            # 初始化空行业列
            result['industry'] = ''
            print("⚠️  '所属行业' 字段缺失，将使用 stock_individual_info_em 批量获取...")
            
            # 批量获取行业数据 (采样方式以提高速度)
            result = _fetch_industries_for_stocks(result)
        
        # 转换市值为亿
        result['market_cap'] = pd.to_numeric(result['market_cap'], errors='coerce') / 100000000
        
        # 排除ST股票
        if exclude_st:
            result = result[~result['name'].str.contains('ST', case=False, na=False)]
        
        # 市值筛选
        if min_market_cap > 0:
            result = result[result['market_cap'] >= min_market_cap]
        
        print(f"筛选后: {len(result)} 只股票 (市值>={min_market_cap}亿, 排除ST={exclude_st})")
        
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


def _fetch_industries_for_stocks(df: pd.DataFrame, sample_size: int = 200) -> pd.DataFrame:
    """
    批量获取股票行业信息
    由于逐个查询速度较慢，这里采用采样策略：
    1. 优先获取大市值股票的行业（更可能被选中）
    2. 对小市值股票进行采样
    
    Args:
        df: 包含 code, name, market_cap 列的 DataFrame
        sample_size: 采样数量，默认200只
    
    Returns:
        添加了 industry 列的 DataFrame
    """
    import time
    
    # 按市值排序，优先获取大市值股票
    df_sorted = df.sort_values('market_cap', ascending=False).reset_index(drop=True)
    
    # 采样策略：前200只 + 随机采样200只
    priority_count = min(sample_size, len(df_sorted))
    priority_stocks = df_sorted.head(priority_count)
    
    print(f"正在获取 {len(priority_stocks)} 只重点股票的行业信息...")
    
    industry_map = {}
    success_count = 0
    fail_count = 0
    
    for idx, row in tqdm(priority_stocks.iterrows(), total=len(priority_stocks), desc="获取行业"):
        code = row['code']
        try:
            info = ak.stock_individual_info_em(symbol=code)
            industry_row = info[info['item'] == '行业']
            if not industry_row.empty:
                industry = industry_row.iloc[0]['value']
                industry_map[code] = industry
                success_count += 1
            time.sleep(0.05)  # 避免请求过快
        except Exception as e:
            fail_count += 1
            if fail_count <= 3:  # 只打印前3个错误
                print(f"  获取 {code} 行业失败: {e}")
            continue
    
    print(f"✅ 成功获取 {success_count} 只股票的行业信息，失败 {fail_count} 只")
    
    # 将获取到的行业信息填充回原DataFrame
    df['industry'] = df['code'].map(industry_map).fillna('')
    
    return df

def fetch_specific_industries(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fetch industry for specific stocks in the dataframe if missing.
    Uses ThreadPoolExecutor for parallel fetching.
    """
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    missing_mask = (df['industry'] == '') | (df['industry'].isnull()) | (df['industry'] == '其他')
    target_df = df[missing_mask]
    
    if target_df.empty:
        return df
        
    print(f"Refining Industry info for {len(target_df)} stocks (Parallel)...")
    
    industry_map = {}
    
    def fetch_one(code):
        try:
            info = ak.stock_individual_info_em(symbol=code)
            industry_row = info[info['item'] == '行业']
            if not industry_row.empty:
                return code, industry_row.iloc[0]['value']
        except Exception:
            pass
        return code, None

    max_workers = 8
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(fetch_one, row['code']) for _, row in target_df.iterrows()]
        
        for future in tqdm(as_completed(futures), total=len(target_df), desc="补全行业(并行)"):
            code, ind = future.result()
            if ind:
                industry_map[code] = ind
            
    # Update
    for code, ind in industry_map.items():
        df.loc[df['code'] == code, 'industry'] = ind
        
    # --- Optim: Persist updates back to global cache ---
    try:
        import os
        cache_path = "results/stock_list_cache.csv"
        if os.path.exists(cache_path) and industry_map:
            print(f"Persisting {len(industry_map)} new industries to {cache_path}...")
            # Load as string to preserve 'code' (e.g. 000001)
            full_df = pd.read_csv(cache_path, dtype={'code': str})
            
            updated_count = 0
            for code, ind in industry_map.items():
                if ind:
                    # Update if exists in full_df
                    mask = full_df['code'] == code
                    if mask.any():
                        full_df.loc[mask, 'industry'] = ind
                        updated_count += 1
            
            if updated_count > 0:
                full_df.to_csv(cache_path, index=False)
                print(f"Saved {updated_count} industry updates to persistent cache.")
    except Exception as e:
        print(f"Failed to persist industry updates: {e}")
        
    return df








def _add_market_prefix(code: str) -> str:
    """Add sh/sz prefix for Sina API"""
    if code.startswith('6'):
        return f"sh{code}"
    elif code.startswith('0') or code.startswith('3'):
        return f"sz{code}"
    elif code.startswith('8') or code.startswith('4'):
        return f"bj{code}"
    return code

def get_stock_data(code: str, days: int = 300) -> Optional[pd.DataFrame]:
    """
    获取单只股票的日线数据 (Prioritize Tushare -> Sina -> Fallback to EastMoney)
    """
    # 0. Try Tushare (Primary if configured)
    ts_manager = TushareManager()
    if ts_manager.is_ready:
        try:
            df = ts_manager.get_daily_data(code, days)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            print(f"Tushare fetching failed for {code}: {e}")

    # 1. Try Sina (Primary now due to EM blocking)
    try:
        sina_code = _add_market_prefix(code)
        df = ak.stock_zh_a_daily(symbol=sina_code, adjust="qfq")
        
        if df is not None and not df.empty:
            # Standardize columns
            if 'date' not in df.columns:
                df = df.reset_index()
            
            required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
            if all(col in df.columns for col in required_cols):
                df = df[required_cols].copy()
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date').reset_index(drop=True)
                if len(df) > days:
                    df = df.tail(days).reset_index(drop=True)
                return df
    except Exception as e:
        pass 

    # 2. Fallback to EastMoney
    try:
        df = None
        for i in range(1): # Try only once
            try:
                df = ak.stock_zh_a_hist(
                    symbol=code,
                    period="daily",
                    start_date=(datetime.now() - timedelta(days=days*2)).strftime('%Y%m%d'),
                    end_date=datetime.now().strftime('%Y%m%d'),
                    adjust="qfq"
                )
                if df is not None and not df.empty:
                    break
            except:
                time.sleep(0.5)
        
        if df is not None and not df.empty:
             df = df.rename(columns={'日期': 'date', '开盘': 'open', '最高': 'high', '最低': 'low', '收盘': 'close', '成交量': 'volume'})
             df = df[['date', 'open', 'high', 'low', 'close', 'volume']].copy()
             df['date'] = pd.to_datetime(df['date'])
             df = df.sort_values('date').reset_index(drop=True)
             if len(df) > days:
                 df = df.tail(days).reset_index(drop=True)
             return df
    except Exception:
        pass
        
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
