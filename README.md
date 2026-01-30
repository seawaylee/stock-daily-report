# Stock Daily Report System (AI Agent)

An automated AI-driven stock analysis system that generates daily market reports, stock selections, and visual prompts for content creation.

## 🚀 Features (10+ Modules)

This system consists of the following independent modules, typically executed in parallel:

1.  **Fish Basin Trend (趋势鱼盆)**: Market trend analysis (Indices & Sectors) + Strategy generation.
2.  **B1 Stock Selection (B1选股)**: AI-powered stock selection (Top 20) with technical analysis (RSI, J, Signals).
3.  **Sector Flow (资金流向)**: Tracks Smart Money inflows/outflows (Industry & Concept).
4.  **Market Ladder (涨停天梯)**: Visualizes Limit-Up hierarchy (Heights, Board Counts).
5.  **Market Calendar (市场日历)**: Next day's events, IPOs, and important news.
6.  **Earnings Analysis (业绩披露)**: Tracks daily earnings disclosures and forecasts.
7.  **Core News (核心要闻)**: Important macro and market news summary.
8.  **Abnormal Alert (异动预警)**: Monitors significant stock price anomalies.
9.  **Weekly Preview (周刊前瞻)**: (Weekend Only) Strategy for the upcoming week.
10. **Weekly Review (本周要闻)**: (Weekend Only) Summary of the past week.

## 🛠️ Usage

### 1. Run Full Daily Workflow (Recommended)
Automatically detects if it's a weekday or weekend and runs relevant modules.
```bash
python main.py all
```
*Note: If running between 00:00 - 09:00, it automatically defaults to the "Previous Trading Day".*

### 2. Run Individual Modules
```bash
# B1 Stock Selection (generates Top 20 prompt)
python main.py b1

# Market Ladder
python main.py ladder

# Market Calendar (Tomorrow)
python main.py calendar

# Earnings Analysis & Prompt
python main.py earnings
python main.py earnings_prompt

# Sector Capital Flow
python main.py sector_flow

# Fish Basin Trend
python main.py fish_basin
```

## 📂 Output Structure
All results are saved in `results/YYYYMMDD/`:
- `AI提示词/`: Generated Prompts for AI Image Generation (Midjourney/Stable Diffusion).
  - `趋势Model.txt`, `趋势B1选股_Prompt.txt`, `涨停天梯_Prompt.txt`, etc.
- `agent_outputs/`: AI Analysis Reports (`result_analysis.txt`).
- `selected_top10.json`: Raw data for selected stocks.

## ⚙️ Configuration
- **Environment**: Python 3.11 (Managed via Conda `stock311`)
- **Dependencies**: `akshare`, `pandas`, `requests`, `numpy`, etc.
- **Settings**: `common/config.py` (Concurrency, Market Cap filters).

## 📝 Developer Notes
- **Prompt Generation**: Most modules now self-contain their prompt generation logic or use helpers in `modules/`.
- **Date Handling**: `main.py` has logic to handle late-night execution (referring to the previous day).
