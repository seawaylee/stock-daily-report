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
   - 格式：`[股票名称] ([代码]) | [行业/题材]`
   - 推荐理由：另起一行，3-5句话，结合技术面与基本面题材。
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
Line 1: #[index] [name_masked] | [code_masked] | [industry_icon] [industry] (smaller font size for industry)
Line 2: [signal_icon] [signals] | J=[J] RSI=[RSI]

Industry icons: 🔋 batteries, ✈️ aerospace, 🔌 electronics, 🤖 robotics, 🚗 automotive, 🏭 machinery, 📦 logistics
Signal icons: Use ONE of 🚀 OR 🔥 OR 📈


**FOOTER CONTENT (Bottom Area):**
Please render the following content at the bottom. Use these EXACT 3 lines (translate/summarize fit if needed):

1. **Top Line (Summary)**: Extract key market summary from here: "{footer_content}". Keep it under 20 words.
2. **Middle Line (Strategy)**: Extract key focus stocks/strategy from here: "{footer_content}". Keep it under 15 words.
3. **Bottom Line (CALL TO ACTION)**: "每日盘后分享AI量化策略的高值博率股票，点赞关注不迷路"

**IMPORTANT**: 
- All footer text MUST be in CHINESE.
- Ensure the CTA line is exactly as specified above.
- Remove Markdown symbols like `**`.


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
