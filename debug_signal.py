"""
调试脚本 - 查看具体错误
"""
import traceback
from data_fetcher import get_stock_data
from signals import StockSignals

code = '000039'
print(f"获取 {code} 数据...")
df = get_stock_data(code, 300)

if df is None:
    print("数据获取失败")
else:
    print(f"数据行数: {len(df)}")
    print(df.tail(3))
    print("\n计算信号...")
    
    try:
        s = StockSignals(df, code)
        result = s.get_latest_signal()
        print("\n信号结果:")
        for k, v in result.items():
            print(f"  {k}: {v}")
    except Exception as e:
        print(f"\n错误: {e}")
        traceback.print_exc()
