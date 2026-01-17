"""
全市场选股 - 高并发版本 (200线程)
市值100亿以上，排除ST
"""
import sys
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_fetcher import get_all_stock_list, get_stock_data
from signals import check_stock_signal
from tqdm import tqdm
import pandas as pd

# 并发线程数
MAX_WORKERS = 200


def process_single_stock(args):
    """处理单只股票"""
    code, name, market_cap = args
    try:
        df = get_stock_data(code, 300)
        if df is None or len(df) < 120:
            return None
        
        result = check_stock_signal(df, code)
        
        if result.get('signal'):
            result['name'] = name
            result['market_cap'] = market_cap
            return result
        return None
    except Exception as e:
        return None


def run_full_market_selection():
    print("=" * 60)
    print("  东方财富 - 知行B1选股策略 (高并发版本)")
    print(f"  市值 >= 100亿 | 排除ST | 并发线程: {MAX_WORKERS}")
    print(f"  执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 获取股票列表（市值100亿+，排除ST）
    print("\n[1/3] 获取股票列表...")
    stock_list = get_all_stock_list(min_market_cap=100, exclude_st=True)
    
    if len(stock_list) == 0:
        print("❌ 无法获取股票列表")
        return
    
    # 准备参数列表
    args_list = [
        (row['code'], row['name'], row['market_cap']) 
        for _, row in stock_list.iterrows()
    ]
    
    print(f"\n[2/3] 并发分析 {len(args_list)} 只股票的信号...")
    
    selected = []
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_single_stock, args): args[0] for args in args_list}
        
        for future in tqdm(as_completed(futures), total=len(futures), desc="选股进度"):
            result = future.result()
            if result is not None:
                selected.append(result)
    
    print("\n" + "=" * 60)
    print(f"[3/3] 选股完成！共选出 {len(selected)} 只股票")
    print("=" * 60)
    
    if selected:
        # 整理结果
        result_df = pd.DataFrame(selected)
        cols = ['code', 'name', 'market_cap', 'signals', 'close', 'K', 'D', 'J', 'RSI']
        cols = [c for c in cols if c in result_df.columns]
        result_df = result_df[cols]
        result_df = result_df.sort_values('market_cap', ascending=False).reset_index(drop=True)
        
        # 保存结果
        os.makedirs('results', exist_ok=True)
        today = datetime.now().strftime('%Y%m%d')
        output_file = f"results/selected_stocks_{today}.csv"
        result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        print(f"\n📁 结果已保存到: {output_file}")
        
        # 显示结果
        print("\n=== 选股结果 ===")
        for i, row in result_df.iterrows():
            signals_str = ', '.join(row['signals']) if isinstance(row['signals'], list) else row['signals']
            print(f"{row['code']} {row['name']:8s} | 市值:{row['market_cap']:.0f}亿 | 信号: {signals_str}")
        
        return result_df
    else:
        print("\n⚠️ 今日无符合条件的股票")
        return pd.DataFrame()


if __name__ == "__main__":
    run_full_market_selection()
