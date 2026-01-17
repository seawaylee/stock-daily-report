"""
测试版选股 - 选出10只就停止，并保存原始数据
"""
import sys
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class NumpyEncoder(json.JSONEncoder):
    """处理numpy类型的JSON编码器"""
    def default(self, obj):
        if isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        if isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)

from data_fetcher import get_all_stock_list, get_stock_data
from signals import check_stock_signal
from tqdm import tqdm
import pandas as pd

# 配置
MAX_WORKERS = 100
TARGET_COUNT = 10  # 选出10只就停止


def process_single_stock(args):
    """处理单只股票，返回原始数据和信号结果"""
    code, name, market_cap = args
    try:
        df = get_stock_data(code, 300)
        if df is None or len(df) < 120:
            return None
        
        result = check_stock_signal(df, code)
        
        # 获取最后一行原始数据
        last_row = df.iloc[-1].to_dict()
        last_row['date'] = str(last_row['date'])[:10]  # 转换日期格式
        
        return {
            'code': code,
            'name': name,
            'market_cap': market_cap,
            'signal': result.get('signal', False),
            'signals': result.get('signals', []),
            'K': result.get('K', 0),
            'D': result.get('D', 0),
            'J': result.get('J', 0),
            'RSI': result.get('RSI', 0),
            'raw_data': last_row  # 原始数据
        }
    except Exception as e:
        return None


def run_test_selection():
    print("=" * 60)
    print("  测试版选股 - 选出10只就停止")
    print(f"  市值 >= 100亿 | 排除ST | 并发线程: {MAX_WORKERS}")
    print(f"  执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 获取股票列表
    print("\n[1/3] 获取股票列表...")
    stock_list = get_all_stock_list(min_market_cap=100, exclude_st=True)
    
    if len(stock_list) == 0:
        print("❌ 无法获取股票列表")
        return
    
    args_list = [
        (row['code'], row['name'], row['market_cap']) 
        for _, row in stock_list.iterrows()
    ]
    
    print(f"\n[2/3] 分析股票信号 (目标: 选出{TARGET_COUNT}只)...")
    
    selected = []
    all_results = []  # 保存所有处理过的股票数据
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_single_stock, args): args[0] for args in args_list}
        
        pbar = tqdm(total=len(futures), desc="选股进度")
        for future in as_completed(futures):
            result = future.result()
            pbar.update(1)
            
            if result is not None:
                all_results.append(result)
                
                if result['signal']:
                    selected.append(result)
                    print(f"\n✅ 找到第{len(selected)}只: {result['code']} {result['name']}")
                    
                    if len(selected) >= TARGET_COUNT:
                        print(f"\n🎯 已选出{TARGET_COUNT}只，停止扫描!")
                        executor.shutdown(wait=False, cancel_futures=True)
                        break
        pbar.close()
    
    # 保存原始数据到本地
    os.makedirs('results', exist_ok=True)
    today = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 保存所有处理过的股票原始数据（一行一个）
    raw_data_file = f"results/raw_data_{today}.jsonl"
    with open(raw_data_file, 'w', encoding='utf-8') as f:
        for item in all_results:
            f.write(json.dumps(item, ensure_ascii=False, cls=NumpyEncoder) + '\n')
    print(f"\n📁 原始数据已保存到: {raw_data_file} ({len(all_results)} 条)")
    
    # 保存选中的股票
    if selected:
        print("\n" + "=" * 60)
        print(f"[3/3] 选股完成！共选出 {len(selected)} 只股票")
        print("=" * 60)
        
        print("\n=== 选股结果 ===")
        for item in selected:
            signals_str = ', '.join(item['signals'])
            raw = item['raw_data']
            print(f"{item['code']} {item['name']:8s} | 市值:{item['market_cap']:.0f}亿 | 信号: {signals_str}")
            print(f"    原始数据: 日期={raw['date']} 开={raw['open']:.2f} 高={raw['high']:.2f} 低={raw['low']:.2f} 收={raw['close']:.2f} 量={raw['volume']}")
        
        # 保存选股结果
        selected_file = f"results/selected_{today}.json"
        with open(selected_file, 'w', encoding='utf-8') as f:
            json.dump(selected, f, ensure_ascii=False, indent=2, cls=NumpyEncoder)
        print(f"\n📁 选股结果已保存到: {selected_file}")
    else:
        print("\n⚠️ 暂未选出符合条件的股票")


if __name__ == "__main__":
    run_test_selection()
