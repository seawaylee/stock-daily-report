


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
            # Try fetching THS data first
            try:
                df = ak.stock_board_industry_index_ths(symbol=name, start_date=start_date, end_date="20260201")
            except: 
                df = None

            # CHECK DATA FRESHNESS & FALLBACK TO EM
            # If df is empty OR df date is old, try EM
            is_old = True
            if df is not None and not df.empty:
                df['日期'] = pd.to_datetime(df['日期'])
                last_date = df['日期'].max().date()
                today_date = datetime.now().date()
                if last_date >= today_date:
                    is_old = False
            
            if is_old:
                # print(f"⚠️ THS data for {name} is old/missing, trying EM fallback...")
                try:
                    # 1. Find EM Code by Name
                    board_list = ak.stock_board_industry_name_em()
                    row = board_list[board_list['板块名称'] == name]
                    
                    if not row.empty:
                        em_code = row.iloc[0]['板块代码']
                        # 2. Fetch EM History
                        df_em = ak.stock_board_industry_hist_em(symbol=em_code, start_date=start_date, end_date="20260201")
                        
                        if df_em is not None and not df_em.empty:
                            # Standardize columns to match THS format for downstream processing
                            # EM: 日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额, ...
                            df_em = df_em.rename(columns={
                                '开盘': '开盘价', '收盘': '收盘价',
                                '最高': '最高价', '最低': '最低价'
                            })
                            # Use this if it's fresher or if we had nothing
                            df = df_em
                            # print(f"✅ Switched to EM data for {name}")
                except Exception as e_em:
                    # print(f"EM fallback failed for {name}: {e_em}")
                    pass


        # 2. THS Concept
        elif itype == 'THS_CONCEPT':
            df = ak.stock_board_concept_index_ths(symbol=name, start_date=start_date, end_date="20260201")
            
        # 3. EM Concept (New)
        elif itype == 'EM_CONCEPT':
             # Try to Use Code if provided, otherwise find by name
            target_code = code
            if not target_code:
                 # Lookup code by name
                 board_list = ak.stock_board_concept_name_em()
                 row = board_list[board_list['板块名称'] == name]
                 if not row.empty:
                     target_code = row.iloc[0]['板块代码']
            
            if target_code:
                df = ak.stock_board_concept_hist_em(symbol=target_code, start_date=start_date, end_date="20260201")
                if df is not None and not df.empty:
                    # Rename columns to match THS format
                    # EM: 日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额, ...
                    df = df.rename(columns={
                        '开盘': 'open', '收盘': 'close',
                        '最高': 'high', '最低': 'low',
                        '成交量': 'volume', '成交额': 'turnover',
                        '日期': 'date'
                    })
                    # EM data usually good quality
                    turnover = df.iloc[-1]['turnover'] if 'turnover' in df.columns else 0
            
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
            display_name = name
            if 'alias' in item:
                display_name = item['alias']

            return display_name, code, df, turnover, name # Return original name at the end

    except Exception as e:
        # print(f"Error fetching {name}: {e}")
        pass

    return name, code, None, 0, name # Return original name

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
        # 动态检测可用的百分比列
        pct_columns = [c for c in ['涨幅%', '黄线偏离率', '白线偏离率', '偏离率', '区间涨幅%'] if c in df.columns]
        styler = df.style.map(color_status, subset=['状态'])\
                        .map(color_pct, subset=pct_columns)
                         
        # 高亮条件: 金叉=1天、死叉=1天、或状态转换日期是今天
        def highlight_important_row(row):
            today_str = datetime.now().strftime("%y.%m.%d")
            should_highlight = False
            
            # 检查金叉天数=1
            if '金叉天数' in row and row['金叉天数'] == 1:
                should_highlight = True
            # 检查死叉天数=1
            if '死叉天数' in row and row['死叉天数'] == 1:
                should_highlight = True
            # 检查状态变量时间是否是今天
            if '状态变量时间' in row:
                status_time = str(row['状态变量时间']).strip()
                if status_time == today_str:
                    should_highlight = True
            
            if should_highlight:
                return ['background-color: #FFFFCC'] * len(row)  # Light Yellow
            return [''] * len(row)

        styler = styler.apply(highlight_important_row, axis=1)
                         
        styler.to_excel(filename, index=False, engine='openpyxl')
        
        # 优化列宽 - 考虑中文字符
        from openpyxl import load_workbook
        wb = load_workbook(filename)
        ws = wb.active
        for column in ws.columns:
            max_length = 0
            column = [cell for cell in column]
            for cell in column:
                try:
                    cell_value = str(cell.value) if cell.value else ""
                    # 中文字符按2个字符宽度计算
                    length = sum(2 if ord(c) > 127 else 1 for c in cell_value)
                    if length > max_length:
                        max_length = length
                except: pass
            # 确保最小宽度为8，加上padding
            adjusted_width = max(max_length + 3, 8)
            ws.column_dimensions[column[0].column_letter].width = adjusted_width
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

def get_spot_data_map():
    """
    Fetch Real-time Spot Data (Sectors) from THS Summary.
    Returns dict: {'SectorName': {'pct': float, 'avg_price': float, 'turnover': float}}
    """
    spot_map = {}
    try:
        # Use THS Summary
        df = ak.stock_board_industry_summary_ths()
        if df is not None and not df.empty:
            # Expected cols: 板块, 涨跌幅, 均价, ...
            for _, row in df.iterrows():
                name = row['板块']
                try:
                    pct = float(row['涨跌幅']) # e.g. 10.32 or 0.55
                except: pct = 0.0
                
                try:
                    # '均价' might be price, but for Index Trend, we mostly care about % Change
                    # We will calculate NewPrice = OldPrice * (1 + pct/100)
                    pass
                except: pass
                
                spot_map[name] = {'pct': pct}
        return spot_map
    except Exception as e:
        print(f"⚠️ Spot Data Fetch Failed: {e}")
        return {}

def patch_today_spot(df, name, spot_map):
    """
    Patch the DataFrame with today's spot data if missing.
    """
    if df is None or df.empty: return df
    if name not in spot_map: return df
    
    try:
        spot_info = spot_map[name]
        spot_pct = spot_info['pct'] # Percentage (e.g. 5.0 for 5%)
        
        # Check last date
        last_date = pd.to_datetime(df.iloc[-1]['date']).date()
        today_date = datetime.now().date()
        
        if last_date < today_date:
            # Need Patch
            last_row = df.iloc[-1]
            last_close = float(last_row['close'])
            
            # Calculate New Close
            new_close = last_close * (1 + spot_pct / 100.0)
            
            # Construct New Row
            new_row = last_row.copy()
            new_row['date'] = pd.Timestamp(today_date)
            new_row['close'] = new_close
            new_row['high'] = new_close # Approx
            new_row['low'] = new_close  # Approx
            new_row['open'] = new_close # Approx
            
            # Append
            # df = df.append(new_row, ignore_index=True) # Deprecated
            new_df = pd.DataFrame([new_row])
            df = pd.concat([df, new_df], ignore_index=True)
            
            # print(f"🔧 Patched {name}: {last_date} -> {today_date} (Pct: {spot_pct}%)")
            
        elif last_date == today_date:
            # Already has today? Check if it looks stale (e.g. if spot is huge but data is small)
            # But usually THS historical is just yesterday.
            # If it HAS today, trusting it is usually safer unless we are sure it's wrong.
            # However, for White Liquor, user said 0.55 vs 10.
            # If the DF has today's date but the change is mismatching spot, we might want to OVERWRITE.
            # But let's assume the issue is MISSING date generally.
            pass
            
            # Advanced: Overwrite if deviation is huge?
            # Let's start with missing date patch.
            
    except Exception as e:
        print(f"Patch failed for {name}: {e}")
        
    return df



def run(date_dir=None, save_excel=True):
    """
    Main entry point for Fish Basin Sector Analysis.
    Returns the DataFrame.
    """
    print("=== Fish Basin Sector Analysis (Configured List) ===")
    
    # 1. Load Config
    print("Loading Sector Config...")
    items = load_sector_config()
    if not items:
        print("No items found in config.")
        return pd.DataFrame()

    # 2. Deduplicate (just in case)
    unique_map = {}
    for item in items:
        unique_map[item['name']] = item
    
    final_list = list(unique_map.values())
    print(f"Total items to process from config: {len(final_list)}")

    # 3. Fetch Data (logic moved below to support better tracking)


    # 4. Retry Logic for Missing Items
    # Fix: Use successful_config_names to track by ORIGINAL config name, not the output name (which might be aliased)
    successful_config_names = set()

        
    # Re-doing the collection logic to be safer
    processed_results = []
    successful_config_names = set()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor: # Reduced to 1 to avoid libmini_racer crash
        futures = {executor.submit(fetch_data_router, item): item for item in final_list}
        
        for future in concurrent.futures.as_completed(futures):
            item = futures[future]
            try:
                name, code, df, turnover, original_name = future.result()
                if df is not None and not df.empty:
                    processed_results.append({
                        'name': name, 'code': code, 'df': df, 'turnover': turnover, 'original_name': original_name
                    })
                    successful_config_names.add(item['name']) # Track by CONFIG name
                # else: logic handles as missing implicitly
            except Exception as e:
                print(f"❌ Initial fetch failed for {item['name']}: {e}")

    missing_items = [item for item in final_list if item['name'] not in successful_config_names]
    
    if missing_items:
        print(f"\n🔄 Retrying {len(missing_items)} failed items sequentially...")
        import time
        max_retries = 2
        
        for attempt in range(max_retries):
            if not missing_items: break
            
            still_missing = []
            for item in missing_items:
                try:
                    # Sequential Retry
                    time.sleep(1.0) # Delay
                    name, code, df, turnover, original_name = fetch_data_router(item)
                    if df is not None and not df.empty:
                        print(f"✅ Retry success: {name}")
                        processed_results.append({
                            'name': name, 'code': code, 'df': df, 'turnover': turnover, 'original_name': original_name
                        })
                    else:
                        still_missing.append(item)
                except:
                    still_missing.append(item)
            
            missing_items = still_missing
            if missing_items:
                print(f"   Cycle {attempt+1} done. {len(missing_items)} still missing.")

    final_results_list = processed_results
            
    print(f"Successfully fetched: {len(final_results_list)}")
    
    # --- Summary Section ---
    success_count = len(final_results_list)
    total_count = len(final_list)
    fail_count = total_count - success_count
    
    print("\n" + "="*40)
    print(f"📊 趋势模型(题材)执行汇总")
    print(f"✅ 成功: {success_count}/{total_count}")
    print(f"❌ 失败: {fail_count}/{total_count}")
    
    if fail_count > 0:
        found_names = {r['name'] for r in final_results_list}
        all_names = {r['name'] for r in final_list}
        missing = all_names - found_names
        print(f"⚠️ 最终失败列表: {', '.join(missing)}")
    print("="*40 + "\n")

    # Spot Data Pre-fetch
    print("Fetching Spot Data for Patching...")
    spot_map = get_spot_data_map()
    print(f"Spot Data Loaded: {len(spot_map)} sectors")

    results = []
    for item in final_results_list:
        name = item['name']
        code = item['code']
        df = item['df']
        original_name = item.get('original_name', name)

        # --- Apply Spot Patch ---
        # Use ORIGINAL NAME for spot lookup (e.g. "工业金属" not "有色金属")
        df = patch_today_spot(df, original_name, spot_map)

        # Fish Basin Logic
        close = df['close']
        
        df['MA14'] = close.rolling(window=14).mean()
        df['MA28'] = close.rolling(window=28).mean()
        df['MA57'] = close.rolling(window=57).mean()
        df['MA114'] = close.rolling(window=114).mean()
        df['大哥黄线'] = (df['MA14'] + df['MA28'] + df['MA57'] + df['MA114']) / 4
        
        ema10 = close.ewm(span=10, adjust=False).mean()
        df['趋势白线'] = ema10.ewm(span=10, adjust=False).mean()
        
        if 'volume' in df.columns:
            vol_ma5 = df['volume'].rolling(window=5).mean()
            df['vol_ratio'] = df['volume'] / vol_ma5
        else:
            df['vol_ratio'] = np.nan
            
        df_valid = df.dropna(subset=['大哥黄线']).copy()
        if df_valid.empty: continue
        
        last_row = df_valid.iloc[-1]
        current_price = last_row['close']
        dage_yellow_current = last_row['大哥黄线']
        white_line_current = last_row['趋势白线']
        vol_ratio = last_row.get('vol_ratio', 0)
        
        status_str = "YES" if current_price >= dage_yellow_current else "NO"
        deviation = (current_price - dage_yellow_current) / dage_yellow_current
        white_deviation = (current_price - white_line_current) / white_line_current
        
        # Backtrack
        price_arr = df['close'].values
        yellow_arr = df['大哥黄线'].values
        white_arr = df['趋势白线'].values
        dates_arr = df['date'].values
        
        idx = len(df) - 1
        curr_state = (price_arr[idx] >= yellow_arr[idx])
        
        signal_idx = -1
        min_idx = min(114, len(df) - 1)
        for i in range(idx - 1, min_idx, -1):
            if i < 0: break
            if pd.isna(yellow_arr[i]): break
            state_i = (price_arr[i] >= yellow_arr[i])
            if state_i != curr_state:
                signal_idx = i + 1
                break
                
        interval_change = 0.0
        change_date_str = "-"
        
        if signal_idx != -1:
            try:
                ts = (dates_arr[signal_idx] - np.datetime64('1970-01-01T00:00:00Z')) / np.timedelta64(1, 's')
                change_date_str = datetime.utcfromtimestamp(ts).strftime("%y.%m.%d")
                base_price = price_arr[signal_idx]
                interval_change = (current_price - base_price) / base_price
            except: pass

        golden_cross_days = 0 
        death_cross_days = 0
        current_is_golden = white_arr[idx] > yellow_arr[idx]
        for i in range(idx, min_idx, -1):
            if i < 0: break
            if pd.isna(white_arr[i]) or pd.isna(yellow_arr[i]): break
            is_golden = white_arr[i] > yellow_arr[i]
            if is_golden == current_is_golden:
                if current_is_golden: golden_cross_days += 1
                else: death_cross_days += 1
            else: break
        if current_is_golden: death_cross_days = 0
        else: golden_cross_days = 0

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

    results.sort(key=lambda x: x['_deviation_raw'], reverse=True)

    df_res = pd.DataFrame(results)
    if not df_res.empty:
        df_res['排名变化'] = "-"
        try:
            from datetime import timedelta
            today = datetime.now()
            for days_back in range(1, 8):
                prev_date = (today - timedelta(days=days_back)).strftime('%Y%m%d')
                
                # Check Individual file FIRST (More reliable for same-type comparison)
                old_prev = f"results/{prev_date}/趋势模型_题材.xlsx"
                merged_prev = f"results/{prev_date}/趋势模型_合并.xlsx"
                prev_df = None

                if os.path.exists(old_prev):
                    try:
                        prev_df = pd.read_excel(old_prev)
                        # print(f"Comparing ranks with previous file: {old_prev}")
                    except: pass

                if prev_df is None and os.path.exists(merged_prev):
                    try:
                        prev_df = pd.read_excel(merged_prev, sheet_name='题材')
                    except:
                        try:
                            # Fallback to default sheet if '题材' missing
                            prev_df = pd.read_excel(merged_prev)
                        except: pass
                
                if prev_df is not None:
                    if '名称' in prev_df.columns:
                        prev_rank = {name: idx+1 for idx, name in enumerate(prev_df['名称'].tolist())}
                        rank_changes = []
                        for idx, row in df_res.iterrows():
                            name = row['名称']
                            today_rank = idx + 1
                            if name in prev_rank:
                                change = prev_rank[name] - today_rank
                                if change > 0: rank_changes.append(f"+{change}")
                                elif change < 0: rank_changes.append(str(change))
                                else: rank_changes.append("-")
                            else: rank_changes.append("新")
                        df_res['排名变化'] = rank_changes
                    break
        except Exception as e:
            print(f"排名变化计算失败: {e}")
        
        cols = ["代码", "名称", "状态", "涨幅%", "现价", "黄线", "白线", "黄线偏离率", "白线偏离率", "金叉天数", "死叉天数", "量比", "状态变量时间", "区间涨幅%", "排名变化"]
        df_res = df_res[[c for c in cols if c in df_res.columns]]
        print("\n=== Result Head (Sorted by Deviation) ===")
        print(df_res.head(10).to_string())
        
        curr_date = datetime.now().strftime('%Y%m%d')
        if save_excel:
            if date_dir:
                 output_path = os.path.join(date_dir, "趋势模型_题材.xlsx")
            else:
                 output_path = f"results/{curr_date}/趋势模型_题材.xlsx"
                 
            print(f"Saving to {output_path}...")
            save_to_excel_colored(df_res, output_path)
        
        return df_res
    else:
        print("No results generated.")
        return pd.DataFrame()

if __name__ == "__main__":
    run()

if __name__ == "__main__":
    run()

