---
name: daily-review
description: Use when the user asks to "execute daily review", "run daily analysis", "执行今日复盘", or uses /daily-review. Automated workflow to run the full stock analysis system.
---

# Daily Review Workflow

## Overview

This skill automates the daily stock analysis process by executing the main system entry point (`main.py`) and presenting a summary of the generated results. It intelligently handles weekday vs. weekend logic.

## When to Use

- User says "Execute daily review" or "执行今日复盘"
- User says "Run daily analysis"
- User types `/daily-review`

## Workflow

### 1. Pre-Flight Check
- **Date Check**: Identify if today is a weekday or weekend.
  - **Mon-Thu**: Standard Daily Analysis.
  - **Fri**: Daily Analysis + Weekly Preview (handled by `main.py`).
  - **Sat/Sun**: Weekly Review/Preview (handled by `main.py`).

### 2. Execution
- Run the main entry point:
  ```bash
  python3 main.py
  ```
- **Wait** for the process to complete (this may take 2-5 minutes depending on network).

### 3. Verification & Reporting
Once `main.py` finishes:

1.  **Market Sentiment**:
    - Read and display the content of: `results/{YYYYMMDD}/AI提示词/市场情绪_Prompt.txt`
    - This contains the "Greed & Fear Index" and key market indicators.

2.  **Media Generation**:
    - Check for generated media in `results/{YYYYMMDD}/mp3/` and `results/{YYYYMMDD}/video/`.
    - Confirm creation of podcast audio and video summaries.

3.  **Stock Selection (B1 Strategy)**:
    - Check for `results/{YYYYMMDD}/selected_top10.json` or `selected_{YYYYMMDD}_*.json`.
    - If found, list the **Count** of selected stocks and the **Top 3** names.

4.  **Abnormal Alerts**:
    - Check `results/{YYYYMMDD}/AI提示词/异常异动_Prompt.txt`.
    - Briefly summarize if there are major warnings.

## Common Issues

- **Network Timeout**: If `main.py` fails due to network, check `common/data_fetcher.py` cache or retry.
- **Data Missing**: If Prompts are empty, check the logs for `akshare` errors.
