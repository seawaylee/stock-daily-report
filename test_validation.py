"""
批量测试选股 - 验证与东方财富客户端选股结果是否一致
"""
import sys
sys.path.insert(0, '.')

from data_fetcher import get_stock_data
from signals import check_stock_signal
import time

# 用户通过东方财富客户端选出的股票（2026-01-17）
test_stocks = [
    '000039', '000061', '000301', '000407', '000423', '000592', 
    '000811', '000816', '000881', '000967', '000973', '001212',
    '001229', '001268', '001376', '001389', '002080', '002134',
    '002163', '002209', '002293', '002295', '002347', '002384',
    '002407', '002536', '002539', '002631'
]

print(f"测试 {len(test_stocks)} 只客户端选出的股票...")
print("=" * 70)

matched = []
not_matched = []

for code in test_stocks:
    try:
        df = get_stock_data(code, 300)
        if df is None or len(df) < 60:
            print(f"{code}: 数据不足")
            not_matched.append((code, "数据不足"))
            continue
        
        result = check_stock_signal(df, code)
        
        if result.get('signal'):
            matched.append(code)
            signals_str = ', '.join(result.get('signals', []))
            print(f"✅ {code}: 匹配! 信号: {signals_str}")
        else:
            not_matched.append((code, "未触发信号"))
            # 打印调试信息
            print(f"❌ {code}: 未匹配 (K={result.get('K',0):.1f}, J={result.get('J',0):.1f}, RSI={result.get('RSI',0):.1f})")
        
        time.sleep(0.1)
    except Exception as e:
        print(f"❌ {code}: 错误 - {e}")
        not_matched.append((code, str(e)))

print("=" * 70)
print(f"\n匹配率: {len(matched)}/{len(test_stocks)} ({len(matched)/len(test_stocks)*100:.1f}%)")
print(f"匹配的股票: {matched}")
