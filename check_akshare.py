import akshare as ak
import pandas as pd
from datetime import datetime

today = datetime.now().strftime("%Y%m%d")
print(f"Checking Akshare LHB data for date: {today} (or recent)")

try:
    # Try to get daily LHB list
    # Documentation often refers to stock_lhb_detail_em or similar for EastMoney
    print("Fetching stock_lhb_detail_daily_sina...")
    df_sina = ak.stock_lhb_detail_daily_sina(date=today)
    if not df_sina.empty:
        print(f"Sina LHB Data Found: {len(df_sina)} rows")
        print(df_sina.head(2))
    else:
        print("Sina LHB Data Empty (might be too early or weekend)")

    # Fallback to recent date if today is empty (for testing)
    # let's try a known past trading day if today is empty, but for now just check function existence
except Exception as e:
    print(f"Error fetching Sina LHB: {e}")

try:
    print("\nChecking available attributes for 'stock_lhb'...")
    lhb_funcs = [f for f in dir(ak) if 'lhb' in f]
    print(f"Found {len(lhb_funcs)} LHB related functions.")
    print(lhb_funcs[:5]) # List first 5
except Exception as e:
    print(f"Error listing attributes: {e}")
