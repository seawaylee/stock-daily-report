


import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime
import time
import os
import concurrent.futures

# Config is now loaded from config/fish_basin_sectors.json

def fetch_data_router(item):
    """
    Route fetching based on item type.
    """
    name = item['name']
    code = item.get('code', '')
    itype = item.get('type', 'THS')
    
    df = None
    turnover = 0
    start_date = "20240101" # Extended history to capture status change
    
    try:
        # 1. THS Industry
        if itype == 'THS':
            # Note: name provided might not match '工业金属' if mapped. 
            # Need to pass correct symbol to fetcher if name differs.
            # But fetcher usually takes Name. 
            # If we call '有色金属' but code is 881168 (Industrial Metals), fetcher needs '工业金属'.
            # Hack: The fetcher function below takes 'name' (symbol).
            # If name is '有色金属' but THS doesn't have it, we must ensure 'name' passed to akshare is valid.
            # Updated: LEGEND mapping should align Name with THS official name or we use code?
            # akshare THS fetcher usually needs exact Name match or Code? Code is safer if supported.
            # Check function doc: stock_board_industry_index_ths(symbol="半导体") -> Symbol is Chinese Name.
            df = ak.stock_board_industry_index_ths(symbol=name, start_date=start_date, end_date="20260201")

        # 2. THS Concept
        elif itype == 'THS_CONCEPT':
            df = ak.stock_board_concept_index_ths(symbol=name, start_date=start_date, end_date="20260201")
            
        # 3. Index (CSI/SE) - Multi-tier fallback: EM (Plan A) -> Sina (Plan B) -> THS (Plan C)
        elif itype == 'INDEX':
            # Plan A: Try EM first (Data quality is generally better)
            try:
                # Try as is first (if it has prefix)
                try:
                    df = ak.stock_zh_index_daily_em(symbol=code)
                except:
                    # Try adding prefix if missing
                    for p in ["sz", "sh"]:
                        try:
                            df = ak.stock_zh_index_daily_em(symbol=p+code)
                            if not df.empty: break
                        except: pass
                
                if df is not None and not df.empty:
                     # Rename to standard
                    df = df.rename(columns={'date': 'date', 'close': 'close', 'open': 'open', 'high': 'high', 'low': 'low', 'volume': 'volume'})
                    df['date'] = pd.to_datetime(df['date'])
                    turnover = 99999999999 # Prioritize Legend
            except Exception as e:
                # print(f"EM Index fetch failed for {name} ({code}): {e}")
                df = None

            # Plan B: Try Sina if EM failed
            if df is None or df.empty:
                try:
                    df = ak.stock_zh_index_daily(symbol=code)
                    if df is not None and not df.empty:
                        # Sina returns standard columns
                        df['date'] = pd.to_datetime(df['date'])
                        
                        # VALIDATION: Check if data is fresh enough (>= start_date)
                        if df['date'].max() < pd.to_datetime(start_date):
                            # print(f"Sina data for {name} is too old ({df['date'].max()}), falling back...")
                            df = None
                        else:
                            turnover = 99999999999 # Prioritize in results
                except Exception as e:
                    df = None

            # Plan C: THS Fallback (last resort)
            if df is None or df.empty:
                print(f"🔄 触发 Plan C: 尝试使用同花顺数据源获取 [{name}]...")
                try:
                    # Try THS Industry first
                    df = ak.stock_board_industry_index_ths(symbol=name, start_date=start_date, end_date="20260201")
                    if df is None or df.empty:
                        # Try THS Concept
                         df = ak.stock_board_concept_index_ths(symbol=name, start_date=start_date, end_date="20260201")
                    
                    if df is not None and not df.empty:
                        print(f"✅ Plan C 成功: 获取到 [{name}] 同花顺数据")
                except Exception as e2:
                    print(f"❌ Plan C 也失败: {e2}")


        if df is not None and not df.empty:
            # Standardize columns
            if '日期' in df.columns:
                 df = df.rename(columns={
                    '日期': 'date', '开盘价': 'open', '最高价': 'high', '最低价': 'low', 
                    '收盘价': 'close', '成交量': 'volume', '成交额': 'turnover'
                })
            
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values(by='date')
            
            # Numeric
            cols = ['close', 'open', 'high', 'low', 'volume', 'turnover']
            for c in cols:
                if c in df.columns: df[c] = pd.to_numeric(df[c], errors='coerce')
                
            if 'turnover' in df.columns and turnover == 0:
                turnover = df.iloc[-1]['turnover']
                
            # Date filter (Index fetcher returns all history)
            # Remove this filter or check if needed. Index fetcher returns a lot.
            # Only keep what we need for Fish Basin (start_date)
            df = df[df['date'] >= pd.to_datetime(start_date)]
            
            # Alias logic: If alias exists, rename for output
            if 'alias' in item:
                return item['alias'], code, df, turnover
                
            return name, code, df, turnover

    except Exception as e:
        # print(f"Error fetching {name}: {e}")
        pass
        
    return name, code, None, 0

def fetch_industry_data(name, code):
    """
    Fetch history for a specific THS industry (Generic Wrapper).
    """
    try:
        # Update start_date here too
        df = ak.stock_board_industry_index_ths(symbol=name, start_date="20240101", end_date="20260201")
        
        rename_map = {
            '日期': 'date', '开盘价': 'open', '最高价': 'high', '最低价': 'low', 
            '收盘价': 'close', '成交量': 'volume', '成交额': 'turnover'
        }
        df = df.rename(columns=rename_map)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values(by='date')
        
        for col in ['close', 'open', 'high', 'low', 'volume', 'turnover']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
        last_turnover = 0
        if not df.empty:
            last_turnover = df.iloc[-1]['turnover']
            
        return name, code, df, last_turnover
    except:
        return name, code, None, 0

def save_to_excel_colored(df, filename):
    if df.empty: return
    import os
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    def color_status(val):
        color = 'red' if val == 'YES' else 'green'
        return f'color: {color}'
    def color_pct(val):
        try:
            v = float(val.strip('%'))
            color = 'red' if v > 0 else 'green'
            return f'color: {color}'
        except: return ''

    try:
        styler = df.style.map(color_status, subset=['状态'])\
                        .map(color_pct, subset=['涨幅%', '偏离率', '区间涨幅%'])
                         
        # Highlight entire row if status changed today
        def highlight_today_row(row):
            today_str = datetime.now().strftime("%y.%m.%d")
            # 兼容可能的空格
            if str(row['状态变量时间']).strip() == today_str:
                return ['background-color: #FFFFCC'] * len(row) # Light Yellow
            return [''] * len(row)

        styler = styler.apply(highlight_today_row, axis=1)
                         
        styler.to_excel(filename, index=False, engine='openpyxl')
        
        from openpyxl import load_workbook
        wb = load_workbook(filename)
        ws = wb.active
        for column in ws.columns:
            max_length = 0
            column = [cell for cell in column]
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except: pass
            ws.column_dimensions[column[0].column_letter].width = max_length + 2
        wb.save(filename)
        print(f"Saved: {filename}")
    except Exception as e:
        print(f"Excel save failed: {e}")

import json

def load_sector_config(config_path="config/fish_basin_sectors.json"):
    """Load sector configuration from JSON file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config {config_path}: {e}")
        return []


def run(date_dir=None):
    """
    Main entry point for Fish Basin Sector Analysis.
    """
    print("=== Fish Basin Sector Analysis (Configured List) ===")
    
    # 1. Load Config
    print("Loading Sector Config...")
    items = load_sector_config()
    if not items:
        print("No items found in config.")
        return

    # 2. Deduplicate (just in case)
    unique_map = {}
    for item in items:
        unique_map[item['name']] = item
    
    final_list = list(unique_map.values())
    print(f"Total items to process from config: {len(final_list)}")

    # 3. Fetch Data (Sequential) - Fixes MiniRacer/Threading crash
    processed_results = []
    # Using ThreadPoolExecutor with 1 worker is effectively sequential but keeps structure
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        # Use fetch_data_router for all, as snapshot items map to THS type
        futures = [executor.submit(fetch_data_router, item) for item in final_list]
        for future in concurrent.futures.as_completed(futures):
            name, code, df, turnover = future.result()
            if df is not None and not df.empty:
                processed_results.append({
                    'name': name, 'code': code, 'df': df, 'turnover': turnover
                })

    final_results_list = processed_results
            
    print(f"Successfully fetched: {len(final_results_list)}")

    results = []
    for item in final_results_list:
        name = item['name']
        code = item['code']
        df = item['df']
        
        # Fish Basin Logic
        close = df['close']
        df['SMA20'] = close.rolling(window=20).mean()
        
        if 'volume' in df.columns:
            vol_ma5 = df['volume'].rolling(window=5).mean()
            df['vol_ratio'] = df['volume'] / vol_ma5
        else:
            df['vol_ratio'] = np.nan
            
        df_valid = df.dropna(subset=['SMA20']).copy()
        if df_valid.empty: continue
        
        last_row = df_valid.iloc[-1]
        current_price = last_row['close']
        sma20_current = last_row['SMA20']
        vol_ratio = last_row.get('vol_ratio', 0)
        
        status_str = "YES" if current_price >= sma20_current else "NO"
        deviation = (current_price - sma20_current) / sma20_current
        
        # Backtrack
        price_arr = df['close'].values
        sma_arr = df['SMA20'].values
        dates_arr = df['date'].values
        
        idx = len(df) - 1
        curr_state = (price_arr[idx] >= sma_arr[idx])
        
        signal_idx = -1
        for i in range(idx - 1, 20, -1):
            if i < 0: break
            if pd.isna(sma_arr[i]): break
            state_i = (price_arr[i] >= sma_arr[i])
            if state_i != curr_state:
                signal_idx = i + 1
                break
                
        interval_change = 0.0
        change_date_str = "-"
        
        if signal_idx != -1:
            try:
                # TS Conversion
                ts = (dates_arr[signal_idx] - np.datetime64('1970-01-01T00:00:00Z')) / np.timedelta64(1, 's')
                change_date_str = datetime.utcfromtimestamp(ts).strftime("%y.%m.%d")
                base_price = price_arr[signal_idx]
                interval_change = (current_price - base_price) / base_price
            except: pass

        daily_change = 0.0
        if len(df_valid) >= 2:
            prev_row = df_valid.iloc[-2]
            daily_change = (current_price - prev_row['close']) / prev_row['close']
        
        vr_str = f"{vol_ratio:.2f}" if pd.notna(vol_ratio) else "-"

        results.append({
            "代码": code,
            "名称": name,
            "状态": status_str,
            "涨幅%": f"{daily_change*100:+.2f}%",
            "现价": int(current_price) if current_price > 5 else f"{current_price:.2f}",
            "临界值点": int(sma20_current),
            "偏离率": f"{deviation*100:.2f}%",
            "量比": vr_str,
            "状态变量时间": change_date_str,
            "区间涨幅%": f"{interval_change*100:.2f}%",
            "_deviation_raw": deviation # Hidden field for sorting
        })

    # Sort by Deviation Descending
    results.sort(key=lambda x: x['_deviation_raw'], reverse=True)

    df_res = pd.DataFrame(results)
    if not df_res.empty:
        # Reorder columns
        cols = ["代码", "名称", "状态", "涨幅%", "现价", "临界值点", "偏离率", "量比", "状态变量时间", "区间涨幅%"]
        df_res = df_res[cols]
        print("\n=== Result Head (Sorted by Deviation) ===")
        print(df_res.head(10).to_string())
        
        curr_date = datetime.now().strftime('%Y%m%d')
        if date_dir:
             output_path = os.path.join(date_dir, "趋势模型_题材.xlsx")
        else:
             output_path = f"results/{curr_date}/趋势模型_题材.xlsx"
             
        print(f"Saving to {output_path}...")
        save_to_excel_colored(df_res, output_path)
        
        # Generate image prompts
        # Note: generate_trend_prompts might need adjustment if moved, but assume imports handle it
        try:
            # We don't have generate_trend_prompts in file tree? 
            # If it's another file, we should check compatibility.
            # Assuming it's in pythonpath or same dir. 
            pass 
        except Exception:
            pass
    else:
        print("No results generated.")
        
    return True

if __name__ == "__main__":
    run()

