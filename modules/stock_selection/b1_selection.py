"""
全市场选股 + AI智能分析生成报告
1. 300并发全市场选股（市值100亿+，排除ST）
2. 接入Gemini分析Top10值博率
3. 生成推荐原因MD文档
4. 生成小红书文案（脱敏处理）
"""
import sys
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import requests
import base64
import time
import numpy as np
from tqdm import tqdm

# 导入配置和Prompt模块
from common.config import MAX_WORKERS, MIN_MARKET_CAP
from common.prompts import (
    NumpyEncoder, 
    get_analysis_prompt, 
    get_xiaohongshu_prompt, 
    get_image_prompt
)

# 导入数据获取和信号检测模块

# 导入数据获取和信号检测模块
from common.data_fetcher import get_all_stock_list, get_stock_data
from common.signals import check_stock_signal
# from modules.daily_report.sector_flow import run_daily_analysis (Refactored)
# from modules.daily_report.generate_ladder_prompt import generate_ladder_prompt (Refactored)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def process_single_stock(args):
    """处理单只股票"""
    code, name, market_cap, industry = args
    try:
        df = get_stock_data(code, 300)
        if df is None or len(df) < 120:
            return None
        
        result = check_stock_signal(df, code)
        
        # 获取最后一行原始数据
        last_row = df.iloc[-1].to_dict()
        last_row['date'] = str(last_row['date'])[:10]
        
        return {
            'code': code,
            'name': name,
            'market_cap': float(market_cap),
            'industry': industry if str(industry).lower() != 'nan' else None,  # 题材/行业
            'signal': bool(result.get('signal', False)),
            'signals': result.get('signals', []),
            'K': float(result.get('K', 0)),
            'D': float(result.get('D', 0)),
            'J': float(result.get('J', 0)),
            'RSI': float(result.get('RSI', 0)),
            'near_amplitude': float(result.get('近期振幅', 0)),
            'far_amplitude': float(result.get('远期振幅', 0)),
            'raw_data_mock': last_row
        }
    except Exception as e:
        return None


def run_full_selection(force=False):
    """全市场选股
    
    Args:
        force: 是否强制重新选股，忽略今日已有结果
    """
    today_date = datetime.now().strftime('%Y%m%d')
    date_dir = os.path.join("results", today_date)
    os.makedirs(date_dir, exist_ok=True)
    
    # 检查是否已有今日结果
    if not force:
        import glob
        existing_files = glob.glob(os.path.join(date_dir, f"selected_{today_date}_*.json")) 
        if existing_files:
            latest_file = max(existing_files, key=os.path.getctime)
            print(f"⚡ 发现今日已有选股结果: {latest_file}")
            with open(latest_file, 'r', encoding='utf-8') as f:
                selected = json.load(f)
            # 从文件名提取完整时间戳 (selected_YYYYMMDD_HHMMSS.json)
            filename = os.path.basename(latest_file)
            # filename格式: selected_20260118_004725.json
            # 去掉前缀 selected_ (9 chars) 和后缀 .json (5 chars)
            timestamp = filename[9:-5] 
            return selected, timestamp
    else:
        print("🔄 --force 模式：忽略今日缓存，强制重新选股")

    print("=" * 70)
    print("  东方财富 - 知行B1选股策略 (AI智能分析版)")
    print(f"  市值 >= {MIN_MARKET_CAP}亿 | 排除ST | 并发线程: {MAX_WORKERS}")
    print(f"  执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # 获取股票列表
    print("\n[1/4] 获取股票列表...")
    stock_list = get_all_stock_list(min_market_cap=MIN_MARKET_CAP, exclude_st=True)
    
    # 注释：移除500只股票限制，分析全部股票
    # stock_list = stock_list.head(500)
    print(f"⚠️ 将分析全部 {len(stock_list)} 只股票")
    
    if len(stock_list) == 0:
        print("❌ 无法获取股票列表")
        return [], ""
    
    args_list = [
        (row['code'], row['name'], row['market_cap'], row.get('industry', '')) 
        for _, row in stock_list.iterrows()
    ]
    
    print(f"\n[2/4] 并发分析 {len(args_list)} 只股票的信号...")
    
    selected = []
    all_results = []
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_single_stock, args): args[0] for args in args_list}
        
        for future in tqdm(as_completed(futures), total=len(futures), desc="选股进度"):
            result = future.result()
            if result is not None:
                all_results.append(result)
                if result['signal']:
                    selected.append(result)
    
    # 保存结果
    today_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 保存所有原始数据
    raw_file = os.path.join(date_dir, f"all_stocks_{today_timestamp}.jsonl")
    with open(raw_file, 'w', encoding='utf-8') as f:
        for item in all_results:
            f.write(json.dumps(item, cls=NumpyEncoder, ensure_ascii=False) + '\n')
    
    print(f"\n📁 原始数据: {raw_file} ({len(all_results)} 条)")
    
    # 保存选股结果
    selected_file = os.path.join(date_dir, f"selected_{today_timestamp}.json")
    with open(selected_file, 'w', encoding='utf-8') as f:
        json.dump(selected, f, cls=NumpyEncoder, ensure_ascii=False, indent=2)
            
    print(f"📁 选股结果: {selected_file} ({len(selected)} 只)")
    
    return selected, today_timestamp


def save_stock_summary(selected_stocks, date_dir, timestamp):
    """保存便于私信发送的文本汇总"""
    summary_file = os.path.join(date_dir, f"stock_list_summary_{timestamp}.txt")
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write(f"📅 选股汇总 {datetime.now().strftime('%Y-%m-%d')}\n")
        f.write(f"策略: AI大模型量化\n")
        f.write("-" * 30 + "\n\n")
        
        for idx, stock in enumerate(selected_stocks, 1):
            code = stock['code']
            name = stock['name']
            industry = stock.get('industry', '未知行业')
            
            f.write(f"{idx}. {name} ({code})\n")
            if industry and str(industry).lower() != 'nan':
                f.write(f"   行业: {industry}\n")
            # 获取信号列表
            stock_signals = stock.get('signals', [])
            
            if stock_signals:
                # 统一术语
                sanitized_signals = [
                    s.replace('B1', '买点')
                     .replace('B', '买点')
                     .replace('原始', '标准')
                    for s in stock_signals
                ]
                f.write(f"   命中规则: {'+'.join(sanitized_signals)}\n")
            
            f.write("\n")
            
        f.write("-" * 30 + "\n")
        f.write("注：次日关注进场，非投资建议。\n")
        f.write("更多详情请看文案分析。\n")

    print(f"📁 私信汇总列表: {summary_file}")
    return summary_file

# 注释：save_stock_summary 功能已移至 agent_outputs/result_analysis.txt
# 此函数保留但不再调用

# ================ 脱敏工具函数 ================

def desensitize_stock_name(name):
    """股票名称脱敏：保留前2字，后面改为拼音首字母大写"""
    if len(name) <= 2:
        return name
    
    try:
        from pypinyin import lazy_pinyin, Style
        # 获取后缀的拼音首字母
        suffix = name[2:]
        pinyin_initials = lazy_pinyin(suffix, style=Style.FIRST_LETTER)
        # 转大写并拼接
        initials = ''.join([p.upper() for p in pinyin_initials])
        return name[:2] + initials
    except ImportError:
        # 如果没有安装 pypinyin，使用简化逻辑
        print("Warning: pypinyin not installed. Using simplified desensitization.")
        suffix = name[2:]
        # 取后缀前两个字符作为标识
        return name[:2] + (suffix[:2].upper() if len(suffix) >= 2 else suffix.upper())

def desensitize_stock_code(code):
    """股票代码脱敏：前4位保留，后2位改为**"""
    if len(code) < 6:
        return code
    return code[:4] + '**'



def call_gemini_analysis(selected_stocks, date_dir):
    """使用Agent分析Top10值博率"""
    # 准备分析数据
    stocks_info = []
    for s in selected_stocks:
        raw = s['raw_data_mock']
        stocks_info.append({
            '代码': s['code'],
            '名称': s['name'],
            '总市值(亿元)': round(s['market_cap'], 0),
            '信号类型': ', '.join(s['signals']),
            'K': round(s['K'], 1),
            'D': round(s['D'], 1),
            'J': round(s['J'], 1),
            'RSI': round(s['RSI'], 1),
            '近期振幅%': round(s['near_amplitude'], 1),
            '远期振幅%': round(s['far_amplitude'], 1),
            '收盘价': raw['close'],
            '成交量': raw['volume']
        })
    
    prompt = get_analysis_prompt(stocks_info)

    # 保存任务到文件供Agent处理
    agent_task_dir = os.path.join(date_dir, "agent_tasks")
    os.makedirs(agent_task_dir, exist_ok=True)
    
    task_file = os.path.join(agent_task_dir, "task_analysis.txt")
    with open(task_file, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    print(f"\n[4/4] 任务已保存，等待Agent分析Top10...")
    print(f"📝 任务文件: {task_file}")
    
    # 读取Agent生成的结果
    agent_output_dir = os.path.join(date_dir, "agent_outputs")
    output_file = os.path.join(agent_output_dir, "result_analysis.txt")
    
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            result = f.read()
        print("✅ Agent分析完成")
        
        # --- 提取并保存 Top 10 ---
        import re
        top_codes = re.findall(r'\((\d{6})\)', result)
        seen = set()
        unique_codes = []
        for c in top_codes:
            if c not in seen:
                unique_codes.append(c)
                seen.add(c)
        unique_codes = unique_codes[:10]
        
        stock_map = {s['code']: s for s in selected_stocks}
        top_stocks = []
        for c in unique_codes:
            if c in stock_map:
                top_stocks.append(stock_map[c])
        
        top10_file = os.path.join(date_dir, "selected_top10.json")
        with open(top10_file, 'w', encoding='utf-8') as f:
            json.dump(top_stocks, f, cls=NumpyEncoder, ensure_ascii=False, indent=2)
        print(f"📁 已生成中间文件: {top10_file} ({len(top_stocks)}只)")
        
        return result, prompt
    else:
        print(f"⚠️  等待Agent生成结果: {output_file}")
        print("提示：请运行 Agent 工作流来处理分析任务")
        return None, prompt


def generate_xiaohongshu_post(gemini_analysis, selected_stocks, date_dir):
    """使用Agent生成小红书文案（脱敏处理）"""
    # 准备脱敏后的股票列表
    masked_stocks = []
    for s in selected_stocks:
        masked_stocks.append({
            'name': s['name'],
            'name_masked': desensitize_stock_name(s['name']),
            'code': s['code'],
            'code_masked': desensitize_stock_code(s['code']),
            'industry': s.get('industry', ''),
        })
    
    # 准备脱敏说明
    prompt = get_xiaohongshu_prompt(
        gemini_analysis, 
        json.dumps(masked_stocks, ensure_ascii=False, indent=2), 
        datetime.now().strftime('%Y-%m-%d')
    )

    # 保存任务到文件供Agent处理
    agent_task_dir = os.path.join(date_dir, "agent_tasks")
    os.makedirs(agent_task_dir, exist_ok=True)
    
    task_file = os.path.join(agent_task_dir, "task_xiaohongshu.txt")
    with open(task_file, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    print(f"📝 小红书任务已保存: {task_file}")
    
    # 读取Agent生成的结果
    agent_output_dir = os.path.join(date_dir, "agent_outputs")
    output_file = os.path.join(agent_output_dir, "result_xiaohongshu.txt")
    
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            result = f.read()
        print("✅ 小红书文案生成完成")
        return result, prompt
    else:
        print(f"⚠️  等待Agent生成结果: {output_file}")
        return None, prompt


def generate_image_prompt(gemini_analysis, selected_stocks, date_dir):
    """使用Agent生成信息图提示词"""
    # 准备股票数据摘要(包含技术指标 + 脱敏信息)
    # 准备股票数据摘要(包含技术指标 + 脱敏信息)
    if len(selected_stocks) > 10:
        print(f"⚠️ 警告: 传入图片生成的股票数量为 {len(selected_stocks)}，预期为10。")
        # 尝试使用前10个
        selected_stocks = selected_stocks[:10]

    # 准备股票数据摘要(包含技术指标 + 脱敏信息)
    stock_summary = []
    for s in selected_stocks:
        stock_summary.append({
            'name': s['name'],
            'name_masked': s.get('name_masked', desensitize_stock_name(s['name'])),  # 优先使用已有脱敏名
            'code': s['code'],
            'code_masked': s.get('code_masked', desensitize_stock_code(s['code'])),  # 优先使用已有脱敏代码
            'industry': s.get('industry', '未知'),
            'signals': ','.join(s.get('signals', [])).replace('B1','标准买点').replace('B','标准买点').replace('原始买点','标准买点'),
            'J': round(s.get('J', 0), 2),
            'RSI': round(s.get('RSI', 0), 2),
        })
    
    # 从小红书文案提取次日策略
    # 从分析结果提取 "整体市场复盘" 和 "次日交易策略"
    import re
    
    # --- 提取复盘与策略 (优先使用 Step 4 专用摘要) ---
    market_review = "无复盘内容"
    tomorrow_strategy = ""
    
    # 尝试提取 "Step 4: 图片生成专用摘要"
    summary_section_match = re.search(r'图片生成专用摘要\s*(.+)', gemini_analysis, re.DOTALL)
    
    SUMMARY_FOUND = False
    if summary_section_match:
        summary_content = summary_section_match.group(1)
        
        # 提取复盘
        match_rev = re.search(r'📍\s*(.+?)(?=\n\s*💡|$)', summary_content, re.DOTALL)
        if match_rev:
            extracted_rev = match_rev.group(1).strip().replace('**', '').replace('整体复盘', '').strip()
            if extracted_rev:
                market_review = extracted_rev
                SUMMARY_FOUND = True
        
        # 提取策略
        match_str = re.search(r'💡\s*(.+)', summary_content, re.DOTALL)
        if match_str:
            extracted_str = match_str.group(1).strip().replace('**', '').replace('次日策略', '').strip()
            if extracted_str:
                tomorrow_strategy = extracted_str
                SUMMARY_FOUND = True
                
    if not SUMMARY_FOUND:
        print("⚠️ 未找到专用摘要，使用智能提取回退模式...")
        # 回退模式：从正文提取第一段
        match_review = re.search(r'整体市场复盘\s+(.+?)(?=\n\s*次日交易策略|$)', gemini_analysis, re.DOTALL)
        if match_review:
            full_review = match_review.group(1).strip()
            market_review = full_review.split('\n')[0].strip().replace('**', '')

        match_strategy = re.search(r'次日交易策略\s+(.+?)(?=\n\s*风险提示|$)', gemini_analysis, re.DOTALL)
        if match_strategy:
            full_strategy = match_strategy.group(1).strip()
            # 提取 **核心点**
            strategy_points = re.findall(r'\*\*(.*?)\*\*', full_strategy)
            if strategy_points:
                tomorrow_strategy = "、".join(strategy_points[:3])
            else:
                tomorrow_strategy = full_strategy.split('\n')[0].strip().replace('**', '')

    # --- 对复盘和策略文案进行脱敏替换 ---
    # 遍历所有股票，将文案中的"全名"替换为"脱敏名"
    # 按名称长度降序排列，避免短名误伤长名 (e.g. "中航" vs "中航光电")
    sorted_stocks = sorted(selected_stocks, key=lambda x: len(x['name']), reverse=True)
    
    for s in sorted_stocks:
        name = s['name']
        name_masked = s.get('name_masked', desensitize_stock_name(name))
        code = s['code']
        code_masked = s.get('code_masked', desensitize_stock_code(code))
        
        # 替换名称
        if name in market_review:
            market_review = market_review.replace(name, name_masked)
        if name in tomorrow_strategy:
            tomorrow_strategy = tomorrow_strategy.replace(name, name_masked)
        
        # 替换代码 (如果有的话)
        if code in market_review:
            market_review = market_review.replace(code, code_masked)
        if code in tomorrow_strategy:
            tomorrow_strategy = tomorrow_strategy.replace(code, code_masked)

    
    # 构建动态 Footer 内容
    footer_content = ""
    if market_review and market_review != "无复盘内容":
        footer_content += f"📍 整体复盘\n{market_review}\n\n"
    
    if tomorrow_strategy:
        footer_content += f"💡 次日策略\n{tomorrow_strategy}"

    prompt = get_image_prompt(stock_summary, footer_content, datetime.now().strftime('%Y-%m-%d'))

    # 保存任务到文件供Agent处理
    agent_task_dir = os.path.join(date_dir, "agent_tasks")
    os.makedirs(agent_task_dir, exist_ok=True)
    
    task_file = os.path.join(agent_task_dir, "task_image_prompt.txt")
    with open(task_file, 'w', encoding='utf-8') as f:
        f.write(prompt)
    
    print(f"📝 图片生成任务已保存: {task_file}")
    
    # 读取Agent生成的结果
    agent_output_dir = os.path.join(date_dir, "agent_outputs")
    output_file = os.path.join(agent_output_dir, "result_image_prompt.txt")
    
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            final_prompt = f.read()
        final_prompt += "\n\n(Note: This prompt is optimized for the 'Nano Banana Pro3' model. Please ensure all details are consistent with high-quality hand-drawn vector art.)"
        print("✅ 图片提示词生成完成")
        return final_prompt, prompt
    else:
        print(f"⚠️  等待Agent生成结果: {output_file}")
        return None, prompt


def save_reports(gemini_analysis, xiaohongshu_post, today):
    """保存报告（简化版 - 仅保存到agent_outputs）"""
    # 注释：外层重复文件已移除，所有结果集中在 agent_outputs/
    # 此函数保留用于向后兼容，actual saving done in agent workflow
    date_str = today.split('_')[0]
    date_dir = os.path.join("results", date_str)
    
    print(f"� 分析结果已保存到: {date_dir}/agent_outputs/")
    print(f"   - result_analysis.txt")
    print(f"   - result_xiaohongshu.txt")
    print(f"   - result_image_prompt.txt")
    
    return None, None


def save_prompts(prompts_dict, today):
    """保存提示词记录（可选 - 用于调试）"""
    # 注释：此功能可选，提示词已在 agent_tasks/ 中保存
    # 保留此函数用于调试目的
def enrich_stocks_from_analysis(selected_stocks, date_dir):
    """从分析报告回填行业/题材"""
    try:
        print("🔄 正在从分析报告回填 [行业] 和 [脱敏信息]...")
        analysis_file = os.path.join(date_dir, "agent_outputs", "result_analysis.txt")
        if os.path.exists(analysis_file):
            import re
            with open(analysis_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析模式: 1. **中航光电 (002179)** | 军工电子/高端连接器 |
            # 兼容带有 ** 的 markdown 格式
            pattern = re.compile(r'\d+\.\s*(?:\*\*)?(.+?)\s*(?:\*\*)?\s*\((?:\*\*)?(\d{6})(?:\*\*)?\)\s*(?:\*\*)?\s*\|\s*(.+?)\s*\|')
            
            # 构建映射表 code -> industry
            industry_map = {}
            matches = pattern.findall(content)
            for name, code, ind in matches:
                # 清理数据
                clean_name = name.replace('*', '').strip()
                clean_code = code.replace('*', '').strip()
                clean_ind = ind.replace('*', '').strip()
                industry_map[clean_code] = clean_ind
                # print(f"  - 识别到: {clean_code} -> {clean_ind}")

            # 回填到 selected_stocks
            count = 0
            for stock in selected_stocks:
                code = stock['code']
                if code in industry_map:
                    stock['industry'] = industry_map[code]
                    count += 1
            
            print(f"✅ 成功从分析报告回填 {count} 条行业数据")
            
            # 保存回填后的结果到 selected_top10.json
            top10_file = os.path.join(date_dir, "selected_top10.json")
            with open(top10_file, 'w', encoding='utf-8') as f:
                json.dump(selected_stocks, f, cls=NumpyEncoder, ensure_ascii=False, indent=2)
            print(f"💾 已更新 selected_top10.json")
            
            return True
        else:
            print("⚠️ 未找到 result_analysis.txt，无法回填信息")
            return False
    except Exception as e:
        print(f"⚠️ 回填信息出错: {e}") 
        return False





def run(date_dir=None, force=False):
    """
    Main entry point for Daily Stock Selection & AI Analysis.
    
    Args:
        date_dir: 输出目录
        force: 是否强制重新生成，忽略今日缓存
    """
    # 1. 全市场选股
    # DEBUG: Mock selection to test downstream
    # print("⚠️ DEBUG MODE: Using mocked stock list to skip slow selection")
    # today = datetime.now().strftime('%Y%m%d')
    # selected = [
    #     {
    #         'code': 'sz002931', 'name': '锋龙股份', 'price': 10.5, 'reason': 'Debug', 
    #         'market_cap': 20.0, 'signals': ['B1'], 'K': 50, 'D': 50, 'J': 50, 'RSI': 50, 'near_amplitude': 5.0, 'far_amplitude': 10.0,
    #         'raw_data_mock': {'收盘': 10.5, '换手%': 5.0, 'close': 10.5, 'volume': 100000}
    #     },
    #     {
    #         'code': 'sh603078', 'name': '江化微', 'price': 20.0, 'reason': 'Debug', 
    #         'market_cap': 30.0, 'signals': ['B1'], 'K': 60, 'D': 60, 'J': 60, 'RSI': 60, 'near_amplitude': 6.0, 'far_amplitude': 12.0,
    #         'raw_data_mock': {'收盘': 20.0, '换手%': 3.2, 'close': 20.0, 'volume': 200000}
    #     },
    #     {
    #         'code': 'sz000063', 'name': '中兴通讯', 'price': 30.0, 'reason': 'Debug',
    #         'market_cap': 1000.0, 'signals': ['B1'], 'K': 70, 'D': 70, 'J': 70, 'RSI': 70, 'near_amplitude': 3.0, 'far_amplitude': 8.0,
    #         'raw_data_mock': {'收盘': 30.0, '换手%': 2.1, 'close': 30.0, 'volume': 500000}
    #     }
    # ]
    selected, today = run_full_selection(force=force)
    
    # 确保日期文件夹存在
    date_str = today.split('_')[0]
    
    # Use passed in date_dir if provided, otherwise default
    if not date_dir:
        date_dir = os.path.join("results", date_str)
        
    os.makedirs(date_dir, exist_ok=True)
    
    gemini_analysis = None
    xiaohongshu_post = None
    
    # 4. 调用AI分析 (仅当有选股时)
    if not selected:
        print("❌ 没有选出股票，跳过 B1 AI 分析，继续执行其他模块...")
        return False
    else:
        try:
            # 传入所有选中的股票供Agent分析
            # Agent会从中选出Top10进行深度分析
            all_stocks = selected
            
            # 调用Agent分析（传入全部候选）
            gemini_analysis, analysis_prompt = call_gemini_analysis(all_stocks, date_dir)
            
            # 如果Agent还未生成结果，等待用户运行工作流
            if gemini_analysis is None:
                print("\n⏸️  脚本暂停：等待Agent工作流处理任务")
                print("请运行 Agent 工作流完成分析，然后再次执行此脚本")
                return True # Not a failure, just a pause
            
            print("\n✅ Agent分析完成")
            
            # 加载 Top 10 中间文件
            top10_file = os.path.join(date_dir, "selected_top10.json")
            top_stocks_list = all_stocks # 默认
            
            if os.path.exists(top10_file):
                 with open(top10_file, 'r', encoding='utf-8') as f:
                    top_stocks_list = json.load(f)
                 print(f"⚡ 加载 Top 10 股票池: {len(top_stocks_list)} 只")
            else:
                 print("⚠️ 未找到 selected_top10.json，将使用全部股票")

            # 生成小红书文案
            xiaohongshu_post, xhs_prompt = generate_xiaohongshu_post(gemini_analysis, top_stocks_list, date_dir)
            if xiaohongshu_post is None:
                print("\n⏸️  脚本暂停：等待Agent工作流处理小红书文案")
                return True
            print("✅ 小红书文案生成完成")
            
            # --- 新增步骤：从 AI分析报告 (result_analysis.txt) 回填 行业/题材 ---
            # 目的：解耦对小红书文案的依赖，直接使用分析结果
            enrich_stocks_from_analysis(top_stocks_list, date_dir)
            # -------------------------------------------------------------------
        except Exception as e_ai:
             print(f"⚠️ AI分析模块出错: {e_ai}")
             return False

    # (Skip Image Prompt generation if no analysis, logically)
    if gemini_analysis:
        try:
            # 生成图片提示词
            image_prompt, img_gen_prompt = generate_image_prompt(gemini_analysis, top_stocks_list, date_dir)
            if image_prompt is not None:
                print("✅ 图片提示词生成完成")
                
                # 保存独立图片提示词文件
                prompt_dir = os.path.join(date_dir, "AI提示词")
                os.makedirs(prompt_dir, exist_ok=True)
                img_prompt_file = os.path.join(prompt_dir, "趋势B1选股_Prompt.txt")
                with open(img_prompt_file, 'w', encoding='utf-8') as f:
                    f.write(image_prompt)
                print(f"📁 图片提示词已保存: {img_prompt_file}")
        except Exception as e_img:
            print(f"⚠️ 图片提示词生成失败: {e_img}")

    # 4. 保存报告
    save_reports(gemini_analysis, xiaohongshu_post, today)
    return True


if __name__ == "__main__":
    run()
