"""
股票选股主程序 - 东方财富"知行B1选股专用"策略
"""
import os
import sys
import argparse
import pandas as pd
from datetime import datetime
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

from data_fetcher import get_all_stock_list, get_stock_data
from signals import check_stock_signal


def select_stocks(
    stock_list: pd.DataFrame = None,
    max_workers: int = 4,
    output_dir: str = "results"
) -> pd.DataFrame:
    """
    执行选股
    
    Args:
        stock_list: 股票列表 DataFrame，包含 code, name 列。None 则获取全部A股
        max_workers: 并发线程数
        output_dir: 结果输出目录
    
    Returns:
        选中的股票 DataFrame
    """
    # 获取股票列表
    if stock_list is None:
        print("正在获取A股列表...")
        stock_list = get_all_stock_list()
        print(f"共 {len(stock_list)} 只股票")
    
    codes = stock_list['code'].tolist()
    code_to_name = dict(zip(stock_list['code'], stock_list['name']))
    
    # 选股结果
    selected = []
    errors = []
    
    def process_stock(code: str) -> dict:
        """处理单只股票"""
        try:
            df = get_stock_data(code, 300)
            if df is None or len(df) < 120:
                return None
            
            result = check_stock_signal(df, code)
            result['name'] = code_to_name.get(code, '')
            return result
        except Exception as e:
            return {'code': code, 'error': str(e)}
    
    # 并发处理
    print(f"\n正在分析股票信号 (并发线程: {max_workers})...")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_stock, code): code for code in codes}
        
        for future in tqdm(as_completed(futures), total=len(futures), desc="选股进度"):
            result = future.result()
            if result is None:
                continue
            
            if 'error' in result and result.get('signal') is None:
                errors.append(result)
            elif result.get('signal', False):
                selected.append(result)
    
    # 整理结果
    if selected:
        result_df = pd.DataFrame(selected)
        # 排序和整理列
        cols = ['code', 'name', 'signals', 'close', 'K', 'D', 'J', 'RSI', '近期振幅', '远期振幅']
        cols = [c for c in cols if c in result_df.columns]
        result_df = result_df[cols]
        result_df = result_df.sort_values('code').reset_index(drop=True)
        
        # 保存结果
        os.makedirs(output_dir, exist_ok=True)
        today = datetime.now().strftime('%Y%m%d')
        output_file = os.path.join(output_dir, f"selected_stocks_{today}.csv")
        result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        
        print(f"\n✅ 选股完成！共选出 {len(result_df)} 只股票")
        print(f"📁 结果已保存到: {output_file}")
        
        return result_df
    else:
        print("\n⚠️ 今日无符合条件的股票")
        return pd.DataFrame()


def test_single_stock(code: str):
    """测试单只股票"""
    print(f"正在测试股票: {code}")
    
    df = get_stock_data(code, 300)
    if df is None:
        print(f"❌ 无法获取 {code} 的数据")
        return
    
    print(f"获取到 {len(df)} 条数据")
    print(df.tail(5))
    
    result = check_stock_signal(df, code)
    
    print("\n=== 选股信号分析 ===")
    print(f"股票代码: {result.get('code')}")
    print(f"最新收盘价: {result.get('close', 0):.2f}")
    print(f"K/D/J: {result.get('K', 0):.2f} / {result.get('D', 0):.2f} / {result.get('J', 0):.2f}")
    print(f"RSI: {result.get('RSI', 0):.2f}")
    print(f"近期振幅: {result.get('近期振幅', 0):.2f}%")
    print(f"远期振幅: {result.get('远期振幅', 0):.2f}%")
    print(f"\n是否触发信号: {'✅ 是' if result.get('signal') else '❌ 否'}")
    if result.get('signals'):
        print(f"触发的信号类型: {', '.join(result.get('signals', []))}")


def main():
    parser = argparse.ArgumentParser(description='东方财富知行B1选股策略')
    parser.add_argument('--test-single', type=str, help='测试单只股票，输入股票代码')
    parser.add_argument('--workers', type=int, default=4, help='并发线程数 (默认: 4)')
    parser.add_argument('--output', type=str, default='results', help='结果输出目录')
    
    args = parser.parse_args()
    
    if args.test_single:
        test_single_stock(args.test_single)
    else:
        print("=" * 50)
        print("  东方财富 - 知行B1选股策略")
        print("=" * 50)
        result = select_stocks(max_workers=args.workers, output_dir=args.output)
        
        if len(result) > 0:
            print("\n=== 选股结果预览 ===")
            pd.set_option('display.max_columns', None)
            pd.set_option('display.width', None)
            print(result.head(20).to_string(index=False))


if __name__ == "__main__":
    main()
