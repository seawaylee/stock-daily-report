import json
import numpy as np

# JSON编码器，用于处理numpy数据类型
class NumpyEncoder(json.JSONEncoder):
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

def get_analysis_prompt(stocks_info):
    """生成Top10分析的Prompt"""
    return f"""你是一位资深量化分析师。以下是通过"AI模型"策略选出的股票列表，该策略主要捕捉超卖反弹和回踩支撑的买入信号。

选出的股票数据：
{json.dumps(stocks_info, ensure_ascii=False, indent=2, cls=NumpyEncoder)}

请从中选出Today Top10值得关注的股票，评估标准：
1. 信号强度（多信号叠加更佳）
2. 技术指标位置（KDJ/RSI超卖程度）
3. **【选股偏好】尽量不选688开头的科创板股票**，除非其他标的质量明显不足。
4. **【题材分布】题材尽量分散，不要扎堆**！每类细分题材/行业入选股票不超过2只。
5. **【重要】所属行业/题材**（由于数据源缺失，请你根据股票代码和名称，利用你的知识库补充其所属的行业和核心题材）

请输出：
1. Top10股票排名
   - 格式：`[股票名称] ([代码]) | [行业/题材] | [推荐理由]`
   - 理由要求：3-5句话，结合技术面与基本面题材。
2. 整体市场分析（2-3句话）
3. 风险提示
4. **【重要】图片生成专用摘要**
   - 目标：用于生成今日复盘海报的底部文案。
   - 要求：极度精炼，每行不超过15字。
   - 格式：
     📍 **整体复盘**
     [Emoji] [短语]: [简短说明]
     [Emoji] [短语]: [简短说明]
     [Emoji] [短语]: [简短说明]
     
     💡 **次日策略**
     [Emoji] [短语]: [简短说明]
     [Emoji] [短语]: [简短说明]
     [Emoji] [短语]: [简短说明]

注意：

3. 风险提示

注意：
1. 这是技术分析参考，不构成投资建议。题材信息请务必准确。
2. **【格式要求】整体市场分析、次日交易策略、风险提示 部分，严禁使用Markdown加粗（**），保持纯文本。**"""

def get_xiaohongshu_prompt(gemini_analysis, masked_stocks_json, current_date):
    """生成小红书文案Prompt"""
    return f"""请将以下股票分析报告改写成小红书风格的文案。

原始分析：
{gemini_analysis}

【脱敏股票列表】（使用此列表中的脱敏名称和代码）：
{masked_stocks_json}

要求：
1. **风格灵魂**：必须极度"小红书化"！大量使用Emoji，段落短促，语气兴奋、专业且硬核。
2. **Emoji使用规范**：
   - 标题前后必须加Emoji (e.g., 🚀/🔥/💰).
   - 每一段开头必须加Emoji.
   - 重点词汇前后加Emoji.
   - 推荐使用：🚀 (潜力), 💰 (买点), 📉 (超卖), 🎯 (目标), ⚠️ (风险), 🤖 (AI分析).
3. **【重要】股票脱敏处理**：
   - 直接使用上面列表中的 name_masked 和 code_masked 字段
   - 示例格式：华盛LD (6883**)
4. **标题**：吸引眼球，严格控制在20个字符以内。
5. **结构要求**：
   - **标题行**：日期 + 核心主题 + Emoji
   - **开头**：各位交易员，AI量化今日扫描全场！ ({current_date})
   - **中间（核心部分）**：列出Top10股票。**必须严格执行2行格式**，每只股票占2行：
     
     1️⃣ [股票名脱敏] ([代码脱敏]) | 🏷️[行业]
     👉 [核心理由简述，30字以内，重点写技术面优势]

     2️⃣ ... (以此类推)
   
   - **结尾**：风险提示 + 互动 + 关注引导。
6. **术语替换**：将 "B" 或 "B1" 替换为 "买点"。
7. **字数限制**：全文字数必须严格控制在 **1000字以内**。精简核心理由，去除冗余修饰。
7. **禁词**：绝对不要出现 "知行"、"东方财富" 等具体策略或来源名称。
7. **人设**：AI量化分析师（机器人语气，但生动）。
8. **严禁Markdown**：不要用 `**`, `###`, `- ` 等Markdown符号。只用Emoji和空行分段。
9. **文末话题**：#AI选股 #量化交易 #A股 #每日复盘
10. **字数**：1000字以内。
11. **称呼**：统称读者为"各位交易员" (Traders)，严禁使用"家人们"、"集美们"等小红书常见称呼。
12. **必须包含**："次日关注进场" 的提示。

请直接输出文案内容。"""

def get_image_prompt(stock_summary, footer_content, current_date):
    """生成图片生成Prompt"""
    return f"""(masterpiece, best quality), (vertical:1.2), (aspect ratio: 10:16), (sketch style), (hand drawn), (infographic)

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


Left: Robot mascot wearing red scarf, holding gear + rocket, thumbs-up, hand-sketched
Right: Speech bubble: "先进制造+军工+新能源三大主线齐发力！KDJ超卖区间 短期修复窗口已开启💰"
Center: "AI大模型量化策略" + "{current_date}"

10 stock cards (5 per column) in a 2-Column Grid:
Left column: Pale blue background with paper texture
Right column: Pale yellow background with paper texture

**DESENSITIZATION RULES:**
All cards must use masked names and codes.

**CONTENT TO RENDER:**
{json.dumps(stock_summary, ensure_ascii=False, indent=2, cls=NumpyEncoder)}

For each stock, create card with:
Line 1: #[index] [name_masked] | [code_masked]
Line 2: [industry_icon] [industry]
Line 3: [signal_icon] [signals] | J=[J] RSI=[RSI]

Industry icons: 🔋 batteries, ✈️ aerospace, 🔌 electronics, 🤖 robotics, 🚗 automotive, 🏭 machinery, 📦 logistics
Signal icons: Use ONE of 🚀 OR 🔥 OR 📈


**FOOTER CONTENT (Bottom Area):**
Please render the following content at the bottom, BUT:
1. **SUMMARIZE IT**: Condense the text below into 1-2 short, punchy sentences suitable for a poster footer. Do NOT paste long paragraphs.
2. **CLEAN IT**: Remove any Markdown symbols like `**` or `##`.
3. **DESENSITIZE**: Ensure no full stock names appear (should already be masked, but double check).

{footer_content}


**ENHANCED HAND-DRAWN STYLE:**
1. Paper texture visible throughout (sketch paper grain)
2. All lines with wobbles, varying thickness
3. Shading only via crosshatching/stippling - NO smooth gradients  
4. Hand-lettered text with irregularities
5. Background: Red-gold gradient with visible pencil strokes
6. Card borders: Hand-drawn rounded rectangles
7. Overall: Professional architect sketch, NOT polished digital

TECHNICAL:
- Aspect ratio: 10:16 (Vertical Phone Wallpaper)
- Resolution: 1600x2560 (2K Vertical)
- Chinese text must be clear and readable
"""
