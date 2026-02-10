
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta

def test_dragon(date_str):
    print(f"Testing for date: {date_str}")
    try:
        print("Fetching Institutional...")
        df_inst = ak.stock_lhb_jgmmtj_em(start_date=date_str, end_date=date_str)
        print("Inst Data:")
        print(df_inst.head() if df_inst is not None else "None")
    except Exception as e:
        print(f"Inst Failed: {e}")

    try:
        print("Fetching Active Depts...")
        df_active = ak.stock_lhb_hyyyb_em(start_date=date_str, end_date=date_str)
        print("Active Data:")
        print(df_active.head() if df_active is not None else "None")
    except Exception as e:
        print(f"Active Failed: {e}")

# Try yesterday
yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
test_dragon(yesterday)

# Try today (might fail if morning)
today = datetime.now().strftime('%Y%m%d')
test_dragon(today)
