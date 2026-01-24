---
name: daily_stock_reporter
description: Execute the full daily stock analysis and content generation workflow for A-shares/HK/US markets.
---

# Daily Stock Reporter

This skill encapsulates the workflow for generating the daily stock market analysis report within the `stock-daily-report` project.

## Capabilities
1. **Trend Analysis (Fish Basin Model)**: Analyzes Indices and Industry Sectors using MA20 deviation.
2. **Market Ladder**: Generates the "Limit-Up Ladder" (涨停天梯) visualization data.
3. **Stock Selection (B1 Strategy)**: Selects top stocks based on volume and trend, then uses AI for deep analysis.
4. **Market Calendar**: IPOs, Suspensions, and Next Week Preview.
5. **Abnormal Alert**: Regulatory warnings (20% deviation) and "Dragon Tiger Board" analysis.
6. **Core News Monitor**: Real-time "Important News Selection" and "Weekly Focus" from EastMoney 7x24.
7. **Weekly Events Preview**: Next week's major market events, policy catalysts, and sector analysis (Friday-Sunday only).
8. **AI Content Generation**: Produces prompts for images and copywriting for social media (Xiaohongshu).

## Execution

### 1. Prerequisites
- **OS**: macOS
- **Environment**: Conda env `py311` (Python 3.11)
- **Project Root**: `/Users/seawaylee/Documents/github/stock-daily-report`

### 2. Standard Daily Run
To run the complete workflow for the current day:

```bash
cd /Users/seawaylee/Documents/github/stock-daily-report
./scripts/run.sh all
```

**Auto-Scheduling Logic:**
- **Monday - Thursday**: Runs Daily modules only.
- **Friday - Sunday**: Runs Daily modules AND Weekly Summary modules (Weekly News, Next Week Calendar).

### 3. Module-Specific Execution
If a specific module fails or needs regeneration, run them individually:

- **Fish Basin Only**: `./scripts/run.sh fish_basin`
- **Ladder Only**: `./scripts/run.sh ladder`
- **B1 Selection Only**: `./scripts/run.sh b1`
- **Calendar Only**: `./scripts/run.sh calendar`
- **Abnormal Alert**: `./scripts/run.sh abnormal`
- **Core News Only**: `./scripts/run.sh core_news`
- **Weekly Preview Only**: `./scripts/run.sh weekly_preview`

## Verification Checklist
Verify outputs in `results/<TODAY_DATE>/` (e.g., `results/20260124/`):

| Module | Critical Output Files | Frequency |
|--------|----------------------|-----------|
| **Fish Basin** | `趋势模型_指数.xlsx`<br>`趋势模型_题材.xlsx`<br>`AI提示词/趋势模型_指数_Prompt.txt`<br>`AI提示词/趋势模型_题材_Prompt.txt` | Daily |
| **Ladder** | `AI提示词/涨停天梯_Prompt.txt` | Daily |
| **B1 Selection** | `agent_outputs/result_analysis.txt`<br>`AI提示词/趋势B1选股_Prompt.txt` | Daily |
| **Calendar** | `明日A股日历_Prompt.txt`<br>`下周A股日历_Prompt.txt` (Fri-Sun) | Daily / Weekly |
| **Abnormal** | `异动监管预警_Prompt.txt` | Daily |
| **Core News** | `核心要闻_Prompt.txt`<br>`本周要闻_Prompt.txt` (Fri-Sun) | Daily / Weekly |
| **Weekly Preview** | `weekly_preview_prompt_YYYYMMDD.txt` (Fri-Sun) | Weekly |

## Troubleshooting Guide

### Data Freshness
- The system prioritizes **EastMoney (EM)** data for real-time accuracy.
- If data seems stale, re-run with `--force` (if supported) or delete the day's `results` folder.

### Network Issues
- `All modules use `common.network` to suppress retry logs but have built-in retries (3 attempts).
- If EastMoney API timeouts (common on weekends), just re-run the specific module.

### Prompt Formatting
- All outputs are optimized for "Hand-drawn/Vintage" aesthetic (#F5E6C8 background).
- If icons appear (e.g. 💚) where they shouldn't, check `modules/core_news/core_news_monitor.py` footer logic.
