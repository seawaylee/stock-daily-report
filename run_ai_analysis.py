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
import numpy as np
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_fetcher import get_all_stock_list, get_stock_data
from signals import check_stock_signal
from tqdm import tqdm
import pandas as pd

# 配置
MAX_WORKERS = 100
MIN_MARKET_CAP = 100  # 市值100亿以上


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
            'industry': industry,  # 题材/行业
            'signal': bool(result.get('signal', False)),
            'signals': result.get('signals', []),
            'K': float(result.get('K', 0)),
            'D': float(result.get('D', 0)),
            'J': float(result.get('J', 0)),
            'RSI': float(result.get('RSI', 0)),
            'near_amplitude': float(result.get('近期振幅', 0)),
            'far_amplitude': float(result.get('远期振幅', 0)),
            'raw_data': last_row
        }
    except Exception as e:
        return None


def run_full_selection():
    """全市场选股"""
    today_date = datetime.now().strftime('%Y%m%d')
    date_dir = os.path.join("results", today_date)
    os.makedirs(date_dir, exist_ok=True)
    
    # 检查是否已有今日结果
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

    print("=" * 70)
    print("  东方财富 - 知行B1选股策略 (AI智能分析版)")
    print(f"  市值 >= {MIN_MARKET_CAP}亿 | 排除ST | 并发线程: {MAX_WORKERS}")
    print(f"  执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # 获取股票列表
    print("\n[1/4] 获取股票列表...")
    stock_list = get_all_stock_list(min_market_cap=MIN_MARKET_CAP, exclude_st=True)
    
    # Limit to 500 stocks as requested
    stock_list = stock_list.head(500)
    print(f"⚠️ [Test Mode] 仅分析前 {len(stock_list)} 只股票")
    
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
            # 尝试获取收盘价，如果在数据里的话
            # 假设stock dict里可能有'price'或者'close'，如果没有就不显示
            
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




def call_gemini_analysis(selected_stocks):
    """调用Gemini分析Top10值博率"""
    from openai import OpenAI
    
    # 配置API（使用环境变量）
    api_key = "sk-ydHa8x53xR3roO9ppZRfuZkPkT5ozng1oXg7BTCeAedRbVgO"
    base_url = os.getenv("GEMINI_API_BASE_URL", "https://api.34ku.com/v1")


    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    )
    
    # 准备分析数据
    stocks_info = []
    for s in selected_stocks:
        raw = s['raw_data']
        stocks_info.append({
            '代码': s['code'],
            '名称': s['name'],
            '市值(亿)': round(s['market_cap'], 0),
            '题材': s.get('industry', ''),  # 添加题材
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
    
    prompt = f"""你是一位资深量化分析师。以下是通过"AI模型"策略选出的股票列表，该策略主要捕捉超卖反弹和回踩支撑的买入信号。

选出的股票数据：
{json.dumps(stocks_info, ensure_ascii=False, indent=2)}

请从中选出Today Top10值得关注的股票，评估标准：
1. 信号强度（多信号叠加更佳）
2. 技术指标位置（KDJ/RSI超卖程度）
3. 市值适中（流动性好但弹性足）
4. 近期波动（有足够空间）
5. **【重要】所属行业/题材**（由于数据源缺失，请你根据股票代码和名称，利用你的知识库补充其所属的行业和核心题材）

请输出：
1. Top10股票排名
   - 格式：`[股票名称] ([代码]) | [行业/题材] | [推荐理由]`
   - 理由要求：3-5句话，结合技术面与基本面题材。
2. 整体市场分析（2-3句话）
3. 风险提示

注意：这是技术分析参考，不构成投资建议。题材信息请务必准确。"""

    print("\n[4/4] 调用Gemini分析Top10...")
    response = client.chat.completions.create(
        model="gemini-3-flash-preview-thinking-exp",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.choices[0].message.content, prompt


def generate_xiaohongshu_post(gemini_analysis, selected_stocks):
    """生成小红书文案（脱敏处理）"""
    from openai import OpenAI
    
    client = OpenAI(
        api_key="sk-ydHa8x53xR3roO9ppZRfuZkPkT5ozng1oXg7BTCeAedRbVgO",
        base_url="https://api.34ku.com/v1"
    )
    
    # 准备脱敏说明
    prompt = f"""请将以下股票分析报告改写成小红书风格的文案。

原始分析：
{gemini_analysis}

要求：
1. **风格灵魂**：必须极度"小红书化"！大量使用Emoji，段落短促，语气兴奋、专业且硬核。
2. **Emoji使用规范**：
   - 标题前后必须加Emoji (e.g., 🚀/🔥/💰).
   - 每一段开头必须加Emoji.
   - 重点词汇前后加Emoji.
   - 推荐使用：🚀 (潜力), 💰 (买点), 📉 (超卖), 🎯 (目标), ⚠️ (风险), 🤖 (AI分析).
3. **【重要】股票脱敏处理**：
   - 股票名称：保留前两个字，后面的换成英文缩写（如"中芯国际"变成"中芯GJ"）。
   - 股票代码：前4位保留，后2位换成xx（如"688981"变成"6889xx"）。
4. **标题**：吸引眼球，20字以内。
5. **结构要求**：
   - **标题行**：日期 + 核心主题 + Emoji
    - 开头：仅用一句话概括（日期: {datetime.now().strftime('%Y-%m-%d')}，AI量化发现超卖反弹机会，请确保标题和文中日期准确无误！）。
    - 中间：直接列出Top10股票及其核心理由。每只股票一行，格式：
     `🔍 [股票名脱敏] ([代码脱敏]) | [行业] | [核心理由简述]` (请使用类似的清晰分割格式，稍微修饰一下)
   - **结尾**：风险提示 + 互动 + 关注引导。
6. **术语替换**：将 "B" 或 "B1" 替换为 "买点"。
7. **禁词**：绝对不要出现 "知行"、"东方财富" 等具体策略或来源名称。
7. **人设**：AI量化分析师（机器人语气，但生动）。
8. **严禁Markdown**：不要用 `**`, `###`, `- ` 等Markdown符号。只用Emoji和空行分段。
9. **文末话题**：#AI选股 #量化交易 #A股 #每日复盘
10. **字数**：1000字以内。
11. **称呼**：统称读者为"各位交易员" (Traders)，严禁使用"家人们"、"集美们"等小红书常见称呼。
12. **必须包含**："次日关注进场" 的提示。

请直接输出文案内容。"""



    response = client.chat.completions.create(
        model="gemini-3-flash-preview-thinking-exp",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content, prompt


def generate_image_prompt(gemini_analysis):
    """生成信息图提示词"""
    from openai import OpenAI
    
    client = OpenAI(
        api_key="sk-ydHa8x53xR3roO9ppZRfuZkPkT5ozng1oXg7BTCeAedRbVgO",
        base_url="https://api.34ku.com/v1"
    )
    
    prompt = f"""基于以下股票分析内容，设计一个生成图片的Prompt。

分析内容：
{gemini_analysis}

当前日期：{datetime.now().strftime('%Y-%m-%d')}

要求基于用户指令：
"请根据输入内容提取核心主题与要点，生成一张卡通风格的信息图：采用手绘风格，横版构图。 加入简洁的卡通元素、图标或名人画像，增强趣味性和视觉记忆。
【重要】图片中必须清晰标注今日日期 ({datetime.now().strftime('%Y-%m-%d')})。
【重要】图中的主角/分析师形象必须是一个具有科技感的AI机器人，而不是人类分析师。
【重要】除了技术指标名称（如RSI, KDJ, MACD）外，图片中绝对不要出现任何其他英文字母！所有标题、说明文字必须是中文手绘字体。
如果有敏感人物或者版权内容，画一个相似替代，但是不要拒绝生成所有图像、文字必须使用手绘风格。信息精简，突出关键词与核心概念，多留白，易于一眼抓住重点。"

请输出一段英文Prompt，用于文生图模型，描述这张信息图的视觉细节。包含Top股票的关键信息。确保在Prompt中明确指定：
1. Title includes date '{datetime.now().strftime('%Y-%m-%d')}'.
2. Title text MUST be "AI大模型量化 今日精选Top10". Do NOT include specific strategy names.
3. The main character is a high-tech AI Robot.
4. NO English text allows for general content, ONLY Technical Indicators (RSI, KDJ, etc.) are allowed in English. All other text MUST be Chinese.
5. **Vertical composition (Aspect Ratio 3:4 or 9:16)** is REQUIRED to fit Xiaohongshu full screen. The image MUST be tall, not wide.
6. **MUST include ALL Top 10 stocks** listed in the analysis content. Arrange them in a clear list or grid format.
7. **MUST include text**: "次日关注进场" (Watch for entry tomorrow) in a prominent position.
8. **Terminology**: Replace all "B" or "B1" signals with "买点" (Buy Point) in Chinese text on the image (e.g. "原始买点", "缩量买点").
"""

    response = client.chat.completions.create(
        model="gemini-3-flash-preview-thinking-exp",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content, prompt


def save_reports(gemini_analysis, xiaohongshu_post, today):
    """保存报告"""
    # 创建日期目录
    date_str = today.split('_')[0]
    date_dir = os.path.join("results", date_str)
    os.makedirs(date_dir, exist_ok=True)
    
    # 保存MD报告
    md_file = os.path.join(date_dir, f"ai_analysis_{today}.md")
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(f"# 📊 AI智能选股分析报告\n\n")
        f.write(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"---\n\n")
        f.write(gemini_analysis)
        f.write(f"\n\n---\n\n")
        f.write(f"## 📱 小红书文案\n\n")
        f.write(xiaohongshu_post)
    
    print(f"📁 AI分析报告: {md_file}")
    
    # 保存小红书文案
    xhs_file = os.path.join(date_dir, f"xiaohongshu_{today}.txt")
    with open(xhs_file, 'w', encoding='utf-8') as f:
        f.write(xiaohongshu_post)
    
    print(f"📁 小红书文案: {xhs_file}")
    
    return md_file, xhs_file


def save_prompts(prompts_dict, today):
    """保存提示词记录"""
    date_str = today.split('_')[0]
    date_dir = os.path.join("results", date_str)
    os.makedirs(date_dir, exist_ok=True)
    
    prompt_file = os.path.join(date_dir, f"prompts_{today}.md")
    
    with open(prompt_file, 'w', encoding='utf-8') as f:
        f.write(f"# 🤖 AI 提示词记录\n")
        f.write(f"> 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        for title, content in prompts_dict.items():
            f.write(f"## {title}\n\n")
            f.write("```text\n")
            f.write(content)
            f.write("\n```\n\n")
            f.write("---\n\n")
            
    print(f"📁 提示词记录: {prompt_file}")
    return prompt_file


def main():
    # 1. 全市场选股
    selected, today = run_full_selection()
    
    # 确保日期文件夹存在
    date_str = today.split('_')[0]
    date_dir = os.path.join("results", date_str)
    os.makedirs(date_dir, exist_ok=True)
    
    # 保存私信汇总列表
    if selected:
        save_stock_summary(selected, date_dir, today)
    
    # 4. 调用AI分析
    if not selected:
        print("❌ 没有选出股票，跳过分析")
        return

    try:
        gemini_analysis, analysis_prompt = call_gemini_analysis(selected) # 传 Top10
        print("\n✅ Gemini分析完成")
        
        # 3. 生成小红书文案
        xiaohongshu_post, xhs_prompt = generate_xiaohongshu_post(gemini_analysis, selected)
        print("✅ 小红书文案生成完成")
        
        # 4. 生成图片提示词
        image_prompt, img_gen_prompt = generate_image_prompt(gemini_analysis)
        print("✅ 图片提示词生成完成")
        print(f"\n[Image Prompt]:\n{image_prompt}\n")
        
        # 保存提示词
        prompts_dict = {
            "Top10分析 Prompt": analysis_prompt,
            "小红书文案 Prompt": xhs_prompt,
            "图片生成 Prompt": img_gen_prompt
        }
        save_prompts(prompts_dict, today)
        
        # 4. 保存报告
        save_reports(gemini_analysis, xiaohongshu_post, today)
        
    except Exception as e:
        print(f"\n❌ AI分析出错: {e}")
        print("请确保已设置 GOOGLE_API_KEY 环境变量")


if __name__ == "__main__":
    main()
