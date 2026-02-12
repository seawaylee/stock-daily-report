"""
全市场选股 + AI智能分析生成报告
1. 300并发全市场选股（市值100亿+，排除ST）
2. 接入Gemini分析Top5值博率

"""
import sys
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import requests
import base64
import time
import random
import numpy as np
from tqdm import tqdm

# 导入配置和Prompt模块
from common.config import MAX_WORKERS, MIN_MARKET_CAP
from common.prompts import (
    NumpyEncoder, 
    get_analysis_prompt, 
    get_image_prompt
)

# 导入数据获取和信号检测模块

# 导入数据获取和信号检测模块
from common.data_fetcher import get_all_stock_list, get_stock_data
from common.signals import check_stock_signal
# Import new LLM client
from common.llm_client import chat_completion

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


# ============ 热门题材过滤功能 ============

def get_hot_sectors_from_fish_basin(date_dir: str, top_n: int = 5):
    """
    从趋势模型Prompt文件中提取Top N热门题材
    
    Args:
        date_dir: 日期目录（例如：results/20260204）
        top_n: 获取前N个题材，默认5
    
    Returns:
        题材列表，例如：['贵金属', '有色金属', '光伏设备', '石油加工贸易', '半导体']
        如果提取失败返回空列表
    """
    import re
    from datetime import datetime, timedelta
    
    # 尝试读取今天的趋势模型Prompt文件
    prompt_file = os.path.join(date_dir, "AI提示词", "趋势模型_合并_Prompt.txt")
    
    # Fallback: 如果今天的文件不存在，尝试昨天的
    if not os.path.exists(prompt_file):
        print(f"⚠️ 今日趋势模型文件不存在: {prompt_file}")
        # 尝试昨天
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
        prompt_file = os.path.join("results", yesterday, "AI提示词", "趋势模型_合并_Prompt.txt")
        if not os.path.exists(prompt_file):
            print(f"❌ 昨日趋势模型文件也不存在: {prompt_file}")
            return []
        else:
            print(f"✅ 使用昨日趋势模型文件: {prompt_file}")
    
    try:
        with open(prompt_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找 "SECTION 2: 热门题材趋势" 部分
        section_match = re.search(r'SECTION 2:.*?热门题材.*?\*\*Data\*\*:(.*?)---', content, re.DOTALL)
        if not section_match:
            print("❌ 未找到热门题材数据段")
            return []
        
        data_section = section_match.group(1)
        
        # 提取题材名称：格式为 "1. ● 贵金属 | 涨跌:..."
        # 正则匹配：数字. ○/● 题材名称 |
        pattern = r'\d+\.\s*[●○]\s*([^\s|]+)\s*\|'
        matches = re.findall(pattern, data_section)
        
        if not matches:
            print("❌ 未能提取题材名称")
            return []
        
        # 取前top_n个
        hot_sectors = matches[:top_n]
        print(f"📊 提取到Top{top_n}热门题材: {hot_sectors}")
        return hot_sectors
        
    except Exception as e:
        print(f"❌ 提取热门题材失败: {e}")
        return []


def match_stock_sector(stock_info: dict, hot_sectors: list) -> bool:
    """
    判断股票是否属于热门题材
    
    Args:
        stock_info: 股票信息字典（需包含'industry'或'sector'字段）
        hot_sectors: 热门题材列表
    
    Returns:
        是否匹配任一热门题材
    """
    if not hot_sectors:
        return False
    
    # 获取股票的行业/题材信息
    industry = stock_info.get('industry', '')
    sector = stock_info.get('sector', '')
    combined = f"{industry} {sector}".lower()
    
    # 题材映射表：Fish Basin题材名 -> 可能的行业关键词
    sector_mapping = {
        '贵金属': ['黄金', '白银', '贵金属'],
        '有色金属': ['有色', '铝', '铜', '锌', '镍', '钴', '锂'],
        '光伏设备': ['光伏', '太阳能', '逆变器', '硅片'],
        '石油加工贸易': ['石油', '石化', '化工', '炼化'],
        '半导体': ['半导体', '芯片', '集成电路', 'IC', '晶圆'],
        '商业航天': ['航天', '卫星', '火箭', '航空航天'],
        '保险': ['保险', '寿险', '财险'],
        '稀土': ['稀土', '钕铁硼', '永磁'],
        '通信设备': ['通信', '5G', '光通信', '网络设备'],
        '细分化工': ['化工', '化学', '精细化工'],
        '电网设备': ['电网', '电力设备', '特高压', '变压器'],
        '煤炭': ['煤炭', '煤矿', '焦煤'],
        '房地产': ['房地产', '地产', '物业'],
        '风电设备': ['风电', '风能', '风机'],
        '电力': ['电力', '发电', '火电', '水电'],
        '养殖': ['养殖', '猪', '鸡', '禽'],
        '医疗服务': ['医疗', '医院', '诊断'],
        '新能源': ['新能源', '电池', '储能', '锂电'],
        '人工智能': ['人工智能', 'AI', '算力', '芯片', '云计算'],
        '旅游': ['旅游', '酒店', '景区'],
    }
    
    # 匹配逻辑
    for hot_sector in hot_sectors:
        # 直接匹配
        if hot_sector.lower() in combined:
            return True
        
        # 通过映射表匹配
        if hot_sector in sector_mapping:
            keywords = sector_mapping[hot_sector]
            for keyword in keywords:
                if keyword.lower() in combined:
                    return True
    
    return False


def process_single_stock(args):
    """处理单只股票"""
    code, name, market_cap, industry = args
    # Add random delay to prevent request bursts (Anti-Scraping / Flow Control)
    time.sleep(random.uniform(0.1, 0.2))
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
    
    # 保存结果
    today_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # 保存所有原始数据 (Incremental)
    raw_file = os.path.join(date_dir, f"all_stocks_{today_timestamp}.jsonl")
    print(f"📁 实时数据将写入: {raw_file}")

    # Initial Parallel Fetch
    processed_codes = set()
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_single_stock, args): args[0] for args in args_list}
        
        # Open file in append mode for incremental writing
        with open(raw_file, 'w', encoding='utf-8') as f_out:
            for future in tqdm(as_completed(futures), total=len(futures), desc="选股进度"):
                result = future.result()
                if result is not None:
                    # Incremental Write
                    f_out.write(json.dumps(result, cls=NumpyEncoder, ensure_ascii=False) + '\n')
                    f_out.flush() # Ensure it flows to disk
                    
                    all_results.append(result)
                    processed_codes.add(result['code'])
                    if result['signal']:
                        selected.append(result)

    # Retry Logic
    missing_args = [arg for arg in args_list if arg[0] not in processed_codes]
    if missing_args:
        print(f"\n🔄 B1 Retry: {len(missing_args)} stocks failed. Retrying sequentially...")
        import time
        
        with open(raw_file, 'a', encoding='utf-8') as f_out:
            for i, args in enumerate(missing_args):
                code = args[0]
                try:
                    # Sequential Retry with delay
                    time.sleep(0.5) 
                    result = process_single_stock(args)
                    
                    if result is not None:
                        f_out.write(json.dumps(result, cls=NumpyEncoder, ensure_ascii=False) + '\n')
                        f_out.flush()
                        all_results.append(result)
                        processed_codes.add(code)
                        if result['signal']:
                            selected.append(result)
                        print(f"   ✅ Retry success: {code}")
                    else:
                        pass # still failed
                except:
                    pass
                
                if (i+1) % 10 == 0:
                    print(f"   Retry progress: {i+1}/{len(missing_args)}")

    # Summary
    success_count = len(processed_codes)
    total_count = len(args_list)
    fail_count = total_count - success_count
    
    print("\n" + "="*40)
    print(f"📊 B1选股 执行汇总")
    print(f"✅ 成功: {success_count}/{total_count}")
    print(f"❌ 失败: {fail_count}/{total_count}")
    print("="*40)
    
    # raw_file is already written incrementally
    
    
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


def normalize_stock_code(code):
    """统一股票代码为6位数字，兼容 sz000001 / sh600000 / 600000。"""
    import re

    digits = re.sub(r"\D", "", str(code or ""))
    return digits[-6:] if digits else ""


def compact_reason_text(reason, max_len=18):
    """压缩LLM理由为简洁短句，避免卡片文本过长。"""
    import re

    cleaned = re.sub(r"\s+", "", str(reason or "").strip())
    if not cleaned:
        return ""

    parts = re.split(r"[。！？!?；;]", cleaned)
    first = ""
    for part in parts:
        segment = part.strip("，,：: ")
        if segment:
            first = segment
            break

    if not first:
        first = cleaned

    if len(first) > max_len:
        return first[: max_len - 1] + "…"
    return first


def extract_reason_map_from_analysis(analysis_text):
    """从分析文本中提取 code->简洁理由 映射。"""
    import re

    if not analysis_text:
        return {}

    reason_map = {}
    lines = analysis_text.splitlines()
    current_code = None

    for idx, raw_line in enumerate(lines):
        line = raw_line.strip()
        if not line:
            continue

        code_match = re.search(r"\((\d{6})\)", line)
        if code_match:
            current_code = code_match.group(1)
            inline_reason = re.search(r"推荐理由[:：]\s*(.+)", line)
            if inline_reason:
                reason_map[current_code] = compact_reason_text(inline_reason.group(1))
                current_code = None
            continue

        if not current_code:
            continue

        reason_line = re.search(r"推荐理由[:：]?\s*(.*)", line)
        if not reason_line:
            continue

        reason_text = reason_line.group(1).strip(" -*•")
        if not reason_text:
            # "推荐理由："单独占一行时，尝试读取下一条非空行作为理由。
            for next_idx in range(idx + 1, min(idx + 4, len(lines))):
                candidate = lines[next_idx].strip(" -*•\t")
                if not candidate:
                    continue
                if re.search(r"\(\d{6}\)", candidate):
                    break
                reason_text = candidate
                break

        compacted = compact_reason_text(reason_text)
        if compacted:
            reason_map[current_code] = compacted
        current_code = None

    return reason_map


def extract_industry_map_from_analysis(analysis_text):
    """从分析文本中提取 code->行业/题材 映射。"""
    import re

    if not analysis_text:
        return {}

    industry_map = {}
    for raw_line in analysis_text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        match = re.search(r"\((\d{6})\)\s*\|\s*(.+)$", line)
        if not match:
            continue

        code = match.group(1)
        industry = match.group(2).strip()
        industry = re.sub(r"^[\-\*\s]+", "", industry)
        industry = re.sub(r"[\*\s]+$", "", industry)
        industry = re.sub(r"\s{2,}", " ", industry)
        if industry and "推荐理由" not in industry:
            industry_map[code] = industry

    return industry_map


def build_fallback_reason(stock):
    """没有LLM理由时，使用技术指标生成简洁回退理由。"""
    signal = ",".join(stock.get("signals", []))
    signal = signal.replace("原始", "").replace("B1", "买点").replace("B", "买点")
    signal = signal.split(",")[0].strip() or "形态关注"

    j_val = round(stock.get("J", 0), 1)
    rsi_val = round(stock.get("RSI", 0), 1)
    return compact_reason_text(f"{signal}，J{j_val}/RSI{rsi_val}")



def call_gemini_analysis(selected_stocks, date_dir):
    """使用LLM直接分析Top5值博率 (全自动模式)"""
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

    # 统一中间文件目录
    temp_dir = os.path.join(date_dir, "temp_data")
    os.makedirs(temp_dir, exist_ok=True)

    prompt = get_analysis_prompt(stocks_info)

    # 保存Prompt备份
    task_file = os.path.join(temp_dir, "task_analysis_prompt.txt")
    with open(task_file, 'w', encoding='utf-8') as f:
        f.write(prompt)

    print(f"\n[4/4] 正在调用 LLM 进行深度分析 (Top {len(selected_stocks)} 只)...")
    print(f"⏳ 请求已发送，请稍候...")

    # === 直接调用 LLM ===
    try:
        start_time = time.time()
        analysis_result = chat_completion(prompt, system_prompt="You are a professional quantitative financial analyst.")
        duration = time.time() - start_time

        if not analysis_result:
            print("❌ LLM 分析失败: 返回为空")
            return None, prompt

        print(f"✅ LLM 分析完成 (耗时 {duration:.1f}s)")

        # 保存结果备份
        output_file = os.path.join(temp_dir, "result_analysis.txt")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(analysis_result)
        print(f"💾 分析报告已保存: {output_file}")

        # --- 提取并保存 Top 5 ---
        import re
        # 匹配 (600123) 格式
        top_codes = re.findall(r'\((\d{6})\)', analysis_result)
        seen = set()
        unique_codes = []
        for c in top_codes:
            if c not in seen:
                unique_codes.append(c)
                seen.add(c)
        unique_codes = unique_codes[:5]  # Top 5

        stock_map = {}
        for stock in selected_stocks:
            norm_code = normalize_stock_code(stock.get("code"))
            if norm_code and norm_code not in stock_map:
                stock_map[norm_code] = stock
        top_stocks = []
        for c in unique_codes:
            if c in stock_map:
                top_stocks.append(stock_map[c])

        reason_map = extract_reason_map_from_analysis(analysis_result)
        industry_map = extract_industry_map_from_analysis(analysis_result)
        for stock in top_stocks:
            norm_code = normalize_stock_code(stock.get("code"))
            reason = reason_map.get(norm_code)
            if reason:
                stock["reason"] = reason
            industry = industry_map.get(norm_code)
            if industry:
                stock["industry"] = industry

        top5_file = os.path.join(temp_dir, "selected_top5.json")
        with open(top5_file, 'w', encoding='utf-8') as f:
            json.dump(top_stocks, f, cls=NumpyEncoder, ensure_ascii=False, indent=2)

        # 兼容旧流程：保留 selected_top10.json（内容同Top5）
        legacy_top10_file = os.path.join(temp_dir, "selected_top10.json")
        with open(legacy_top10_file, 'w', encoding='utf-8') as f:
            json.dump(top_stocks, f, cls=NumpyEncoder, ensure_ascii=False, indent=2)
        print(f"📁 已提取 Top5 股票池: {top5_file} ({len(top_stocks)}只)")

        return analysis_result, prompt

    except Exception as e:
        print(f"❌ LLM 调用过程出错: {e}")
        return None, prompt





def generate_image_prompt(gemini_analysis, selected_stocks, date_dir):
    """直接生成信息图提示词 (无需Agent二次处理)"""
    # Import data masking utilities
    from common.data_masking import mask_stock_info

    # 准备股票数据摘要(包含技术指标 + 脱敏信息)
    if len(selected_stocks) > 5:
        print(f"⚠️ 警告: 传入图片生成的股票数量为 {len(selected_stocks)}，截取Top 5。")
        selected_stocks = selected_stocks[:5]

    # 从分析结果提取 "整体市场复盘" 和 "次日交易策略"
    import re
    
    # --- 提取复盘与策略 ---
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

    
    # 构建动态 Footer 内容
    footer_content = ""
    # if market_review and market_review != "无复盘内容":
    #    footer_content += f"📍 整体复盘\n{market_review}\n\n"
    
    # if tomorrow_strategy:
    #    footer_content += f"💡 次日策略\n{tomorrow_strategy}"
    # 
    # USER REQUEST: Specific Footer with Disclaimer
    footer_content = """
**FOOTER:**
"Daily AI Algo Strategy | High Value Ratio Stocks | Follow for Updates"
(Render in Chinese: "每日盘后分享AI量化策略的高值博率股票，点赞关注不迷路")

**免责声明 (Disclaimer):**
本内容仅供学习交流，不构成任何投资建议。
股市有风险，投资需谨慎。请独立思考，理性决策。
"""

    # --- Generate Card Text with Trading Strategy (Python Logic) ---
    reason_map = extract_reason_map_from_analysis(gemini_analysis)
    industry_map = extract_industry_map_from_analysis(gemini_analysis)
    cards_text = ""
    for idx, s in enumerate(selected_stocks, 1):
        # 应用数据脱敏：代码后2位替换为**，名称后2字替换为拼音缩写
        masked_code, masked_name = mask_stock_info(s['code'], s['name'])

        norm_code = normalize_stock_code(s.get("code"))
        industry = s.get('industry', '')
        if not industry or industry == '未知' or str(industry).lower() == 'nan':
            industry = industry_map.get(norm_code, "行业待补充")

        signals = ','.join(s.get('signals', [])).replace('B1', '买点').replace('B', '买点').replace('原始买点', '买点')
        signals = signals.split(',')[0]  # First signal

        J_val = round(s.get('J', 0), 2)
        RSI_val = round(s.get('RSI', 0), 2)
        llm_reason = s.get("reason") or reason_map.get(norm_code) or build_fallback_reason(s)
        llm_reason = compact_reason_text(llm_reason)

        # 使用脱敏后的代码和名称
        line1 = f"#{idx} {masked_name} | {masked_code} | 🏭 {industry}"
        line2 = f"📌 选股理由: {llm_reason}"
        line3 = f"📊 信号: {signals} | J={J_val} RSI={RSI_val}"

        cards_text += f"{line1}\n{line2}\n{line3}\n\n"

    # --- Final Prompt Construction ---
    final_prompt = f"""(masterpiece, best quality), (vertical:1.2), (aspect ratio: 10:16), (sketch style), (hand drawn), (infographic)

Create a TALL VERTICAL PORTRAIT IMAGE (Aspect Ratio 10:16) HAND-DRAWN SKETCH style stock market infographic poster.

**CRITICAL: VERTICAL PORTRAIT FORMAT (10:16)**
- The image MUST be significantly taller than it is wide (Phone wallpaper style).
- Aspect Ratio: 10:16.
- Canvas Size: 1600x2560.

**CRITICAL: HAND-DRAWN AESTHETIC**
- Use ONLY pencil sketch lines, charcoal shading, ink pen strokes
- Visible paper grain texture throughout
- Line wobbles and imperfections (authentic hand-drawn feel)
- NO digital smoothness, NO vector graphics
- Shading: crosshatching, stippling, charcoal smudges only
- Background: Hand-drawn red-gold gradient with visible pencil strokes


Center: "AI大模型量化策略 · 热门题材筛选" + "{datetime.now().strftime('%Y-%m-%d')}"
**Visual Highlight**: Add a realistic "Red Ink Stamp" (Seal) near the title with text: "次日择机买入"

**NEW: 基于趋势模型Top5热门题材筛选**

5 stock cards in a single column layout:
Background: Pale blue background with paper texture

**COLOR ACCENT GUIDELINES (Avoid monotone):**
- Keep overall palette soft and low-saturation, not neon.
- Use soft AI-cyan accents (e.g., #BFEFFF / #DFF4FF) for small icons like 📌 📊 🏭.
- Render line icons and separators with light tint + hand-drawn ink texture.
- For key sentences (especially "选股理由"), add a rounded light highlight background.
- Highlight chip colors: pale cyan #EAF7FF or light amber #FFF4E6.
- Keep text readable: dark gray text on light backgrounds.

**VISUAL CONTENT:**
Refined Hand-Drawn Table/Cards:

{cards_text}

{footer_content}

(Note: This prompt is optimized for the 'Nano Banana Pro3' model. Please ensure all details are consistent with high-quality hand-drawn vector art.)
"""

    return final_prompt, final_prompt

def save_reports(gemini_analysis, today):
    """保存报告（简化版 - 仅保存到agent_outputs）"""
    # 注释：外层重复文件已移除，所有结果集中在 agent_outputs/
    # 此函数保留用于向后兼容，actual saving done in agent workflow
    date_str = today.split('_')[0]
    date_dir = os.path.join("results", date_str)
    
    print(f"� 分析结果已保存到: {date_dir}/agent_outputs/")
    print(f"   - result_analysis.txt")

    print(f"   - result_image_prompt.txt")
    
    return None


def save_prompts(prompts_dict, today):
    """保存提示词记录（可选 - 用于调试）"""
    # 注释：此功能可选，提示词已在 agent_tasks/ 中保存
    # 保留此函数用于调试目的
def enrich_stocks_from_analysis(selected_stocks, date_dir):
    """从分析报告回填行业/题材"""
    try:
        print("🔄 正在从分析报告回填 [行业] 和 [脱敏信息]...")
        temp_dir = os.path.join(date_dir, "temp_data")
        analysis_file = os.path.join(temp_dir, "result_analysis.txt")
        if os.path.exists(analysis_file):
            with open(analysis_file, 'r', encoding='utf-8') as f:
                content = f.read()

            industry_map = extract_industry_map_from_analysis(content)

            # 回填到 selected_stocks
            count = 0
            for stock in selected_stocks:
                pure_code = normalize_stock_code(stock.get("code"))
                if pure_code in industry_map:
                    stock['industry'] = industry_map[pure_code]
                    count += 1

            print(f"✅ 成功从分析报告回填 {count} 条行业数据")

            # 保存回填后的结果到 selected_top5.json
            top5_file = os.path.join(temp_dir, "selected_top5.json")
            with open(top5_file, 'w', encoding='utf-8') as f:
                json.dump(selected_stocks, f, cls=NumpyEncoder, ensure_ascii=False, indent=2)

            # 兼容旧流程
            legacy_top10_file = os.path.join(temp_dir, "selected_top10.json")
            with open(legacy_top10_file, 'w', encoding='utf-8') as f:
                json.dump(selected_stocks, f, cls=NumpyEncoder, ensure_ascii=False, indent=2)
            print(f"💾 已更新 selected_top5.json")

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
    
    # 2. **NEW** 获取热门题材并过滤股票
    print("\n" + "="*70)
    print("  Step 2: 热门题材过滤")
    print("="*70)
    
    if not selected:
        print("❌ 没有选出股票，跳过 B1 AI 分析，继续执行其他模块...")
        return False
    
    print(f"📊 B1技术筛选结果: {len(selected)} 只股票")
    
    # 获取Top5热门题材
    hot_sectors = get_hot_sectors_from_fish_basin(date_dir, top_n=5)
    
    if not hot_sectors:
        print("⚠️ 未能获取热门题材，跳过题材过滤，使用全部B1股票")
        filtered_stocks = selected
    else:
        # 按题材过滤逻辑优化：优先选题材，不足则按信号强度补齐
        hot_stocks = [s for s in selected if match_stock_sector(s, hot_sectors)]

        print(f"\n✅ 题材匹配完成:")
        print(f"   - 热门题材Top5: {', '.join(hot_sectors)}")
        print(f"   - 匹配题材的B1股票: {len(hot_stocks)} 只")

        # 补齐逻辑：确保至少有 15-20 只候选股供 AI 筛选 Top 5
        target_pool_size = 20
        if len(hot_stocks) < target_pool_size:
            # 排除已选中的题材股
            remaining = [s for s in selected if s not in hot_stocks]
            # 按 J 值排序（越低代表超卖越严重，信号通常越强）
            remaining.sort(key=lambda x: x.get('J', 100))

            padding_needed = min(len(remaining), target_pool_size - len(hot_stocks))
            padding_stocks = remaining[:padding_needed]

            filtered_stocks = hot_stocks + padding_stocks
            print(f"   - 信号补齐: 题材股 {len(hot_stocks)} 只 + 强信号补齐 {len(padding_stocks)} 只 = 总计 {len(filtered_stocks)} 只候选")
        else:
            filtered_stocks = hot_stocks
            print(f"   - 题材股充足，使用前 {len(filtered_stocks)} 只候选")
    
    # 3. 调用AI分析 (使用filtered_stocks而不是selected)
    print("\n" + "="*70)
    print("  Step 3: AI智能分析")
    print("="*70)
    
    try:
        # 传入过滤后的股票供Agent分析
        # Agent会从中选出Top进行深度分析
        all_stocks = filtered_stocks
        
        # 调用Agent分析（传入题材过滤后的候选）
        gemini_analysis, analysis_prompt = call_gemini_analysis(all_stocks, date_dir)

        # 如果分析失败
        if gemini_analysis is None:
            print("\n❌ LLM 分析失败，无法生成后续报告")
            return False

        print("\n✅ AI 智能分析流程结束")

        # 加载 Top 5 中间文件 (call_gemini_analysis 已经生成)
        temp_dir = os.path.join(date_dir, "temp_data")
        top5_file = os.path.join(temp_dir, "selected_top5.json")
        legacy_top10_file = os.path.join(temp_dir, "selected_top10.json")
        top_stocks_list = all_stocks # 默认
        
        if os.path.exists(top5_file):
             with open(top5_file, 'r', encoding='utf-8') as f:
                top_stocks_list = json.load(f)
             print(f"⚡ 加载 Top5股票池: {len(top_stocks_list)} 只")
        elif os.path.exists(legacy_top10_file):
             with open(legacy_top10_file, 'r', encoding='utf-8') as f:
                top_stocks_list = json.load(f)
             print(f"⚡ 加载兼容股票池: {len(top_stocks_list)} 只")
        else:
             print("⚠️ 未找到 selected_top5.json，将使用全部过滤后的股票")

        # --- 新增步骤：从 AI分析报告 (result_analysis.txt) 回填 行业/题材 ---
        # 目的：直接从分析结果回填信息
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
    save_reports(gemini_analysis, today)
    return True


if __name__ == "__main__":
    run()
