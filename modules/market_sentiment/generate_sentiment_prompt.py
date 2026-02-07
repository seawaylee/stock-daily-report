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

    prompt = (
        f"A vintage hand-drawn illustration of a sentiment gauge for stock market analysis, "
        f"{theme['atmosphere']}, aged paper texture, ink sketch style. "
        f"The gauge needle is pointing to {index_value} on a scale of 0 to 100, indicating '{sentiment_level}'. "
        f"Visual elements: {theme['elements']}{visual_extras}. "
        f"Visual style: antique scientific instrument, da vinci sketch, detailed, {theme['mood']} atmosphere. "
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

    prompt = f"""# AI绘图提示词 - 市场贪婪恐惧指数可视化

**风格要求**: 复古手绘风格，保持项目视觉一致性

---

## Midjourney / Stable Diffusion Prompt

{raw_prompt}

**主题**: 市场情绪温度计/仪表盘

**核心元素**:
- 一个半圆形或垂直的复古仪表盘，刻度从0到100
- 指针指向{index_value}刻度位置，当前指向"{sentiment_level}"区域
- 仪表盘分区标注：
  - 0-30: 极度恐惧 (深蓝色)
  - 30-45: 恐惧 (蓝色)
  - 45-55: 中性 (黄色)
  - 55-70: 贪婪 (橙色)
  - 70-100: 极度贪婪 (红色)

**视觉风格**:
- 手绘墨水线条，复古铜版画质感
- 泛黄的纸张背景，边缘有岁月痕迹
- {theme_cn}

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
