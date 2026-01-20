import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime
import time

# Symbol Mapping
# Format: "Name": "Code"
# Updated based on user feedback (Jan 20)
SYMBOLS = {
    # --- A-Shares ---
    "上证指数": "sh000001",
    "深证成指": "sz399001",
    "创业板指": "sz399006",
    "科创50": "sh000688",
    "北证50": "bj899050",
    "沪深300": "sh000300",
    "中证500": "sz399905",
    "中证1000": "sz399852", 
    "中证A500": "sh000510", # Updated from sz399935 to Sina source
    "国证2000": "sz399303", # Proxy for CSI 2000 (932000 not available)
    "国证微盘": "sz399852", # Proxy for Micro Cap

    # --- HK ---
    "恒生指数": "hkHSI",
    "恒生科技": "hkHSTECH",
    
    # --- US ---
    "纳斯达克": "us.IXIC",
    "标普500": "us.INX",

    # --- Commodities (COMEX Futures) ---
    "COMEX黄金": "GC", 
    "COMEX白银": "SI",
}

def fetch_data(name, code):
    """
    Fetch data for a given symbol.
    Handles Commodities, US/HK Indices, and A-Share Indices.
    """
    try:
        df = None
        
        # 1. Commodities (COMEX Futures)
        if code in ["GC", "SI"]:
            df = ak.futures_foreign_hist(symbol=code) 
            if df is not None:
                df = df.rename(columns={'date': 'date', 'close': 'close', 'open': 'open', 'high': 'high', 'low': 'low'})
                # Filter recent
                df['date'] = pd.to_datetime(df['date'])
                df = df[df['date'] >= '2024-01-01']
                return df

        # 2. HK Indices
        if code.startswith("hk"):
             # Use hk_index_daily_sina? or similar
             # Current akshare might use stock_hk_index_daily_sina(symbol=code[2:])
             try:
                 df = ak.stock_hk_index_daily_sina(symbol=code[2:])
             except: pass

        # 3. US Indices
        elif code.startswith("us."):
             try:
                df = ak.stock_us_index_daily_sina(symbol=code)
             except: pass
        
        # 4. THS Concepts (Micro Cap)
        elif code.startswith("ths_"):
             try:
                 symbol = code.split("_")[1]
                 df = ak.stock_board_concept_index_ths(symbol=symbol, start_date="20240101")
                 if df is not None:
                     df = df.rename(columns={
                        '日期': 'date', '开盘价': 'open', '最高价': 'high', '最低价': 'low', 
                        '收盘价': 'close', '成交量': 'volume', '成交额': 'turnover'
                     })
             except: pass

        # 5. Specialized A-Share Index (CSI A500)
        elif code == "932000":
             try:
                 # Try index_zh_a_hist (Newer interface for A-Share Indices)
                 df = ak.index_zh_a_hist(symbol="932000", period="daily", start_date="20240101", end_date="20260201")
                 if df is not None:
                     df = df.rename(columns={
                        '日期': 'date', '开盘': 'open', '最高': 'high', '最低': 'low', 
                        '收盘': 'close', '成交量': 'volume'
                     })
             except:
                 # Fallback to EM with prefix
                 try:
                     df = ak.stock_zh_index_daily_em(symbol="sh932000")
                 except: pass

        # 6. Generic A-Share Indices (Default)
        else:
             # Try Sina Daily first
             try:
                df = ak.stock_zh_index_daily(symbol=code)
             except:
                # Fallback to EM Daily
                try:
                    df = ak.stock_zh_index_daily_em(symbol=code)
                except: pass

        if df is not None and not df.empty:
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values(by='date')
            
            # Ensure columns
            if 'close' not in df.columns and '收盘价' in df.columns:
                 df = df.rename(columns={'收盘价': 'close', '日期': 'date', '成交量': 'volume'})
            elif 'close' not in df.columns and '收盘' in df.columns:
                 df = df.rename(columns={'收盘': 'close', '日期': 'date', '成交量': 'volume'})

            # Numeric conversion
            df['close'] = pd.to_numeric(df['close'], errors='coerce')
            if 'volume' in df.columns:
                df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
                
            return df

    except Exception as e:
        print(f"Error fetching {name} ({code}): {e}")
        return None
    return None

def get_fish_basin_analysis(symbols_map):
    results = []
    print(f"Starting Fish Basin Analysis for {len(symbols_map)} symbols...")
    
    print(f"Starting Fish Basin Analysis for {len(symbols_map)} symbols...")
    
    for name, code in symbols_map.items():
        try:
            print(f"Processing {name} ({code})...")
            
            # 1. Fetch
            df = fetch_data(name, code)
            
            if df is None or df.empty:
                print(f"No data for {name}")
                continue
                
            close = df['close']
            
            # 2. Indicators
            # SMA20
            df['SMA20'] = close.rolling(window=20).mean()
            
            # Volume Ratio (Vol / MA5_Vol)
            if 'volume' in df.columns:
                vol_ma5 = df['volume'].rolling(window=5).mean()
                df['vol_ratio'] = df['volume'] / vol_ma5
            else:
                df['vol_ratio'] = np.nan

            df_valid = df.dropna(subset=['SMA20']).copy()
            if df_valid.empty: continue
            
            last_row = df_valid.iloc[-1]
            current_date = last_row['date']
            
            # If data is too old (e.g. > 5 days), warn?
            # day_diff = (datetime.now() - current_date).days
            # if day_diff > 5: print(f"Warning: Data for {name} is old ({current_date.date()})")

            current_price = last_row['close']
            sma20_current = last_row['SMA20']
            vol_ratio = last_row.get('vol_ratio', 0)
            
            # Status
            status_str = "YES" if current_price >= sma20_current else "NO"
            
            # Deviation
            deviation = (current_price - sma20_current) / sma20_current
            
            # Signal Date (Backtrack)
            price_arr = df['close'].values
            sma_arr = df['SMA20'].values
            dates_arr = df['date'].values
            
            idx = len(df) - 1
            curr_state = (price_arr[idx] >= sma_arr[idx])
            
            signal_idx = -1
            for i in range(idx - 1, 20, -1):
                if pd.isna(sma_arr[i]): break
                state_i = (price_arr[i] >= sma_arr[i])
                if state_i != curr_state:
                    signal_idx = i + 1
                    break
            
            interval_change = 0.0
            change_date_str = "-"
            if signal_idx != -1:
                # Safe date conversion
                ts = (dates_arr[signal_idx] - np.datetime64('1970-01-01T00:00:00Z')) / np.timedelta64(1, 's')
                change_date_str = datetime.utcfromtimestamp(ts).strftime("%y.%m.%d")
                base_price = price_arr[signal_idx]
                interval_change = (current_price - base_price) / base_price

            # Daily Change
            prev_close = df.iloc[-2]['close']
            daily_change = (current_price - prev_close) / prev_close
            
            # Vol Ratio Format
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
                "_deviation_raw": deviation
            })
            
        except Exception as e:
            print(f"Error processing {name}: {e}")
            import traceback
            traceback.print_exc()

    # Sort results by deviation descending
    results.sort(key=lambda x: x.get('_deviation_raw', -999), reverse=True)
    
    # Remove raw helper key if desired, or just let it drop during DataFrame column selection if we selected columns. 
    # But fish_basin.py might just convert all. Let's select columns explicitly or drop.
    return pd.DataFrame(results).drop(columns=['_deviation_raw'], errors='ignore')

def save_to_excel(df, filename="results/fish_basin_report.xlsx"):
    """
    Save the dataframe to an Excel file with conditional formatting.
    Red for Bullish/Positive, Green for Bearish/Negative.
    """
    if df.empty: return
    
    # Ensure directory exists
    import os
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    # 1. Create a Styler
    # Helper to color text
    def color_status(val):
        color = 'red' if val == 'YES' else 'green'
        return f'color: {color}'
        
    def color_pct(val):
        # val is string like "+1.23%" or "-0.5%"
        try:
            v = float(val.strip('%'))
            color = 'red' if v > 0 else 'green'
            return f'color: {color}'
        except:
            return ''

    # Apply styles
    # Note: subset needs columns to exist
    try:
        styler = df.style.map(color_status, subset=['状态'])\
                        .map(color_pct, subset=['涨幅%', '偏离率', '区间涨幅%'])
                         
        # 2. Save
        styler.to_excel(filename, index=False, engine='openpyxl')
        print(f"Excel report saved to: {filename}")
        
        # 3. Post-process for column widths (Optional but nice)
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
                except:
                    pass
            adjusted_width = (max_length + 2)
            ws.column_dimensions[column[0].column_letter].width = adjusted_width
        wb.save(filename)
        
    except Exception as e:
        print(f"Failed to save Excel: {e}")

if __name__ == "__main__":
    # Expanded monitoring list
    # Expanded monitoring list
    # Format: "Name": "Code"
    targets = {
        "白银现货": "SI", # COMEX Silver
        "黄金现货": "GC", # COMEX Gold
        "中证500": "sz399905",
        "科创50": "sh000688",
        # "中证2000": "sz932000", # EM Daily 932000 might fail, let's use proxy if found
        "中证2000": "sz399303", # CNI 2000 proxy
        "中证1000": "sz399852",
        "中证A500": "932000", # Use official code via new fetcher
        "微盘股": "ths_微盘股", # Use THS Concept
        "北证50": "bj899050",
        "创业板指": "sz399006",
        "恒生科技": "hkHSTECH",
        "恒生指数": "hkHSI",
        "沪深300": "sh000300",
        "上证50": "sh000016",
        "标普500": "us.INX",
        "纳指100": "us.IXIC",
        "上证指数": "sh000001" 
    }
    
    df = get_fish_basin_analysis(targets)
    
    print("\n=== 鱼盆趋势模型v2.0 (Fish Basin Model) ===")
    print(f"Date: {datetime.now().strftime('%Y.%m.%d')}")
    
    if not df.empty:
        curr_date = datetime.now().strftime('%Y%m%d')
        output_path = f"results/{curr_date}/fish_basin_report.xlsx"
        # Save Excel
        save_to_excel(df, output_path)

        # Define ANSI colors
        RED = '\033[91m'
        GREEN = '\033[92m'
        RESET = '\033[0m'
        BOLD = '\033[1m'
        
        # Columns to display - Added Volume Ratio
        headers = ["代码", "名称", "状态", "涨幅%", "现价", "临界值点", "偏离率", "量比", "状态变量时间", "区间涨幅%"]
        
        # Print Header
        header_str = "  ".join([f"{h:<8}" for h in headers])
        print(f"{BOLD}{header_str}{RESET}")
        
        for _, row in df.iterrows():
            # Extract raw values for color logic (strip % and convert)
            try:
                # Status Color
                status = row['状态']
                status_color = RED if status == 'YES' else GREEN
                
                # Change % Color
                chg_str = row['涨幅%']
                chg_val = float(chg_str.strip('%'))
                chg_color = RED if chg_val > 0 else GREEN
                
                # Deviation Color
                dev_str = row['偏离率']
                dev_val = float(dev_str.strip('%'))
                dev_color = RED if dev_val > 0 else GREEN
                
                # Interval Color
                int_str = row['区间涨幅%']
                int_val = float(int_str.strip('%'))
                int_color = RED if int_val > 0 else GREEN
                
                # Format the line
                line = [
                    f"{row['代码']:<8}",
                    f"{row['名称']:<8}",
                    f"{status_color}{status:<8}{RESET}",
                    f"{chg_color}{chg_str:<8}{RESET}",
                    f"{str(row['现价']):<8}",
                    f"{str(row['临界值点']):<8}",
                    f"{dev_color}{dev_str:<8}{RESET}",
                    f"{str(row['量比']):<8}",
                    f"{row['状态变量时间']:<12}",
                    f"{int_color}{int_str:<8}{RESET}"
                ]
                print("  ".join(line))
                
            except Exception as e:
                # Fallback if parsing fails
                print(row.to_string())
    else:
        print("No data generated.")
