
import akshare as ak
import pandas as pd
from datetime import datetime

def check_units():
    date_str = "20260210"
    print(f"Checking data for {date_str}...")

    try:
        # Institutional
        df_inst = ak.stock_lhb_jgmmtj_em(start_date=date_str, end_date=date_str)
        if df_inst is not None and not df_inst.empty:
            print("\n--- Institutional Data (Head) ---")
            # Show Name and Net Buy
            print(df_inst[['名称', '机构买入净额']].head())

            # Check a value
            val = df_inst['机构买入净额'].iloc[0]
            print(f"\nSample '机构买入净额': {val}")
            print(f"If Wan: {val} Wan = {val/10000:.4f} Yi")
            print(f"If Yuan: {val} Yuan = {val/100000000:.8f} Yi")
        else:
            print("No Inst data found.")

        # Active Dept
        df_active = ak.stock_lhb_hyyyb_em(start_date=date_str, end_date=date_str)
        if df_active is not None and not df_active.empty:
            print("\n--- Active Dept Data (Head) ---")
            print(df_active[['营业部名称', '买入总金额']].head())

            val = df_active['买入总金额'].iloc[0]
            print(f"\nSample '买入总金额': {val}")
            print(f"If Wan: {val} Wan = {val/10000:.4f} Yi")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_units()
