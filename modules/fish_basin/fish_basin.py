import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime
import time
import os
from .fish_basin_helper import save_to_excel

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
    "中证A500": "sh000510", # Updated to sh000510
    "国证2000": "sz399303", 
    "国证微盘": "sz399852", 

    # --- HK ---
    "恒生指数": "hkHSI",
    "恒生科技": "hkHSTECH",
    
    # --- US ---
    "纳斯达克": "us.IXIC",
    "标普500": "us.INX",

    # --- Commodities / FX ---
    "COMEX黄金": "GC", 
    "COMEX白银": "SI",
    "美元离岸人民币": "FX_USDCNH", # Added (Using CNY proxy if CNH unavailable)
}

def fetch_data(name, code):
    """
    Fetch data for a given symbol.
    Handles Commodities, US/HK Indices, and A-Share Indices.
    """
    try:
        df = None
        
        # 0. FX (USD/CNH)
        if code == "FX_USDCNH":
            try:
                # Attempt to get USD/CNY from BOC as a proxy for USD/CNH
                # Akshare free APIs for CNH history are limited. 
                # currency_boc_sina returns '中行折算价' (Conversion Rate) which is a good daily reference.
                df = ak.currency_boc_sina(symbol="美元", start_date="20240101", end_date="20261231")
                if df is not None:
                     # Rename columns
                     # '日期', '中行汇买价', '中行钞买价', '中行钞卖价/汇卖价', '央行中间价', '中行折算价'
                     df = df.rename(columns={'日期': 'date', '中行折算价': 'close'})
                     # Data is per 100 units (e.g. 720.0), scale to 7.20
                     df['close'] = pd.to_numeric(df['close'], errors='coerce') / 100.0
                     df['volume'] = 0 # No volume for FX rate
                     
                     # Fill Open/High/Low with Close as we only need Close for trend
                     df['open'] = df['close']
                     df['high'] = df['close']
                     df['low'] = df['close']
            except: pass
            if df is not None: return df

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
             # Use hk_index_daily_sina (History)
             try:
                 symbol_clean = code[2:] # Remove 'hk' prefix
                 df = ak.stock_hk_index_daily_sina(symbol=symbol_clean)
                 
                 # Check if we need to append today's spot data
                 if df is not None and not df.empty:
                     df['date'] = pd.to_datetime(df['date'])
                     last_date = df['date'].iloc[-1].date()
                     today_date = datetime.now().date()
                     
                     if last_date < today_date:
                         # Fetch Spot Data
                         try:
                             spot_df = ak.stock_hk_index_spot_em()
                             # Filter by code (e.g. HSI or HSTECH)
                             target_row = spot_df[spot_df['代码'] == symbol_clean]
                             if not target_row.empty:
                                 row = target_row.iloc[0]
                                 new_data = {
                                     'date': pd.to_datetime(today_date),
                                     'open': row['今开'],
                                     'high': row['最高'],
                                     'low': row['最低'],
                                     'close': row['最新价'],
                                     'volume': row['成交量']
                                 }
                                 # Convert new_data to DataFrame and concat
                                 # Ensure types are correct
                                 new_df = pd.DataFrame([new_data])
                                 df = pd.concat([df, new_df], ignore_index=True)
                         except Exception as e_spot:
                             print(f"Failed to fetch HK spot data for {code}: {e_spot}")
             except Exception as e: 
                 print(f"Error fetching HK history: {e}")


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

        # 5. Specialized A-Share Index (CSI A500) - Use EM source first
        elif code == "sh000510":
             try:
                 # Use EM source (Plan A)
                 df = ak.stock_zh_index_daily_em(symbol="sh000510")
             except:
                 # Fallback to Sina (Plan B)
                 try:
                     df = ak.stock_zh_index_daily(symbol="sh000510")
                 except: pass

        # 6. Generic A-Share Indices (Default)
        else:
             # Try EM Daily first
             try:
                df = ak.stock_zh_index_daily_em(symbol=code)
             except:
                # Fallback to Sina Daily
                try:
                    df = ak.stock_zh_index_daily(symbol=code)
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
            # 大哥黄线: (MA14 + MA28 + MA57 + MA114) / 4
            df['MA14'] = close.rolling(window=14).mean()
            df['MA28'] = close.rolling(window=28).mean()
            df['MA57'] = close.rolling(window=57).mean()
            df['MA114'] = close.rolling(window=114).mean()
            df['大哥黄线'] = (df['MA14'] + df['MA28'] + df['MA57'] + df['MA114']) / 4
            
            # 趋势白线: EMA(EMA(C,10),10)
            ema10 = close.ewm(span=10, adjust=False).mean()
            df['趋势白线'] = ema10.ewm(span=10, adjust=False).mean()
            
            # Volume Ratio (Vol / MA5_Vol)
            if 'volume' in df.columns:
                vol_ma5 = df['volume'].rolling(window=5).mean()
                df['vol_ratio'] = df['volume'] / vol_ma5
            else:
                df['vol_ratio'] = np.nan

            df_valid = df.dropna(subset=['大哥黄线']).copy()
            if df_valid.empty: continue
            
            last_row = df_valid.iloc[-1]
            current_date = last_row['date']
            
            # If data is too old (e.g. > 5 days), warn?
            # day_diff = (datetime.now() - current_date).days
            # if day_diff > 5: print(f"Warning: Data for {name} is old ({current_date.date()})")

            current_price = last_row['close']
            dage_yellow_current = last_row['大哥黄线']
            white_line_current = last_row['趋势白线']
            vol_ratio = last_row.get('vol_ratio', 0)
            
            # Status
            status_str = "YES" if current_price >= dage_yellow_current else "NO"
            
            # Deviation
            deviation = (current_price - dage_yellow_current) / dage_yellow_current
            
            # Signal Date (Backtrack for price crossing yellow line)
            price_arr = df['close'].values
            indicator_arr = df['大哥黄线'].values
            white_arr = df['趋势白线'].values
            dates_arr = df['date'].values
            
            idx = len(df) - 1
            curr_state = (price_arr[idx] >= indicator_arr[idx])
            
            signal_idx = -1
            for i in range(idx - 1, 114, -1):  # 大哥黄线需要114天数据
                if pd.isna(indicator_arr[i]): break
                state_i = (price_arr[i] >= indicator_arr[i])
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

            # 计算金叉/死叉持续天数 (白线vs黄线)
            golden_cross_days = 0  # 白线在黄线之上的持续天数
            death_cross_days = 0   # 白线在黄线之下的持续天数
            
            # 当前状态：白线 > 黄线 = 金叉状态
            current_is_golden = white_arr[idx] > indicator_arr[idx]
            
            for i in range(idx, 114, -1):
                if pd.isna(white_arr[i]) or pd.isna(indicator_arr[i]): break
                is_golden = white_arr[i] > indicator_arr[i]
                if is_golden == current_is_golden:
                    if current_is_golden:
                        golden_cross_days += 1
                    else:
                        death_cross_days += 1
                else:
                    break
            
            # 如果不是对应状态，设为0
            if current_is_golden:
                death_cross_days = 0
            else:
                golden_cross_days = 0

            # Daily Change
            prev_close = df.iloc[-2]['close']
            daily_change = (current_price - prev_close) / prev_close
            
            # 白线偏离率
            white_deviation = (current_price - white_line_current) / white_line_current
            
            # Vol Ratio Format
            vr_str = f"{vol_ratio:.2f}" if pd.notna(vol_ratio) else "-"
            
            results.append({
                "代码": code,
                "名称": name,
                "状态": status_str,
                "涨幅%": f"{daily_change*100:+.2f}%",
                "现价": int(current_price) if current_price > 5 else f"{current_price:.2f}",
                "黄线": int(dage_yellow_current),
                "白线": int(white_line_current) if white_line_current > 5 else f"{white_line_current:.2f}",
                "黄线偏离率": f"{deviation*100:.2f}%",
                "白线偏离率": f"{white_deviation*100:.2f}%",
                "量比": vr_str,
                "金叉天数": golden_cross_days if golden_cross_days > 0 else "-",
                "死叉天数": death_cross_days if death_cross_days > 0 else "-",
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

# Export Default Targets for external use
DEFAULT_TARGETS = {
    "白银现货": "SI", # COMEX Silver
    "黄金现货": "GC", # COMEX Gold
    "中证500": "sz399905",
    "科创50": "sh000688",
    # "中证2000": "sz932000", # EM Daily 932000 might fail, let's use proxy if found
    "中证2000": "sz399303", # CNI 2000 proxy
    "中证1000": "sz399852",
    "中证A500": "sh000510", # Use Sina source (tested)
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

def run(date_dir=None, save_excel=True):
    """
    Main entry point for Fish Basin Index Analysis.
    Returns the DataFrame.
    """
    print("\n=== 鱼盆趋势模型v2.0 (Fish Basin Model) ===")
    print(f"Date: {datetime.now().strftime('%Y.%m.%d')}")
    
    df = get_fish_basin_analysis(DEFAULT_TARGETS)
    
    if not df.empty:
        curr_date = datetime.now().strftime('%Y%m%d')
        output_path = None
        
        # Calculate Rank Change (Logic preserved)
        df['排名变化'] = "-"
        try:
            from datetime import timedelta
            today = datetime.now()
            for days_back in range(1, 8):
                prev_date = (today - timedelta(days=days_back)).strftime('%Y%m%d')
                
                # Check Merged first, then Individual
                merged_prev = f"results/{prev_date}/趋势模型_合并.xlsx"
                old_prev = f"results/{prev_date}/趋势模型_指数.xlsx"
                prev_df = None
                
                if os.path.exists(merged_prev):
                    try: prev_df = pd.read_excel(merged_prev, sheet_name='指数')
                    except: pass
                
                if prev_df is None and os.path.exists(old_prev):
                    prev_df = pd.read_excel(old_prev)
                
                if prev_df is not None:
                    if '名称' in prev_df.columns:
                        prev_rank = {name: idx+1 for idx, name in enumerate(prev_df['名称'].tolist())}
                        rank_changes = []
                        for idx, row in df.iterrows():
                            name = row['名称']
                            today_rank = idx + 1
                            if name in prev_rank:
                                change = prev_rank[name] - today_rank
                                if change > 0: rank_changes.append(f"+{change}")
                                elif change < 0: rank_changes.append(str(change))
                                else: rank_changes.append("-")
                            else: rank_changes.append("新")
                        df['排名变化'] = rank_changes
                    break
        except Exception as e:
            print(f"排名变化计算失败: {e}")
              
        # Save Excel only if requested
        if save_excel:
            if date_dir:
                 output_path = os.path.join(date_dir, "趋势模型_指数.xlsx")
            else:
                 output_path = f"results/{curr_date}/趋势模型_指数.xlsx"
            save_to_excel(df, output_path)

        # Console Output (Preserved)
        RED = '\033[91m'
        GREEN = '\033[92m'
        RESET = '\033[0m'
        BOLD = '\033[1m'
        headers = ["代码", "名称", "状态", "涨幅%", "现价", "黄线", "白线", "黄线偏离率", "白线偏离率", "金叉天数", "死叉天数", "排名变化"]
        header_str = "  ".join([f"{h:<10}" for h in headers])
        print(f"{BOLD}{header_str}{RESET}")
        
        for _, row in df.iterrows():
            try:
                status = row['状态']
                status_color = RED if status == 'YES' else GREEN
                chg_str = row['涨幅%']
                chg_val = float(chg_str.strip('%'))
                chg_color = RED if chg_val > 0 else GREEN
                dev_str = row['黄线偏离率']
                dev_val = float(dev_str.strip('%'))
                dev_color = RED if dev_val > 0 else GREEN
                white_dev_str = row['白线偏离率']
                white_dev_val = float(white_dev_str.strip('%'))
                white_dev_color = RED if white_dev_val > 0 else GREEN
                rank_change = str(row.get('排名变化', '-'))
                rank_color = RED if rank_change.startswith('+') else (GREEN if rank_change.startswith('-') and rank_change != '-' else RESET)
                
                line = [
                    f"{row['代码']:<10}",
                    f"{row['名称']:<10}",
                    f"{status_color}{status:<10}{RESET}",
                    f"{chg_color}{chg_str:<10}{RESET}",
                    f"{str(row['现价']):<10}",
                    f"{str(row['黄线']):<10}",
                    f"{str(row['白线']):<10}",
                    f"{dev_color}{dev_str:<10}{RESET}",
                    f"{white_dev_color}{white_dev_str:<10}{RESET}",
                    f"{str(row['金叉天数']):<10}",
                    f"{str(row['死叉天数']):<10}",
                    f"{rank_color}{rank_change:<6}{RESET}"
                ]
                print("  ".join(line))
            except: pass
            
        return df
    else:
        print("No data generated.")
        return pd.DataFrame()

if __name__ == "__main__":
    run()
