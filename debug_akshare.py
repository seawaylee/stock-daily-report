
import akshare as ak
import pandas as pd

def debug_akshare_data():
    print(f"Akshare version: {ak.__version__}")
    print("Fetching stock spot data...")
    try:
        df = ak.stock_zh_a_spot_em()
        print(f"Total rows fetched: {len(df)}")
        print("Columns:", df.columns.tolist())
        
        # Check Fenglong (002931)
        fl = df[df['名称'].str.contains('锋龙')]
        if not fl.empty:
            print("\nFenglong Raw Data:")
            print(fl.T)
            
            raw_mc = fl.iloc[0]['总市值']
            print(f"\nRaw Market Cap Value: {raw_mc} (Type: {type(raw_mc)})")
            
            # Check a big bank for comparison (e.g. ICBC 601398)
            icbc = df[df['代码'] == '601398']
            if not icbc.empty:
                print("\nICBC Raw Market Cap:")
                print(icbc.iloc[0]['总市值'])
        else:
            print("Fenglong not found")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_akshare_data()
