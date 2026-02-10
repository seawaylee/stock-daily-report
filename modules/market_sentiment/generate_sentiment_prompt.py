"""
Market Sentiment Prompt Generation
Generates analysis report prompt and image generation prompt.
"""

from datetime import datetime
from typing import Dict, Any


def generate_analysis_prompt(sentiment_result: Dict[str, Any]) -> str:
    """
    Generate a prompt for LLM to write the market sentiment analysis report.

    Args:
        sentiment_result: Result from calculate_sentiment_index()

    Returns:
        Formatted prompt string
    """
    index_value = sentiment_result['index']
    sentiment_level = sentiment_result['sentiment_level']
    scores = sentiment_result['score_breakdown']
    raw_data = sentiment_result['raw_data']

    # Format indices data
    indices_text = "\n".join([
        f"- {name}: {change:+.2f}%"
        for name, change in raw_data['indices'].items()
    ])

    # Format news data
    news = raw_data['news_sentiment']
    bullish_news = "\n".join([f"  • {n}" for n in news['bullish_news']]) or "  无"
    bearish_news = "\n".join([f"  • {n}" for n in news['bearish_news']]) or "  无"

    # Format sector flow
    sectors = raw_data['sector_flow']
    inflow_text = "\n".join([
        f"  • {s['名称']}: {s['净额']/1e8:.2f}亿"
        for s in sectors['inflow_sectors']
    ]) or "  无数据"
    outflow_text = "\n".join([
        f"  • {s['名称']}: {s['净额']/1e8:.2f}亿"
        for s in sectors['outflow_sectors']
    ]) or "  无数据"

    prompt = f"""# 市场情绪分析报告 - {datetime.now().strftime("%Y年%m月%d日")}

## 任务说明
你是一位资深的A股市场分析师。请根据以下市场数据，撰写一份专业的市场情绪分析报告。

## 贪婪恐惧指数
**当前指数**: {index_value}/100 ({sentiment_level})

### 指数构成分析
- 市场宽度评分: {scores['market_breadth']:+.2f} (满分±15)
- 指数趋势评分: {scores['indices_trend']:+.2f} (满分±15)
- 新闻情绪评分: {scores['news_sentiment']:+.2f} (满分±10)
- 资金流向评分: {scores['money_flow']:+.2f} (满分±10)

## 原始市场数据

### 1. 主要指数表现
{indices_text}

### 2. 市场情绪指标
- 涨停股票数量: {raw_data['limit_up_count']}
- 跌停股票数量: {raw_data['limit_down_count']}
- 涨跌停比率: {raw_data['limit_up_count']/(raw_data['limit_up_count']+raw_data['limit_down_count']+1):.2%}

### 3. 新闻情绪分布
- 利好新闻: {news['bullish_count']}条
- 利空新闻: {news['bearish_count']}条
- 中性新闻: {news['neutral_count']}条

**主要利好新闻**:
{bullish_news}

**主要利空新闻**:
{bearish_news}

### 4. 板块资金流向
**净流入板块 (Top 3)**:
{inflow_text}

**净流出板块 (Top 3)**:
{outflow_text}

**总体净流向**: {sectors['net_inflow']/1e8:.2f}亿元

---

## 报告要求

请撰写一份结构化的市场情绪分析报告，包含以下部分：

### 1. 市场情绪总结 (200字以内)
- 用通俗易懂的语言解释当前的贪婪恐惧指数值
- 说明当前市场处于什么情绪状态，以及这对投资者意味着什么

### 2. 数据解读与证据支撑 (400-600字)
- **指数表现**: 分析主要指数的涨跌情况，哪些指数表现强势/弱势
- **市场宽度**: 从涨跌停数据看，市场赚钱效应如何
- **资金流向**: 哪些板块受到资金青睐，哪些被抛弃，背后的逻辑是什么
- **新闻面**: 结合具体新闻标题，分析当前市场的主要关注点和情绪倾向

### 3. 投资建议 (300-400字)

#### 短期建议 (1-3日)
- 基于当前情绪状态，给出仓位建议（激进/稳健/保守）
- 操作策略：追涨/观望/逢高减仓等

#### 中长期建议 (1-4周)
- 趋势判断：市场可能的运行方向
- 风险提示：需要关注的潜在风险点

### 4. 主题与板块机会 (200-300字)
- 基于资金流向和新闻热点，推荐2-3个值得关注的主题或板块
- 说明推荐逻辑和潜在催化剂
- 给出具体的关注指数或ETF代码（如有）

### 5. 风险提示
- 列出当前市场主要风险因素
- 给出应对建议

---

## 输出格式要求
- 使用Markdown格式
- 语言专业但易懂，避免过于晦涩的术语
- 观点明确，有理有据
- 数据引用要准确，来源于上述提供的原始数据
- 总字数控制在1200-1500字

请开始撰写报告。
"""

    return prompt


def get_raw_image_prompt(sentiment_result: Dict[str, Any]) -> str:
    """
    Generate the raw English prompt for image generation.
    """
    index_value = sentiment_result['index']
    sentiment_level = sentiment_result['sentiment_level']
    color = sentiment_result['color']

    # Try to get top sector for visual elements (simple mapping)
    # This adds variety based on market data
    visual_extras = ""
    try:
        raw_data = sentiment_result.get('raw_data', {})
        sectors = raw_data.get('sector_flow', {}).get('inflow_sectors', [])
        if sectors:
            top_sector = sectors[0]['名称']
            # Simple keyword mapping for common sectors
            sector_map = {
                "半导体": "circuit board patterns, microchip details",
                "电子": "electronic components sketches",
                "计算机": "binary code background elements",
                "新能源": "solar panel sketches, lightning bolts",
                "光伏": "sun ray patterns",
                "电池": "energy symbols",
                "医药": "medical cross symbols, herb sketches",
                "医疗": "DNA helix sketches",
                "白酒": "vintage wine bottle contours",
                "食品": "wheat patterns",
                "银行": "coin stacks sketches, vault door details",
                "证券": "candlestick chart patterns",
                "地产": "building blueprints",
                "汽车": "gear mechanical parts"
            }
            # Find matching keyword
            for key, val in sector_map.items():
                if key in top_sector:
                    visual_extras = f", {val} blended in background"
                    break
    except:
        pass

    # Map color to visual elements
    color_themes = {
        "red": {
            "atmosphere": "fiery red tones, burning background",
            "mood": "frenzy, excitement",
            "elements": "rising arrows, flames, scattering sparks"
        },
        "orange": {
            "atmosphere": "warm orange tones, bright background",
            "mood": "optimistic, positive",
            "elements": "upward curves, warm light rays, blooming flowers sketches"
        },
        "yellow": {
            "atmosphere": "neutral yellow tones, balanced composition",
            "mood": "calm, waiting",
            "elements": "horizontal lines, balanced scales, pendulum"
        },
        "blue": {
            "atmosphere": "cool blue tones, calm background",
            "mood": "cautious, worried",
            "elements": "falling curves, cool shadows, rain streaks"
        },
        "dark_blue": {
            "atmosphere": "deep cold blue tones, icy background",
            "mood": "panic, extreme pessimism",
            "elements": "downward arrows, ice crystals, frost textures, cracked ground"
        }
    }

    theme = color_themes.get(color, color_themes["yellow"])

    # 构建更丰富的信息图Prompt (包含5大维度区块)
    scores = sentiment_result.get('score_breakdown', {})

    # 维度描述生成
    dim_desc = []
    # 1. 宽度
    breadth_score = scores.get('market_breadth', 0)
    dim_desc.append(f"Panel 1 (Breadth): {'Rising' if breadth_score > 0 else 'Falling'} bar chart sketch")
    # 2. 趋势
    trend_score = scores.get('indices_trend', 0)
    dim_desc.append(f"Panel 2 (Trend): {'Upward' if trend_score > 0 else 'Downward'} line graph")
    # 3. 资金
    flow_score = scores.get('money_flow', 0)
    dim_desc.append(f"Panel 3 (Capital): {'Inflow' if flow_score > 0 else 'Outflow'} coin stack illustration")
    # 4. 新闻
    news_score = scores.get('news_sentiment', 0)
    dim_desc.append(f"Panel 4 (News): {'Sun' if news_score > 0 else 'Cloud'} weather icon over newspaper")
    # 5. 估值
    val_score = scores.get('valuation_score', 0) # Note: key might vary, check raw data usage if needed
    dim_desc.append(f"Panel 5 (Value): Balance scale sketch")

    blocks_text = ", ".join(dim_desc)

    prompt = (
        f"(masterpiece, best quality), (vertical:1.2), (aspect ratio: 9:16), (sketch style), (hand drawn), (infographic)\n\n"
        f"Create a TALL VERTICAL PORTRAIT IMAGE (Aspect Ratio 9:16) HAND-DRAWN SKETCH style stock market sentiment infographic poster.\n\n"
        f"**Layout Structure**:\n"
        f"1. **Top Section**: A large vintage MAIN GAUGE (Speedometer style) pointing to {index_value} ({sentiment_level}).\n"
        f"2. **Middle Section**: 5 distinct rectangular DATA BLOCKS/PANELS arranged in a grid below the gauge.\n"
        f"   - {blocks_text}\n"
        f"3. **Background**: {theme['atmosphere']}, aged paper texture, ink sketch lines.\n\n"
        f"**Visual Details**:\n"
        f"- Style: Da Vinci engineering sketch, complex mechanical details, infographic layout.\n"
        f"- Color Palette: {theme['mood']} tones (Mainly {color} highlights) on parchment paper.\n"
        f"- Textures: Crosshatching, ink splatters, rough paper grain.\n"
        f"- No digital text, just visual representations of data.\n\n"
        f"--ar 9:16 --style raw --v 6"
    )
    return prompt


def generate_image_prompt(sentiment_result: Dict[str, Any]) -> str:
    """
    Generate a formatted prompt file content for AI image generation (Midjourney/Stable Diffusion).
    """
    index_value = sentiment_result['index']
    sentiment_level = sentiment_result['sentiment_level']
    color = sentiment_result['color']

    raw_prompt = get_raw_image_prompt(sentiment_result)

    # Map color to visual elements (Chinese for display)
    color_themes_cn = {
        "red": "火红色调，炽热的背景",
        "orange": "橙黄色调，温暖的背景",
        "yellow": "中性色调，平衡的构图",
        "blue": "冷蓝色调，冷静的背景",
        "dark_blue": "深蓝冰冷色调，寒冷的背景"
    }
    theme_cn = color_themes_cn.get(color, "中性色调")

    prompt = f"""# AI绘图提示词 - 市场贪婪恐惧指数可视化 (信息图版)

**风格要求**: 复古手绘风格，竖版信息图海报

---

## Midjourney / Stable Diffusion Prompt

{raw_prompt}

**画面结构**:
1. **顶部核心**: 复古仪表盘，指针指向 {index_value} ({sentiment_level})
2. **中部模块**: 5个独立的数据可视化方块 (代表宽度、趋势、资金、新闻、估值)
3. **整体风格**: 达芬奇手稿风格，机械细节，{theme_cn}

**文字信息** (建议后期PS添加):
- 标题："A股市场情绪指数"
- 日期：{datetime.now().strftime("%Y.%m.%d")}
- 指数值：{index_value}/100

---

## 使用说明
1. 复制英文Prompt到绘图工具
2. 推荐尺寸：1024x1792 (9:16)
"""
    return prompt


def generate_prompts(sentiment_result: Dict[str, Any], output_dir: str):
    """
    Generate and save both analysis and image prompts to files.

    Args:
        sentiment_result: Result from calculate_sentiment_index()
        output_dir: Output directory path (e.g., results/20260204)
    """
    import os

    # Create AI prompts directory
    prompts_dir = os.path.join(output_dir, "AI提示词")
    os.makedirs(prompts_dir, exist_ok=True)

    # Generate prompts
    analysis_prompt = generate_analysis_prompt(sentiment_result)
    image_prompt = generate_image_prompt(sentiment_result)

    # Save analysis prompt
    analysis_file = os.path.join(prompts_dir, "市场情绪指数_分析_Prompt.txt")
    with open(analysis_file, 'w', encoding='utf-8') as f:
        f.write(analysis_prompt)
    print(f"✅ Saved analysis prompt: {analysis_file}")

    # Save image prompt
    image_file = os.path.join(prompts_dir, "市场情绪指数_配图_Prompt.txt")
    with open(image_file, 'w', encoding='utf-8') as f:
        f.write(image_prompt)
    print(f"✅ Saved image prompt: {image_file}")

    # Also save a summary JSON for reference
    import json
    summary_file = os.path.join(output_dir, "市场情绪指数.json")
    summary_data = {
        "timestamp": sentiment_result['raw_data']['timestamp'],
        "index": sentiment_result['index'],
        "sentiment_level": sentiment_result['sentiment_level'],
        "score_breakdown": sentiment_result['score_breakdown']
    }
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved summary: {summary_file}")


if __name__ == "__main__":
    # Test prompt generation
    test_result = {
        "index": 65.5,
        "sentiment_level": "贪婪",
        "color": "orange",
        "score_breakdown": {
            "market_breadth": 8.5,
            "indices_trend": 4.2,
            "news_sentiment": 2.3,
            "money_flow": 0.5
        },
        "raw_data": {
            "timestamp": "2026-02-04 14:30:00",
            "indices": {
                "上证50": 1.2,
                "沪深300": 0.8,
                "中证500": 1.5,
                "中证2000": 2.1
            },
            "limit_up_count": 45,
            "limit_down_count": 8,
            "news_sentiment": {
                "bullish_count": 12,
                "bearish_count": 5,
                "neutral_count": 20,
                "bullish_news": ["政策利好刺激市场", "科技股集体上涨"],
                "bearish_news": ["外围市场承压"]
            },
            "sector_flow": {
                "net_inflow": 5.2e9,
                "inflow_sectors": [
                    {"名称": "半导体", "净额": 1.5e9},
                    {"名称": "新能源", "净额": 1.2e9}
                ],
                "outflow_sectors": [
                    {"名称": "房地产", "净额": -0.8e9}
                ]
            }
        }
    }

    print("=== Analysis Prompt ===")
    print(generate_analysis_prompt(test_result))
    print("\n" + "="*80 + "\n")
    print("=== Image Prompt ===")
    print(generate_image_prompt(test_result))
