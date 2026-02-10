
import akshare as ak
import pandas as pd
from datetime import datetime

def check_cols():
    date_str = "20260210"
    try:
        df_active = ak.stock_lhb_hyyyb_em(start_date=date_str, end_date=date_str)
        if df_active is not None and not df_active.empty:
            print("Columns:", df_active.columns.tolist())
            print(df_active.head(2))
    except Exception as e:
        print(e)

if __name__ == "__main__":
    check_cols()
