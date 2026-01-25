
"""
Earnings Analysis Module Entry Point
"""
import os
from datetime import datetime, timedelta
from modules.earnings import data, analysis, excel_export, generate_performance_prompt

def run_prompt_gen(date_str, output_dir):
    return generate_performance_prompt.run(date_str, output_dir)

def run(date_str, output_dir):
    """
    Run Earnings Analysis.
    Target: Find stocks disclosing earnings in the target week.
    Default: If date_str is provided, look at that week (Mon-Sun).
    """
    print(f"🚀 Starting Earnings Analysis for {date_str}...")
    
    # 1. Determine Date Range
    try:
        if date_str:
            target_date = datetime.strptime(date_str, '%Y%m%d')
        else:
            target_date = datetime.now()
            
        # Strategy: Get the ISO Week of the target date
        # Start = Monday of that week
        # End = Sunday of that week
        
        # Adjust: If today is Sunday, maybe user wants NEXT week?
        # User said "本周" (This Week). 
        # But if running on Sunday for a report?
        # Let's just default to the week containing target_date.
        
        start_of_week = target_date - timedelta(days=target_date.weekday()) # Monday
        end_of_week = start_of_week + timedelta(days=6) # Sunday
        
        s_date_str = start_of_week.strftime('%Y%m%d')
        e_date_str = end_of_week.strftime('%Y%m%d')
        
        print(f"📅 Target Week: {s_date_str} - {e_date_str}")
        
    except Exception as e:
        print(f"Date Error: {e}")
        return False

    # 2. Fetch Data
    
    # List A: Formal Schedule (Stocks officially releasing Annual Report)
    schedule_df = data.fetch_disclosure_schedule(s_date_str, e_date_str)
    if not schedule_df.empty:
        schedule_df['source_type'] = '正式披露'
        
    # List B: Forecasts Announced in this range (Stocks releasing Forecasts)
    forecast_announce_df = data.fetch_earnings_forecast_by_date(s_date_str, e_date_str)
    if not forecast_announce_df.empty:
        forecast_announce_df['source_type'] = '业绩预告'
        forecast_announce_df['实际披露时间'] = forecast_announce_df['disclosure_date'] # Map date
        
        # Forecast DF already has the forecast columns. 
        # Schedule DF needs to Merge with Forecast Content Database to get details.
        
    # 3. Consolidate
    # Strategy:
    # - If we have Schedule Items, we still need to fetch their Forecast DETAILS (from the big forecast table)
    # - If we have Forecast Announcements, they HAVE details.
    
    # 3.1 Get FULL Forecast Database (for lookups)
    full_forecast_db = data.fetch_earnings_forecast()
    
    # 3.2 Enrich Schedule DF
    final_list = []
    
    if not schedule_df.empty:
        # Merge Forecast Details into Schedule
        enriched_schedule = data.merge_data(schedule_df, full_forecast_db)
        final_list.append(enriched_schedule)
        
    if not forecast_announce_df.empty:
        # forecast_announce_df ALREADY has '业绩变动', '预告类型' etc. from akshare
        # Just ensure columns match `enriched_schedule` for concatenation
        # Enrich just in case fields are missing? No, stock_yjyg_em has them.
        final_list.append(forecast_announce_df)
        
    if not final_list:
        print("⚠️ No disclosures or forecasts found for this period.")
        return True
        
    # Concatenate
    import pandas as pd
    combined_df = pd.concat(final_list, ignore_index=True)
    
    # Deduplicate (If a stock is both scheduled and announced forecast same day? Unlikely, but possible)
    combined_df = combined_df.drop_duplicates(subset=['股票代码', 'source_type'])
    
    # 4. Analyze
    print(f"🧠 Analyzing {len(combined_df)} items...")
    final_df = analysis.analyze_df(combined_df)
    
    # 5. Export
    output_filename = f"earnings_weekly_preview_{s_date_str}.xlsx"
    output_path = os.path.join(output_dir, output_filename)
    
    print(f"💾 Exporting to {output_path}...")
    if excel_export.export_earnings_excel(final_df, output_path):
        print("✅ Earnings Analysis Completed Successfully.")
        return True
    else:
        print("❌ Export Failed.")
        return False
