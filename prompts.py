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

def get_xiaohongshu_prompt(gemini_analysis, masked_stocks_json, current_date):
    """生成小红书文案Prompt（含合规防违规规则）"""
    return f"""请将以下股票分析报告改写成小红书风格的文案。

原始分析：
{gemini_analysis}

【脱敏股票列表】（使用此列表中的脱敏名称和代码）：
{masked_stocks_json}

===========================================
【🚨 合规要求 - 最高优先级 🚨】
===========================================

**核心定位：技术分析学习分享，不是投资建议！**

1. **【严禁投资建议性语言】**：
   - ❌ 禁止使用：买点、卖点、低吸、高抛、进场、建仓、加仓、减仓、止损、止盈
   - ❌ 禁止使用：推荐、建议、适合买入、值得关注、可以入手
   - ❌ 禁止使用：反弹、拉升、龙头、核心标的、首选、必选
   - ❌ 禁止使用：机构看好、主力资金、资金流入
   - ✅ 改用：技术特征、指标表现、形态观察、走势分析、技术面修复

2. **【必须声明定位】**：
   - 开头必须包含："📚 技术指标学习分享，仅供研究参考"
   - 结尾必须包含："📌 以上仅为AI技术指标扫描结果，不构成任何投资建议"
   - 结尾必须包含："📌 股市有风险，投资需谨慎，请独立判断"

3. **【改写风格】**：
   - 将"买入信号"改为"技术特征"
   - 将"超卖反弹"改为"超卖区间/技术面修复需求"  
   - 将"支撑位"改为"均线附近"
   - 将"信号叠加"改为"多指标共振"
   - 只描述客观技术指标数值，不做主观判断

4. **【话题标签合规】**：
   - ❌ 禁止：#AI选股 #选股 #买入 #卖出
   - ✅ 使用：#技术分析 #量化学习 #A股研究 #投资笔记

===========================================
【格式要求】
===========================================

1. **Emoji使用**：每段开头加Emoji，使用📊📈📉📖🤖等学习类图标
2. **股票脱敏**：必须使用 name_masked 和 code_masked
3. **标题**：20字以内，定位为"技术学习"而非"选股"
4. **结构**：
   - 标题：🤖[日期] AI量化技术面复盘📊
   - 开头：各位交易员，AI量化今日扫描全场！({current_date})
   - 声明：📚 技术指标学习分享，仅供研究参考
   
   - 每只股票2行：
     1️⃣ [股票名脱敏] ([代码脱敏]) | 📖[行业]
     技术特征：[客观描述KDJ/RSI等指标数值和形态，禁止判断性语言]

   - **【重要】必须包含整体复盘和次日观察（从原始分析的"图片生成专用摘要"部分提取）**：
     
     📍 整体复盘
     [用合规语言改写原始分析中的整体复盘内容，保留3条要点，每条用Emoji开头]
     
     💡 次日观察要点
     [用合规语言改写原始分析中的次日策略内容，保留3条要点，每条用Emoji开头]
     [注意：将"策略"改为"观察要点"，将"低吸"改为"关注技术面变化"，将"加仓"改为"观察量能配合"]

   - 结尾：合规免责声明 + 评论区交流

5. **严禁Markdown**：不用 `**`, `###` 等符号
6. **字数**：900字以内（需要给整体复盘和次日观察留空间）
7. **称呼**：统称"各位交易员"

请直接输出合规文案内容。"""

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
