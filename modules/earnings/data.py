
"""
Data Fetching Logic for Earnings Module
"""
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import time
import os

def get_current_report_period(date_str=None):
    """
    Determine the most likely reporting period.
    """
    if not date_str:
        dt = datetime.now()
    else:
        dt = datetime.strptime(date_str, "%Y%m%d")
    
    year = dt.year
    month = dt.month
    
    if 1 <= month <= 4:
        return f"{year-1}1231"
    elif 4 < month <= 5:
        return f"{year}0331"
    elif 6 <= month <= 8:
        return f"{year}0630"
    elif 9 <= month <= 10:
        return f"{year}0930"
    else:
        return f"{year}0930"

def fetch_disclosure_schedule(start_date, end_date):
    """
    Fetch disclosure schedule (Formal Reports).
    """
    period = get_current_report_period(start_date)
    print(f"Fetching Disclosure Schedule for Period: {period}...")
    
    try:
        df = ak.stock_yysj_em(symbol="A股", date=period)
        
        # Normalize date columns
        date_cols = ['首次预约时间', '一次变更日期', '二次变更日期', '三次变更日期', '实际披露时间']
        for col in date_cols:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors='coerce')
        
        df['disclosure_date'] = df['实际披露时间'].fillna(df['首次预约时间'])
        
        s_date = pd.to_datetime(start_date, format='%Y%m%d')
        e_date = pd.to_datetime(end_date, format='%Y%m%d')
        
        mask = (df['disclosure_date'] >= s_date) & (df['disclosure_date'] <= e_date)
        filtered_df = df[mask].copy()
        
        print(f"Found {len(filtered_df)} stocks formally disclosing between {start_date}-{end_date}")
        return filtered_df
        
    except Exception as e:
        print(f"Error fetching schedule: {e}")
        return pd.DataFrame()

def fetch_earnings_forecast_by_date(start_date, end_date):
    """
    Fetch earnings forecasts announced within a date range.
    """
    period = get_current_report_period(start_date)
    print(f"Fetching Earnings Forecasts (Released in {start_date}-{end_date})...")
    
    try:
        # Get ALL forecasts for the period
        df = ak.stock_yjyg_em(date=period)
        
        if df.empty:
            return pd.DataFrame()
            
        # Filter by Announcement Date (公告日期)
        if '公告日期' in df.columns:
            df['公告日期'] = pd.to_datetime(df['公告日期'], errors='coerce')
            
            s_date = pd.to_datetime(start_date, format='%Y%m%d')
            e_date = pd.to_datetime(end_date, format='%Y%m%d')
            
            # Handle potential NaT in 公告日期
            mask = (df['公告日期'] >= s_date) & (df['公告日期'] <= e_date)
            filtered = df[mask].copy()
            
            print(f"Found {len(filtered)} forecasts announced in target range.")
            
            # Map columns to match what `schedule_df` might have, effectively treating '公告日期' as the event date
            filtered['disclosure_date'] = filtered['公告日期']
            return filtered
        else:
            print("Warning: '公告日期' column missing in forecast data.")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"Error fetching forecast by date: {e}")
        return pd.DataFrame()

def fetch_earnings_forecast(period=None, use_cache=True):
    """
    (Legacy) Fetch all forecasts for a period.
    Added caching mechanism.
    """
    if not period:
        period = get_current_report_period()
        
    # Cache setup
    cache_dir = "results/cache/earnings"
    os.makedirs(cache_dir, exist_ok=True)
    today_str = datetime.now().strftime('%Y%m%d')
    cache_file = f"{cache_dir}/forecast_{period}_{today_str}.csv"
    
    if use_cache and os.path.exists(cache_file):
        print(f"Loading earnings forecast from cache: {cache_file}")
        try:
            return pd.read_csv(cache_file, dtype={'股票代码': str, 'code': str})
        except Exception as e:
            print(f"Cache load failed: {e}")

    try:
        print(f"Fetching Earnings Forecast for {period} from network...")
        df = ak.stock_yjyg_em(date=period)
        
        # Save cache
        if df is not None and not df.empty:
            df.to_csv(cache_file, index=False)
            print(f"Saved forecast cache to: {cache_file}")
            
        return df
    except Exception as e:
        print(f"Fetch failed: {e}")
        return pd.DataFrame()

def merge_data(schedule_df, forecast_df):
    """
    Merge logic. 
    Here we might have TWO types of inputs:
    1. Schedule DF (Formal)
    2. Forecast DF (Announcements)
    
    We want to output a consolidated list.
    """
    # If inputs are mixed types (schedule vs forecast filtered), Normalize them
    
    # 1. Normalize Schedule DF
    # Needs: 股票代码, 股票简称, disclosure_date, type='formal'
    
    # 2. Normalize Forecast DF
    # Needs: 股票代码, 股票简称, disclosure_date, type='forecast'
    
    pass 
    # Logic moved to __init__.py mostly, or specialized here.
    # But sticking to original plan: Join Forecast info ONTO Schedule.
    
    # Re-implement standard left join
    schedule_df['股票代码'] = schedule_df['股票代码'].astype(str)
    forecast_df['股票代码'] = forecast_df['股票代码'].astype(str)
    
    merged = pd.merge(
        schedule_df, 
        forecast_df[['股票代码', '业绩变动', '预测数值', '业绩变动幅度', '业绩变动原因', '预告类型', '上年同期值', '预测指标']], 
        on='股票代码', 
        how='left'
    )
    return merged
