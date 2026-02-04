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


def generate_image_prompt(sentiment_result: Dict[str, Any]) -> str:
    """
    Generate a prompt for AI image generation (Midjourney/Stable Diffusion).
    
    Args:
        sentiment_result: Result from calculate_sentiment_index()
    
    Returns:
        Image generation prompt string
    """
    index_value = sentiment_result['index']
    sentiment_level = sentiment_result['sentiment_level']
    color = sentiment_result['color']
    
    # Map color to visual elements
    color_themes = {
        "red": {
            "atmosphere": "火红色调，炽热的背景，火焰元素",
            "mood": "狂热、兴奋",
            "elements": "上升的箭头、火焰、红色渐变"
        },
        "orange": {
            "atmosphere": "橙黄色调，温暖的背景",
            "mood": "乐观、积极",
            "elements": "向上的曲线、暖色光芒"
        },
        "yellow": {
            "atmosphere": "中性色调，平衡的构图",
            "mood": "平静、观望",
            "elements": "水平线、平衡的天平"
        },
        "blue": {
            "atmosphere": "冷蓝色调，冷静的背景",
            "mood": "谨慎、担忧",
            "elements": "下降的曲线、冷色调阴影"
        },
        "dark_blue": {
            "atmosphere": "深蓝冰冷色调，寒冷的背景，冰霜元素",
            "mood": "恐慌、极度悲观",
            "elements": "下坠的箭头、冰晶、深蓝渐变"
        }
    }
    
    theme = color_themes.get(color, color_themes["yellow"])
    
    # Determine pointer position (0-100 mapped to gauge arc)
    position_desc = f"指针指向{index_value}刻度位置"
    
    prompt = f"""# AI绘图提示词 - 市场贪婪恐惧指数可视化

**风格要求**: 复古手绘风格，保持项目视觉一致性

---

## Midjourney / Stable Diffusion Prompt

A vintage hand-drawn illustration of a sentiment gauge/thermometer for stock market analysis, {theme['atmosphere']}, aged paper texture, ink sketch style --ar 16:9 --style raw --v 6

**主题**: 市场情绪温度计/仪表盘

**核心元素**:
- 一个半圆形或垂直的复古仪表盘，刻度从0到100
- {position_desc}，当前指向"{sentiment_level}"区域
- 仪表盘分区标注：
  - 0-30: 极度恐惧 (深蓝色)
  - 30-45: 恐惧 (蓝色)
  - 45-55: 中性 (黄色)
  - 55-70: 贪婪 (橙色)
  - 70-100: 极度贪婪 (红色)

**视觉风格**:
- 手绘墨水线条，复古铜版画质感
- 泛黄的纸张背景，边缘有岁月痕迹
- {theme['atmosphere']}
- 情绪氛围：{theme['mood']}
- 装饰元素：{theme['elements']}

**文字信息** (嵌入画面):
- 标题："A股市场情绪指数" (中文书法字体或复古英文)
- 日期：{datetime.now().strftime("%Y.%m.%d")}
- 指数值：{index_value}/100
- 情绪等级：{sentiment_level}

**构图**:
- 主体居中，仪表盘占画面60%
- 背景使用{theme['elements']}烘托氛围
- 四角可添加复古装饰框或印章元素

**禁止元素**:
- 现代感设计、光滑渐变
- 3D渲染效果
- 过于写实的照片风格
- 卡通或可爱风格

---

## 中文提示词 (适用于国内AI绘图工具)

复古手绘风格的股市情绪仪表盘插画，{theme['atmosphere']}，泛黄纸张质感，墨水线稿风格，16:9画幅

**画面描述**:
一个精美的半圆形情绪指数表盘，刻度清晰标注0-100，指针指向{index_value}位置({sentiment_level}区域)。表盘分为五个色区：深蓝(极度恐惧)、蓝色(恐惧)、黄色(中性)、橙色(贪婪)、红色(极度贪婪)。

整体采用{theme['atmosphere']}，营造{theme['mood']}的情绪氛围。画面使用手绘铜版画技法，复古墨水线条，泛黄羊皮纸背景。

装饰元素包括：{theme['elements']}，四周点缀复古花纹边框。

画面顶部书法标题"市场情绪指数"，底部标注日期"{datetime.now().strftime("%Y年%m月%d日")}"和数值"{index_value}/100 - {sentiment_level}"。

**风格参考**: 19世纪科学仪器插图、复古股票行情图、航海图表美学

---

## 使用说明
1. 将上述英文prompt复制到Midjourney或Stable Diffusion
2. 或使用中文提示词在国内AI绘图平台（如文心一格、通义万相）
3. 根据生成效果微调参数，保持与项目其他模块的视觉一致性
4. 推荐尺寸：1920x1080 或 1600x900
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
