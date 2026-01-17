# 📈 Stock AI Analysis & Report Generator

这是一个自动化的A股选股、分析及内容生成工具。它结合了传统量化指标（KDJ, RSI）与AI大模型（Gemini/OpenAI）来生成每日复盘报告和小红书文案。

## 🚀 快速开始

### 1. 执行选股与分析
运行主程序：
```bash
python run_ai_analysis.py
```
**脚本执行流程：**
1.  **数据获取**：拉取最新的A股日线数据。
2.  **量化选股**：根据策略（超卖反弹、回踩支撑等）筛选股票。
    -   *默认配置：并发100线程，仅测试前500只股票（可修改）。*
3.  **AI分析**：调用大模型分析Top 10股票的题材与技术面。
4.  **内容生成**：
    -   生成 **小红书文案** (`xiaohongshu_*.txt`)
    -   生成 **图片提示词** (`prompts_*.md`)

### 2. 生成海报图片 (必须步骤)
**⚠️ 注意：脚本仅生成提示词，不直接生成图片。**
请按照以下步骤生成配图：

1.  打开生成的提示词文件：`results/YYYYMMDD/prompts_YYYYMMDD_*.md`
2.  找到 **"图片生成 Prompt"** 章节。
3.  复制对应的英文 Prompt。
4.  **操作**：
    -   将 Prompt 发送给 **DALL-E 3** 或 **Midjourney**。
    -   或者直接告诉 **本Agent**："请根据最新的 Prompt 帮我生成图片"。
5.  **检查要点**：
    -   日期必须是 **今日日期**。
    -   标题包含 "**AI大模型量化**" 和 "**今日精选 Top 10**"。
    -   底部文字 "**次日关注进场**"。

---

## 📂 输出文件说明
所有结果保存在 `results/YYYYMMDD/` 目录下：

| 文件名 | 说明 | 用途 |
| :--- | :--- | :--- |
| `selected_*.json` | 原始选股结果 | 数据备份/调试 |
| `stock_list_summary_*.txt` | 私信汇总列表 | 包含股票代码、行业及命中规则，适合发送给私信用户 |
| `xiaohongshu_*.txt` | 小红书文案 | **核心产出**，直接复制发布 |
| `ai_analysis_*.md` | AI分析报告 | 详细的逻辑分析与板块点评 |
| `prompts_*.md` | AI提示词记录 | 记录所有发给AI的指令，用于生成图片或调试 |

## ⚙️ 配置修改
编辑 `run_ai_analysis.py` 文件头部：

- **`MAX_WORKERS`**: 并发线程数（默认100，机器性良好可调至300+）。
- **`MIN_MARKET_CAP`**: 最小市值过滤（单位：亿）。
- **全市场扫描**：
  搜索并注释掉/删除以下代码以扫描全市场：
  ```python
  # Limit to 500 stocks as requested
  stock_list = stock_list.head(500)
  ```

## 📝 维护指南
- **API Key**: 确保脚本中的 `api_key` 和 `base_url` 有效。
- **依赖库**: 主要依赖 `akshare`, `pandas`, `openai`。
