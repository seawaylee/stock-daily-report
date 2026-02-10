import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

def check_data():
    today = "20260210"
    print(f"Checking data for date: {today}")

    # 1. Institutional Seats (jgmmtj)
    print("\n--- 1. stock_lhb_jgmmtj_em ---")
    try:
        # Correcting argument to use start_date and end_date
        df_jg = ak.stock_lhb_jgmmtj_em(start_date=today, end_date=today)
        if df_jg is not None and not df_jg.empty:
            print("Columns:", df_jg.columns.tolist())
            print(df_jg.head())
        else:
            print("No data returned for this date.")
    except Exception as e:
        print(f"Error: {e}")

    # 2. Active Business Depts (hyyyb)
    print("\n--- 2. stock_lhb_hyyyb_em ---")
    try:
        # Correcting argument to use start_date and end_date
        df_hy = ak.stock_lhb_hyyyb_em(start_date=today, end_date=today)
        if df_hy is not None and not df_hy.empty:
            print("Columns:", df_hy.columns.tolist())
            print(df_hy.head())
        else:
            print("No data returned for this date.")
    except Exception as e:
        print(f"Error: {e}")

    # 3. Sector Fund Flow
    print("\n--- 3. stock_sector_fund_flow_rank ---")
    try:
        # Trying stock_sector_fund_flow_rank as requested, usually it returns current data
        df_flow = ak.stock_sector_fund_flow_rank()
        if df_flow is not None and not df_flow.empty:
            print("Columns:", df_flow.columns.tolist())
            print(df_flow.head())
        else:
            print("No data returned.")
    except Exception as e:
        print(f"Error calling stock_sector_fund_flow_rank: {e}")
        # Fallback attempt if name changed or specific params needed
        try:
             print("Trying ak.stock_industry_daily() or similar as fallback if needed...")
        except:
             pass

if __name__ == "__main__":
    check_data()
