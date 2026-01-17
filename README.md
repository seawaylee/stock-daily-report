# 东方财富 AI量化选股助手 (Zhixing B1 Strategy)

这是一个全自动化的AI量化选股与内容生成工具。它结合了东方财富的经典指标（“知行B1”策略）与Google Gemini大模型的分析能力，每日自动挖掘市场潜力股，并生成专业的小红书文案和可视化图表。

## 📋 功能特点

*   **全自动选股**: 每日扫描全A股市场（剔除ST、小市值），基于7大核心信号筛选潜力股。
*   **AI深度分析**: 使用Gemini 2.5模型对Top10潜力股进行深度解读，生成推荐理由。
*   **小红书文案**: 自动生成符合小红书调性的爆款文案（纯文本 + Emoji + 流量标签）。
*   **智能信息图**: 自动生成“AI量化分析师”风格的竖版长图，包含所有推荐股票。
*   **自动归档**: 所有产出文件自动按日期归档，井井有条。
*   **私信汇总**: 生成便于私信发送的纯文本选股列表。

## 🚀 每日运行步骤

1.  **打开终端**: 进入项目目录 `d:\git\stock-daily-report`。
    ```powershell
    cd d:\git\stock-daily-report
    ```

2.  **运行脚本**:
    ```powershell
    python run_ai_analysis.py
    ```

3.  **等待完成**: 脚本会自动执行以下步骤（约需1-3分钟）：
    *   [1/4] 获取最新股票列表
    *   [2/4] 并发计算全市场技术指标与信号
    *   [3/4] 筛选Top10并保存数据
    *   [4/4] 调用Gemini生成分析报告、文案与图片提示词

4.  **获取结果**: 运行完成后，所有文件会保存在 `results/YYYYMMDD` 目录下（例如 `results/20260118`）：
    *   `xiaohongshu_YYYYMMDD_HHMMSS.txt`: **小红书发布文案** (直接复制使用)
    *   `stock_analysis_infographic.png`: **配图** (竖版长图)
    *   `stock_list_summary_YYYYMMDD_HHMMSS.txt`: **私信汇总列表** (用于回复粉丝)
    *   `ai_analysis_YYYYMMDD_HHMMSS.md`: 完整AI分析报告 (内部参考)
    *   `selected_YYYYMMDD_HHMMSS.json`: 选股数据源文件

## ⚙️ 环境配置

如果换了电脑或重装系统，请确保：

1.  安装 Python 3.8+
2.  安装依赖库:
    ```bash
    pip install -r requirements.txt
    # 额外依赖
    pip install openai
    ```
3.  确保 `run_ai_analysis.py` 中的 API Key 配置正确。

## � 文案与图片生成规范 (重要)

为确保输出内容符合小红书发布要求及专业人设，脚本已内置以下规则，请勿随意修改：

### 1. 小红书文案规范
*   **字数限制**: 正文 < 800字，标题 < 20字。
*   **结构要求**:
    *   **开头**: 极简，一句话入题 (e.g., "AI量化发现今日超卖机会")。
    *   **中间**: 直接列出Top10股票及核心理由。
    *   **结尾**: 风险提示 + 关注引导 (CTA)。
*   **人设语气**: "AI量化交易员"，硬核、专业、理性。**严禁**使用"姐妹"、"宝子"等女性化称呼，统称"交易员们"。
*   **格式**: 纯文本 + Emoji。**严禁**使用Markdown (###, **, -)。
*   **术语**: 策略名统一为"AI大模型量化"，不提"知行"。

### 2. 信息图(Infographic)规范
*   **尺寸**: 竖版 9:16 (适合手机全屏)。
*   **内容**: 必须包含完整Top10股票列表。
*   **术语替换**: 图中所有 "B" 或 "B1" 信号必须替换为 **"买点"** (e.g., "原始买点", "超卖缩量买点")。
*   **行动号召**: 底部必须显著展示 **"次日关注进场"**。
*   **语言**: 除 RSL/KDJ 指标外，全中文手绘风格。

## �📂 目录结构

```
stock-daily-report/
├── results/                # 结果输出目录
│   ├── 20260118/           # 按日期归档
│   │   ├── xiaohongshu_*.txt
│   │   ├── stock_analysis_infographic.png
│   │   └── ...
│   └── ...
├── run_ai_analysis.py      # 主程序脚本
├── indicators.py           # 技术指标计算
├── signals.py              # 选股信号逻辑
├── data_fetcher.py         # 数据获取模块
└── requirements.txt        # 依赖列表
```

## ❓ 常见问题

*   **Q: 脚本运行报错 `429 Too Many Requests`?**
    *   A: AI模型调用频繁，请稍等1-2分钟后重新运行脚本。脚本会智能跳过已完成的选股步骤，直接进行分析。

*   **Q: 图片没有生成?**
    *   A: 脚本目前仅生成图片提示词（Prompt）。你需要将终端输出的Prompt复制到Midjourney或DALL-E 3中生成，或者等待Antigravity自动生成（如果仍在会话中）。
    *   *注：当前版本已集成Antigravity自动绘图功能，但在脚本独立运行时可能需要手动操作。*

*   **Q: 想修改文案风格?**
    *   A: 打开 `run_ai_analysis.py`，搜索 `def generate_xiaohongshu_post`，修改里面的 `prompt` 变量即可。
