
import akshare as ak
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.font_manager as fm
from datetime import datetime, timedelta
import os
import platform

# --- Configuration ---
plt.style.use('default')

def get_font_prop():
    system = platform.system()
    font_path = None
    if system == 'Darwin':
        paths = [
            '/System/Library/Fonts/PingFang.ttc',
            '/System/Library/Fonts/STHeiti Light.ttc',
            '/System/Library/Fonts/Hiragino Sans GB.ttc'
        ]
        for p in paths:
            if os.path.exists(p):
                font_path = p
                break
    if font_path:
        return fm.FontProperties(fname=font_path)
    return fm.FontProperties()

font_prop = get_font_prop()
font_bold = get_font_prop() # Need a bold version if possible, but regular is fine for now
font_small = get_font_prop()
font_small.set_size(10)

def get_trading_date(date_str, offset=0):
    """
    Get trading date with offset.
    Note: Simplified logic, ideally should query trade calendar.
    For this prototype, we'll try to find previous day by strictly query akshare or assuming logic.
    """
    # Try to fetch recent trade dates
    try:
        df = ak.tool_trade_date_hist_sina()
        df['trade_date'] = pd.to_datetime(df['trade_date']).dt.strftime('%Y%m%d')
        dates = df['trade_date'].tolist()
        
        if date_str in dates:
            idx = dates.index(date_str)
            if idx + offset >= 0 and idx + offset < len(dates):
                return dates[idx + offset]
    except:
        pass
    
    # Fallback
    d = datetime.strptime(date_str, '%Y%m%d')
    d = d + timedelta(days=offset)
    return d.strftime('%Y%m%d')

def get_limit_up_data(date_str):
    """Fetch Limit Up, Fried, and Previous Limit Up data"""
    print(f"Fetching data for {date_str}...")
    
    # 1. Today's Limit Up
    try:
        df_zt = ak.stock_zt_pool_em(date=date_str)
        # Ensure columns exist
        if df_zt is None or df_zt.empty:
            print("No Limit Up data found.")
            return None, None, None
        
        # Renaissance (Columns mapping)
        # Code, Name, Time, BoardCount, Industry
        df_zt = df_zt[['代码', '名称', '首次封板时间', '最后封板时间', '连板数', '所属行业', '涨停统计']]
    except Exception as e:
        print(f"Error fetching ZT pool: {e}")
        return None, None, None

    # 2. Today's Fried Board
    try:
        df_fried = ak.stock_zt_pool_zbgc_em(date=date_str)
        if df_fried is not None and not df_fried.empty:
            df_fried = df_fried[['代码', '名称', '首次封板时间', '所属行业', '涨停统计']]
    except:
        df_fried = pd.DataFrame()

    # 3. Yesterday's Limit Up (to find Broken Boards)
    prev_date = get_trading_date(date_str, -1)
    print(f"Fetching previous day data ({prev_date})...")
    try:
        df_prev = ak.stock_zt_pool_em(date=prev_date)
        if df_prev is not None and not df_prev.empty:
            df_prev = df_prev[['代码', '名称', '连板数', '所属行业']]
    except:
        df_prev = pd.DataFrame()
    return df_zt, df_fried, df_prev

def get_stock_history(symbol, start_date, end_date):
    """Fetch daily history for a stock"""
    try:
        df = ak.stock_zh_a_hist(symbol=symbol, start_date=start_date, end_date=end_date, adjust='qfq')
        return df
    except:
        return None

def repair_board_counts(df_zt, date_str):
    """
    Repair board counts for stocks that might be misclassified (e.g. after suspension).
    Logic: If Board=1 but ZT_Stat shows high activity (e.g. >5 boards in 30 days),
    fetch history to verify true consecutive limit ups.
    """
    if df_zt is None: return df_zt
    
    print("Checking for board count repairs...")
    # Calculate start date for history (e.g. 30 days ago)
    end_date = date_str
    start_date = (datetime.strptime(date_str, "%Y%m%d") - timedelta(days=40)).strftime("%Y%m%d")
    
    for idx, row in df_zt.iterrows():
        boards = row['连板数']
        zt_stat = str(row['涨停统计'])
        code = row['代码']
        
        # Generic Repair Logic
        # If Board Count is significantly less than recent ZT count, it implies a possible reset (e.g. data provider reset after suspension)
        # We trust our own calculation based on continuous limit-ups in trading history
        if '/' in zt_stat:
            try:
                days_range, zts_count = map(int, zt_stat.split('/'))
                
                # Heuristic: Check repair if ZT count is higher than current board count
                if zts_count > boards:
                    # print(f"Inspecting {row['名称']} ({code}) for repair (Stat: {zt_stat}, Board: {boards})...")
                    hist = get_stock_history(code, start_date, end_date)
                    
                    if hist is not None and not hist.empty:
                        # Count consecutive limit ups backwards in TRADING DAYS (ignoring suspension gaps)
                        cnt = 0
                        # Ensure sorted by date descending (latest first)
                        hist = hist.sort_values('日期', ascending=False)
                        
                        # Verify the latest record matches our date (or is very recent) to ensure we aren't counting old history
                        # But for now, just counting backwards from the top is fine as we fetched up to date_str
                        
                        for i in range(len(hist)):
                            pct = hist.iloc[i]['涨跌幅']
                            # Check for Limit Up (approx > 9.5% for 10% stocks, >19.5% for 20% stocks)
                            # Also handle ST 5% (>4.8%)
                            is_limit_up = False
                            if pct > 9.5 or (pct > 19.5):
                                is_limit_up = True
                            elif pct > 4.8 and ('ST' in row['名称'] or 'st' in row['名称']):
                                is_limit_up = True
                                
                            if is_limit_up:
                                cnt += 1
                            else:
                                if i == 0: 
                                    # If today (first record) is not limit up, then boards should be 0 or it's a fried board.
                                    # But we are in df_zt, so it MUST be a limit up today. 
                                    # If data mismatch (hist says not ZT), we stop.
                                    pass 
                                else:
                                    break # Chain broken
                        
                        if cnt > boards:
                            print(f"  -> Repaired {row['名称']} from {boards} to {cnt} boards.")
                            df_zt.at[idx, '连板数'] = cnt
            except Exception as e:
                # print(f"Repair check failed for {code}: {e}")
                pass
                
    return df_zt

def format_time(t_val):
    """Format time string/int to HH:MM"""
    s = str(t_val).strip()
    # Handle int/float conversion if needed
    if '.' in s: s = s.split('.')[0]
    
    # Pad if needed (e.g. 92500 -> 092500)
    if len(s) == 5: s = '0' + s
    
    if len(s) >= 4:
        # Check if already has colon
        if ':' in s:
            return s[:5]
        else:
            # Assume HHMMSS
            return f"{s[:2]}:{s[2:4]}"
    return s

def process_ladder_data(df_zt, df_fried, df_prev):
    """
    Combine data into a ladder structure.
    Returns: {BoardCount: [StockInfoDict]}
    """
    ladder = {}
    
    # 0. Repair Data (Already called in main)
    
    # Process Successes
    prev_board_map = {}
    if df_prev is not None and not df_prev.empty:
         exclude_st = df_prev[~df_prev['名称'].str.contains('ST', na=False)]
         # Handle potential duplicates in code
         prev_board_map = dict(zip(exclude_st['代码'], exclude_st['连板数']))
         
    processed_codes = set()
    
    # 1. Add Successful Limit Ups
    for _, row in df_zt.iterrows():
        boards = row['连板数']
        code = row['代码']
        
        # Check Yi Zi - both first AND last seal time must be 09:25 (never opened)
        first_seal = str(row['首次封板时间']).strip()
        last_seal = str(row['最后封板时间']).strip()
        formatted_first = format_time(first_seal)
        formatted_last = format_time(last_seal)
        # True 一字: sealed at 09:25 and NEVER opened (last seal also 09:25)
        is_yizi = (formatted_first == '09:25') and (formatted_last == '09:25')
        
        # Time Display - show last seal time
        if is_yizi:
            t_display = "一字"
        else:
            t_display = formatted_last

        item = {
            'name': row['名称'],
            'time': t_display,
            'industry': row['所属行业'],
            'status': 'success',
            'is_yizi': is_yizi
        }
        
        if boards not in ladder:
            ladder[boards] = []
        ladder[boards].append(item)
        processed_codes.add(code)
    
    # 2. Add Fried Boards
    if df_fried is not None and not df_fried.empty:
        for _, row in df_fried.iterrows():
            code = row['代码']
            if code in processed_codes: continue
            
            prev_boards = prev_board_map.get(code, 0)
            target_board = prev_boards + 1
            
            # User Feedback: Only show fried boards for 3+ boards (not 2板)
            if target_board < 3: continue
            
            t_display = format_time(row['首次封板时间'])

            item = {
                'name': row['名称'],
                'time': t_display,
                'industry': row['所属行业'],
                'status': 'fried',
                'is_yizi': False
            }
            
            if target_board not in ladder:
                ladder[target_board] = []
            ladder[target_board].append(item)
            processed_codes.add(code)

    # 3. Add Broken Boards
    if df_prev is not None:
        for _, row in df_prev.iterrows():
            code = row['代码']
            if code in processed_codes: continue 
            
            prev_boards = row['连板数']
            target_board = prev_boards + 1
            
            # User Feedback: 2板不看断板! 只过滤1板断板
            # 显示3板及以上的断板 (prev_boards >= 2)
            if prev_boards < 2: continue
            
            ind = row.get('所属行业', '')
            if pd.isna(ind) or not ind: ind = '--'

            item = {
                'name': row['名称'],
                'time': '',
                'industry': ind, 
                'status': 'broken',
                'is_yizi': False
            }
            
            if target_board not in ladder: ladder[target_board] = []
            ladder[target_board].append(item)
            
    # Sort ladder
    sorted_ladder = dict(sorted(ladder.items(), key=lambda item: item[0], reverse=True))
    return sorted_ladder

def draw_ladder_image(ladder, date_str, filename="results/limit_up_ladder.png"):
    """
    Draw using Matplotlib Patches to simulate the Table Layout.
    Matches the reference design with paper-yellow background and proper borders.
    """
    
    # Colors matching reference image
    BG_COLOR = '#F5E6C8'      # Paper yellow background
    BORDER_COLOR = '#C4A35A'  # Warm brown border 
    BOX_BG = '#FAF3E3'        # Lighter box background
    TEXT_COLOR = '#333333'
    TITLE_RED = '#D32F2F'     # Red for "涨停" in title
    INDUSTRY_RED = '#B22222'  # Industry text color
    
    # Setup Figure with Exact Size
    # Width 10 inches, Height 16 inches -> 10:16
    FIG_W = 10.0
    FIG_H = 16.0
    
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=200)
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    
    # Coordinate system: 0..10 X, 0..16 Y - use tighter margins
    MARGIN_X = 0.3
    MARGIN_Y = 0.2
    ax.set_xlim(0, FIG_W)
    ax.set_ylim(0, FIG_H)
    ax.axis('off')

    # --- Layout Calculation ---
    # We lay out from Top (Y=16) downwards
    
    layout_items = []
    
    # 1. Header
    header_h = 1.8  # Reduced whitespace
    layout_items.append({'type': 'header', 'h': header_h})
    
    # 2. Ladder Rows
    import math
    first_board_limit = 30  # Limit first board display
    for board, items in ladder.items():
        # Limit first board items to improve readability
        display_items = items[:first_board_limit] if board == 1 else items
        total_count = len(items)
        
        # Determine Row Height - more compact
        if board == 1:
            col_limit = 5
            base_cell_h = 1.3  # More compact
        else:
            col_limit = 4
            base_cell_h = 1.5  # More compact
            
        rows_needed = math.ceil(len(display_items) / col_limit)
        h = max(base_cell_h, rows_needed * base_cell_h)
        
        layout_items.append({
            'type': 'row', 
            'board': board, 
            'items': display_items, 
            'h': h,
            'total_count': total_count
        })

    # 3. Calculate Scale Factor
    total_content_h = sum(item['h'] for item in layout_items)
    
    # Target content area height (leaving some margin)
    SAFE_H = FIG_H - 0.5
    
    if total_content_h > SAFE_H:
        scale_factor = SAFE_H / total_content_h
        print(f"Content height {total_content_h:.2f} > {SAFE_H}. Scaling by {scale_factor:.2f}")
    else:
        scale_factor = 1.0
    
    # --- Drawing ---
    cursor_y = FIG_H
    
    for layout in layout_items:
        # Scale Height
        h = layout['h'] * scale_factor
        
        # IMPORTANT: Decrement cursor_y FIRST before drawing
        cursor_y -= h
        
        if layout['type'] == 'header':
            # Now cursor_y is the bottom of header, header top is cursor_y + h
            header_top = cursor_y + h
            header_bottom = cursor_y
            
            # Title - positioned near top
            title_y = header_top - (0.6 * scale_factor)
            ax.text(FIG_W/2, title_y, f"{date_str} A股涨停复盘", 
                    ha='center', va='center', fontsize=32*scale_factor, color='#1a1a1a', fontproperties=font_bold, fontweight='bold')
            
            # Badges - show in two rows for better visibility
            # Count industries from ORIGINAL ladder (not limited display)
            all_industries = []
            for bucket in ladder.values():
                for item in bucket:
                    ind = item.get('industry', '')
                    if ind and ind != '--': 
                        all_industries.append(ind)
            from collections import Counter
            top_inds = Counter(all_industries).most_common(8)  # Show top 8
            
            # Split into two rows
            row1_inds = top_inds[:4]
            row2_inds = top_inds[4:]
            
            # Row 1
            badge_y1 = header_bottom + (0.55 * scale_factor)
            start_x1 = FIG_W/2 - (len(row1_inds) * 1.1) / 2
            for i, (ind, count) in enumerate(row1_inds):
                txt = f"{ind}({count})"
                ax.text(start_x1 + i*1.2 + 0.6, badge_y1, txt, 
                        ha='center', va='center', fontsize=20*scale_factor, color='#8B0000', fontproperties=font_bold, fontweight='bold')
            
            # Row 2
            if row2_inds:
                badge_y2 = header_bottom + (0.2 * scale_factor)
                start_x2 = FIG_W/2 - (len(row2_inds) * 1.1) / 2
                for i, (ind, count) in enumerate(row2_inds):
                    txt = f"{ind}({count})"
                    ax.text(start_x2 + i*1.2 + 0.6, badge_y2, txt, 
                            ha='center', va='center', fontsize=20*scale_factor, color='#8B0000', fontproperties=font_bold, fontweight='bold')
            
            # Separator at bottom of header
            ax.plot([0.5, 9.5], [header_bottom, header_bottom], color=BORDER_COLOR, linewidth=1.5*scale_factor)
            
        elif layout['type'] == 'row':
            board = layout['board']
            items = layout['items']
            col_limit = 5 if board == 1 else 4
            
            # Row occupies [cursor_y, cursor_y + h]
            row_top = cursor_y + h
            row_bottom = cursor_y
            
            # Side Label
            rect = patches.Rectangle((0.5, row_bottom), 1.5, h, linewidth=1.5*scale_factor, edgecolor=BORDER_COLOR, facecolor=BOX_BG)
            ax.add_patch(rect)
            
            label_txt = "首 板" if board == 1 else f"{board} 板"
            if board == 1: label_txt += f"\n({layout['total_count']})"
            
            ax.text(1.25, (row_top + row_bottom)/2, label_txt, 
                    ha='center', va='center', fontsize=22*scale_factor, fontproperties=font_bold, color=TEXT_COLOR, fontweight='bold')
            
            # Items
            left_margin = 2.2
            right_margin = 0.5
            area_width = FIG_W - left_margin - right_margin
            cell_w = area_width / col_limit
            
            # Effective cell height based on number of rows
            rows_num = math.ceil(len(items) / col_limit)
            eff_cell_h = h / max(1, rows_num)
            
            items.sort(key=lambda x: (x['status']!='success', x['time']))
            
            for i, item in enumerate(items):
                c = i % col_limit
                r = i // col_limit
                
                cx = left_margin + c * cell_w + cell_w/2
                cy = row_top - r * eff_cell_h - eff_cell_h/2
                
                name_color = TEXT_COLOR
                if item['status'] != 'success': name_color = '#696969' 
                
                time_txt = item['time']
                time_color = '#333333'
                
                # Scaled Font Sizes - larger and bolder
                fs_name = (18 if board == 1 else 22) * scale_factor
                fs_time = (12 if board == 1 else 14) * scale_factor
                fs_ind = (12 if board == 1 else 15) * scale_factor
                
                # Offsets for text positioning within cell - tighter
                off_time = 0.2 * scale_factor if board == 1 else 0.4 * scale_factor
                off_name = 0.0 if board == 1 else 0.05 * scale_factor
                off_ind = -0.25 * scale_factor if board == 1 else -0.35 * scale_factor
                
                if item.get('is_yizi', False) or time_txt == '一字':
                     bbox_props = dict(boxstyle="square,pad=0.2", fc="#D32F2F", ec="none")
                     ax.text(cx, cy+off_time, "一字", ha='center', va='center', fontsize=fs_time, color='white', fontproperties=font_bold, bbox=bbox_props)
                else:
                     ax.text(cx, cy+off_time, time_txt, ha='center', va='center', fontsize=fs_time, color=time_color, fontproperties=font_bold)
                
                ax.text(cx, cy+off_name, item['name'], ha='center', va='center', fontsize=fs_name, color=name_color, fontproperties=font_bold, fontweight='bold')
                ax.text(cx, cy+off_ind, item['industry'], ha='center', va='center', fontsize=fs_ind, color='#B22222', fontproperties=font_bold)
                
                # Strikethrough for failed stocks
                if item['status'] != 'success':
                     st_y = cy + (-0.05 * scale_factor if board == 1 else 0.1 * scale_factor)
                     ax.plot([cx-0.4, cx+0.4], [st_y, st_y], color='red', linewidth=1.5*scale_factor, alpha=0.8)

            # Row Separator at bottom
            ax.plot([0.5, 9.5], [row_bottom, row_bottom], color=BORDER_COLOR, linewidth=1.5*scale_factor)
            # Right border for content area
            ax.plot([9.5, 9.5], [row_bottom, row_top], color=BORDER_COLOR, linewidth=1.5*scale_factor)
    
    # Add top border for the table
    ax.plot([0.5, 9.5], [FIG_H - header_h * scale_factor, FIG_H - header_h * scale_factor], color=BORDER_COLOR, linewidth=1.5*scale_factor)
    # Add left border for entire table
    ax.plot([0.5, 0.5], [cursor_y, FIG_H - header_h * scale_factor], color=BORDER_COLOR, linewidth=1.5*scale_factor)
    # Add right border for entire table  
    ax.plot([9.5, 9.5], [cursor_y, FIG_H - header_h * scale_factor], color=BORDER_COLOR, linewidth=1.5*scale_factor)
    
    # Remove bbox_inches='tight' to respect exact figsize
    plt.savefig(filename, dpi=200)
    print(f"Beautified ladder saved to {filename} (10:16 Ratio)")
    
if __name__ == "__main__":
    date_str = datetime.now().strftime('%Y%m%d')
    # date_str = "20260119" # Test
    df_zt, df_fried, df_prev = get_limit_up_data(date_str)
    
    if df_zt is not None:
        df_zt = repair_board_counts(df_zt, date_str)
        ladder = process_ladder_data(df_zt, df_fried, df_prev)
        draw_ladder_image(ladder, date_str)
