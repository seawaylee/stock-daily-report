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
4. **AI Content Generation**: Produces prompts for images and copywriting for social media (Xiaohongshu).

## Execution

### 1. Prerequisites
- **OS**: macOS
- **Environment**: Conda env `stock311` (Python 3.11)
- **Project Root**: `/Users/NikoBelic/Documents/IdeaProjects/stock-daily-report`

### 2. Standard Daily Run
To run the complete workflow for the current day:

```bash
cd /Users/NikoBelic/Documents/IdeaProjects/stock-daily-report
./scripts/run.sh all
```

This script sequentially executes:
1. `fish_basin` (Indices & Sectors)
2. `b1` (Stock Selection)
3. `ladder` (Limit-Up Ladder)
4. `sector_flow` (Fund Flow - *Note: Check if enabled*)

### 3. Module-Specific Execution
If a specific module fails or needs regeneration, run them individually:

- **Fish Basin Only**: `./scripts/run.sh fish_basin`
- **Ladder Only**: `./scripts/run.sh ladder`
- **B1 Selection Only**: `./scripts/run.sh b1`

## Verification Checklist
Verify outputs in `results/<TODAY_DATE>/` (e.g., `results/20260123/`):

| Module | Critical Output Files |
|--------|----------------------|
| **Fish Basin** | `趋势模型_指数.xlsx`<br>`趋势模型_题材.xlsx`<br>`AI提示词/趋势模型_指数_Prompt.txt`<br>`AI提示词/趋势模型_题材_Prompt.txt` |
| **Ladder** | `AI提示词/涨停天梯_Prompt.txt` |
| **B1 Selection** | `agent_outputs/result_analysis.txt`<br>`agent_outputs/result_xiaohongshu.txt`<br>`AI提示词/趋势B1选股_Prompt.txt` |

## Troubleshooting Guide

### Data Freshness (Date Mismatch)
- The system prioritizes **EastMoney (EM)** data for real-time accuracy.
- If `趋势模型_题材.xlsx` shows yesterday's date, verify `modules/fish_basin/fish_basin_sectors.py` logic (Freshness Check enabled).
- **Fix**: Re-run `./scripts/run.sh fish_basin`.

### Network/Proxy Issues
- `akshare` relies on Sina/EM/THS APIs. If you see updates failing:
  - Check internet connection.
  - Disable VPN/Proxy if specific domestic APIs (like EastMoney) are blocking foreign IPs.
  - The scripts have built-in retry logic (3 attempts).

### AI Generation Delays
- The B1 module simulates AI processing locally if the external Agent is not connected.
- Check `results/.../agent_tasks/` to see the generated prompts.
