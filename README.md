# Stock Daily Report System (AI Agent)

An automated AI-driven stock analysis system that generates daily market reports, stock selections, and visual prompts for content creation.

## 🚀 Features (13+ Modules)

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
11. **Market Sentiment (市场情绪)**: Greed & Fear Index, Market Temperature analysis.
12. **Close Report (收盘速报)**: Auto-generates end-of-day infographic prompt with indices, turnover, and LLM commentary.
13. **Automated Media (多媒体生成)**: Auto-generates Podcasts (Audio), Videos, and Cover Images for reports.

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

# Earnings Analysis & Prompt
python main.py earnings
python main.py earnings_prompt

# Weekly Preview
python main.py weekly_preview

# Sector Capital Flow
python main.py sector_flow

# Market Sentiment
python main.py sentiment

# Close Report Prompt (收盘速报)
python main.py close_report

# Fish Basin Trend
python main.py fish_basin
```

### 3. After-Close Auto Email (Trade Days)
Run selected close-time modules and send attachments by email:
```bash
# Manual run (today)
bash scripts/run_after_close.sh

# Manual run (specific date)
bash scripts/run_after_close.sh --date 20260213

# Dry run (no email send)
python scripts/after_close_workflow.py --date 20260213 --dry-run
```

Install local `launchd` scheduler (Mon-Fri 15:10):
```bash
bash scripts/install_close_launchd.sh
launchctl list | grep com.stock_daily_report.after_close
```

Scheduler logs:
- `logs/after_close_scheduler.out.log`
- `logs/after_close_scheduler.err.log`

Notes:
- Workflow checks A-share trade calendar and skips non-trade days automatically.
- Default recipient is `13522781970@163.com` (override with `--recipient`).
- Attachments are collected from `results/YYYYMMDD/` and `results/YYYYMMDD/AI提示词/`.

## 📂 Output Structure
All results are saved in `results/YYYYMMDD/`:
- `AI提示词/`: Generated Prompts for AI Image Generation (Midjourney/Stable Diffusion).
  - `趋势Model.txt`, `趋势B1选股_Prompt.txt`, `涨停天梯_Prompt.txt`, etc.
- `agent_outputs/`: AI Analysis Reports (`result_analysis.txt`).
- `mp3/`: Generated Podcast Audio files.
- `video/`: Generated Short Videos.
- `scripts/`: Podcast Scripts.
- `selected_top10.json`: Raw data for selected stocks.

## ⚙️ Configuration
- **Environment**: Python 3.11 (Managed via Conda `stock311`)
- **Dependencies**: `akshare`, `pandas`, `requests`, `numpy`, etc.
- **Settings**: `common/config.py` (Concurrency, Market Cap filters).

### Mail Environment Variables (`.env`)
- `MAIL_SMTP_HOST` (default: `smtp.163.com`)
- `MAIL_SMTP_PORT` (default: `465`)
- `MAIL_USE_SSL` (`1/0`, default: `1`)
- `MAIL_SMTP_USER` (required)
- `MAIL_SMTP_PASS` (required, SMTP authorization code)
- `MAIL_FROM` (optional, default: `MAIL_SMTP_USER`)
- `MAIL_ATTACHMENT_PREFIX_DATE` (`true/false`, default: `false`)
- `MAIL_ATTACHMENT_USE_CHINESE` (`true/false`, default: `false`)

Attachment naming behavior:
- Default (`MAIL_ATTACHMENT_USE_CHINESE=false`): ASCII-safe names for better mail client compatibility.
- If `MAIL_ATTACHMENT_USE_CHINESE=true`: use original Chinese filenames.
- If `MAIL_ATTACHMENT_PREFIX_DATE=true`: prepend `YYYYMMDD_` to attachment names.

## 📝 Developer Notes
- **Prompt Generation**: Most modules now self-contain their prompt generation logic or use helpers in `modules/`.
- **Date Handling**: `main.py` has logic to handle late-night execution (referring to the previous day).
