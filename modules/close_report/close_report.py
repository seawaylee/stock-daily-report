#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
收盘速报 Prompt 生成模块

输出:
- results/YYYYMMDD/AI提示词/收盘速报_Prompt.txt
"""

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Tuple

try:
    import pandas as pd
except Exception:  # pragma: no cover - optional for minimal test env
    pd = None

INDEX_SYMBOLS = [
    ("上证指数", "sh000001"),
    ("沪深300", "sh000300"),
    ("创业板指", "sz399006"),
]

DEFAULT_SUMMARY = {
    "market_commentary": "指数分化偏强，仓位维持中性，优先低吸主线。",
    "favorable_commentary": "政策催化延续，主线板块仍有轮动机会。",
    "unfavorable_commentary": "高位分化加剧，追涨容易回撤。",
}

SUMMARY_MAX_LEN = {
    "market_commentary": 44,
    "favorable_commentary": 28,
    "unfavorable_commentary": 28,
}


def _format_display_date(date_str: str) -> str:
    dt = datetime.strptime(date_str, "%Y%m%d")
    return f"{dt.year}年{dt.month}月{dt.day}日"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _build_index_item(name: str, code: str, target_date: str) -> Dict[str, float]:
    """
    读取指数收盘值与涨跌幅。
    """
    try:
        if pd is None:
            raise RuntimeError("pandas is required for index snapshot")

        from modules.fish_basin.fish_basin import fetch_data

        df = fetch_data(name, code)
        if df is None or df.empty:
            raise ValueError("empty dataframe")

        if "date" not in df.columns or "close" not in df.columns:
            raise ValueError("missing required columns")

        local_df = df[["date", "close"]].copy()
        local_df["date"] = pd.to_datetime(local_df["date"], errors="coerce")
        local_df["close"] = pd.to_numeric(local_df["close"], errors="coerce")
        local_df = local_df.dropna(subset=["date", "close"])

        cutoff = datetime.strptime(target_date, "%Y%m%d").date()
        local_df = local_df[local_df["date"].dt.date <= cutoff].sort_values("date")

        if local_df.empty:
            raise ValueError("no rows before target date")

        close_value = _safe_float(local_df.iloc[-1]["close"])
        if len(local_df) < 2:
            return {"name": name, "pct_change": 0.0, "close": round(close_value, 2)}

        prev_close = _safe_float(local_df.iloc[-2]["close"])
        pct_change = 0.0 if prev_close == 0 else (close_value - prev_close) / prev_close * 100
        return {"name": name, "pct_change": round(pct_change, 2), "close": round(close_value, 2)}
    except Exception as exc:
        print(f"⚠️ 指数数据获取失败 {name}({code}): {exc}")
        return {"name": name, "pct_change": 0.0, "close": 0.0}


def get_index_snapshot(date_str: str) -> List[Dict[str, float]]:
    return [_build_index_item(name, code, date_str) for name, code in INDEX_SYMBOLS]


def format_turnover_text(volume_data: Dict[str, float]) -> str:
    today = _safe_float(volume_data.get("today_volume"))

    if today <= 0:
        return "暂无数据"

    total_wan_yi = today / 1e12
    return f"{total_wan_yi:.2f}万亿"


def select_news_factors(date_str: str) -> Tuple[str, str]:
    """
    提取一条“有利因素”与一条“不利因素”新闻。
    """
    from modules.core_news.core_news_monitor import (
        calculate_importance,
        clean_text_gentle,
        fetch_eastmoney_data,
        get_sentiment_and_target,
    )

    news_data = fetch_eastmoney_data(target_window_hours=24)
    if not news_data:
        return "暂无显著利好消息。", "暂无显著利空消息。"

    target_day = datetime.strptime(date_str, "%Y%m%d").date()
    daily_news = [item for item in news_data if item.get("time") and item["time"].date() == target_day]
    candidates = daily_news if daily_news else news_data

    bullish_candidates = []
    bearish_candidates = []

    for item in candidates:
        title = (item.get("title") or "").strip()
        if not title:
            continue

        direction, _ = get_sentiment_and_target(title)
        if direction not in ("利多", "利空"):
            continue

        score = calculate_importance(title)
        if score <= 0:
            continue

        cleaned = clean_text_gentle(title)
        if len(cleaned) < 6:
            continue

        row = (score, item.get("time"), cleaned)
        if direction == "利多":
            bullish_candidates.append(row)
        else:
            bearish_candidates.append(row)

    def _sort_key(row: Tuple[int, Any, str]) -> Tuple[int, str]:
        score, ts, _ = row
        ts_text = ts.strftime("%Y-%m-%d %H:%M:%S") if isinstance(ts, datetime) else ""
        return score, ts_text

    bullish_candidates.sort(key=_sort_key, reverse=True)
    bearish_candidates.sort(key=_sort_key, reverse=True)

    favorable_factor = bullish_candidates[0][2] if bullish_candidates else "暂无显著利好消息。"
    unfavorable_factor = bearish_candidates[0][2] if bearish_candidates else "暂无显著利空消息。"
    return favorable_factor, unfavorable_factor


def _build_summary_prompt(report_data: Dict[str, Any]) -> str:
    idx_lines = "\n".join(
        [
            f"- {item['name']}: {item['pct_change']:+.2f}%, 收盘 {item['close']:.2f}"
            for item in report_data["indices"]
        ]
    )

    return f"""你是A股收盘复盘编辑。请基于数据输出简洁、专业、易懂的总结。

要求：
1) market_commentary: 1句话，18-40字，只写结论。
2) favorable_commentary: 1句话，12-24字，只写结论。
3) unfavorable_commentary: 1句话，12-24字，只写结论。
4) 不要编造数据，不要使用markdown，不要输出除JSON之外的任何内容。

今日数据：
{idx_lines}
- 成交额: {report_data["turnover_text"]}
- 有利因素新闻: {report_data["favorable_factor"]}
- 不利因素新闻: {report_data["unfavorable_factor"]}

输出JSON格式：
{{
  "market_commentary": "...",
  "favorable_commentary": "...",
  "unfavorable_commentary": "..."
}}
"""


def _compact_summary_text(text: str, max_len: int) -> str:
    cleaned = re.sub(r"\s+", "", (text or "").strip())
    if not cleaned:
        return ""

    parts = re.split(r"[。！？!?]", cleaned)
    first_sentence = ""
    for part in parts:
        part = part.strip("，,；; ")
        if part:
            first_sentence = part
            break
    if not first_sentence:
        first_sentence = cleaned

    if len(first_sentence) >= max_len:
        first_sentence = first_sentence[: max_len - 1].rstrip("，,；; ")
    if not first_sentence.endswith("。"):
        first_sentence += "。"
    if len(first_sentence) > max_len:
        first_sentence = first_sentence[:max_len]
    return first_sentence


def parse_llm_summary(text: str) -> Dict[str, str]:
    """
    解析LLM返回，兼容 code fence 与额外文本。
    """
    if not text:
        return dict(DEFAULT_SUMMARY)

    candidate = text.strip()
    fence_pattern = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)
    fence_match = fence_pattern.search(candidate)
    if fence_match:
        candidate = fence_match.group(1).strip()

    obj_match = re.search(r"\{[\s\S]*\}", candidate)
    if obj_match:
        candidate = obj_match.group(0)

    try:
        payload = json.loads(candidate)
        if not isinstance(payload, dict):
            raise ValueError("summary payload is not dict")
    except Exception:
        return dict(DEFAULT_SUMMARY)

    result = {}
    for key, fallback in DEFAULT_SUMMARY.items():
        value = payload.get(key, fallback)
        if not isinstance(value, str):
            value = str(value)
        value = value.strip()
        compacted = _compact_summary_text(value if value else fallback, SUMMARY_MAX_LEN[key])
        if not compacted:
            compacted = _compact_summary_text(fallback, SUMMARY_MAX_LEN[key]) or fallback
        result[key] = compacted
    return result


def generate_summary(report_data: Dict[str, Any]) -> Dict[str, str]:
    from common.llm_client import chat_completion

    prompt = _build_summary_prompt(report_data)
    system_prompt = "你是严谨的中文财经编辑，擅长把结构化行情数据压缩成短文本要点。"
    raw = chat_completion(
        prompt,
        system_prompt=system_prompt,
        temperature=0.2,
    )
    return parse_llm_summary(raw or "")


def collect_report_data(date_str: str) -> Dict[str, Any]:
    from modules.market_sentiment.market_sentiment import get_market_volume

    indices = get_index_snapshot(date_str)
    volume_data = get_market_volume(date_str)
    turnover_text = format_turnover_text(volume_data)
    favorable_factor, unfavorable_factor = select_news_factors(date_str)

    report_data = {
        "date_str": date_str,
        "display_date": _format_display_date(date_str),
        "indices": indices,
        "turnover_text": turnover_text,
        "favorable_factor": favorable_factor,
        "unfavorable_factor": unfavorable_factor,
    }
    report_data["summary"] = generate_summary(report_data)
    return report_data


def build_image_prompt(report_data: Dict[str, Any]) -> str:
    summary = report_data["summary"]
    idx_map = {item["name"]: item for item in report_data["indices"]}
    sh = idx_map.get("上证指数", {"pct_change": 0.0, "close": 0.0})
    hs300 = idx_map.get("沪深300", {"pct_change": 0.0, "close": 0.0})
    cyb = idx_map.get("创业板指", {"pct_change": 0.0, "close": 0.0})

    prompt = f"""# A股收盘速报 - AI绘图Prompt

## 图片规格
- 比例: 9:16 竖版
- 风格: 手绘/手账风格，暖色纸张质感
- 背景色: #F5E6C8 纸黄色
- 配色: 指数涨跌遵循A股红涨绿跌

## 标题
**📌 A股收盘速报**（主标题）
**{report_data["display_date"]}**（副标题）

---

## 硬性文案（必须逐字呈现）
- 指标1：上证指数  {sh["pct_change"]:+.2f}%  {sh["close"]:.2f}
- 指标2：沪深300  {hs300["pct_change"]:+.2f}%  {hs300["close"]:.2f}
- 指标3：创业板指  {cyb["pct_change"]:+.2f}%  {cyb["close"]:.2f}
- 成交额：{report_data["turnover_text"]}
- 点评：{summary["market_commentary"]}
- 有利因素标题：有利因素
- 有利因素正文：{report_data["favorable_factor"]}
- 有利因素点评：{summary["favorable_commentary"]}
- 不利因素标题：不利因素
- 不利因素正文：{report_data["unfavorable_factor"]}
- 不利因素点评：{summary["unfavorable_commentary"]}

## 排版要求
1) 顶部为标题区：主标题 + 日期横条。
2) 第二屏为三列指数卡片：指数名、涨跌幅、收盘点位。
3) 第三屏为成交额与点评信息框，点评文字控制在2-3行。
4) 第四屏为“有利因素”模块，红色小标题与强调图标。
5) 第五屏为“不利因素”模块，绿色小标题与强调图标。
6) 版面强调信息可读性，避免花哨插画和过多装饰。
7) 重点结论（点评/有利因素点评/不利因素点评）使用浅红底色块轻微高亮：#FDECEC。

---

## AI绘图Prompt (English)

Hand-drawn financial infographic poster, China A-share close report, {report_data["display_date"]}.

Style: warm cream paper texture (#F5E6C8), vintage notebook aesthetic, handwritten Chinese fonts.

Layout (9:16 vertical):
- Title area: "A股收盘速报" with date.
- Three index cards: SSE, CSI300, ChiNext with red-up green-down values.
- Turnover and commentary block.
- Favorable factor block with red highlight icon.
- Unfavorable factor block with green highlight icon.
- Use subtle light-red background highlight (#FDECEC) for key conclusion lines.
- Keep all Chinese text exactly as provided, no paraphrase.

Atmosphere: Professional, concise, hand-drawn finance poster style, high readability.

--ar 9:16 --style raw --v 6

---

## 底部标语
**总结不易，每天收盘后推送，点赞关注不迷路！**
"""
    return prompt


def run(date_str: str = None, output_dir: str = None) -> str:
    if not date_str:
        date_str = datetime.now().strftime("%Y%m%d")

    if output_dir is None:
        output_dir = os.path.join("results", date_str)

    report_data = collect_report_data(date_str)
    prompt_content = build_image_prompt(report_data)

    prompt_dir = os.path.join(output_dir, "AI提示词")
    os.makedirs(prompt_dir, exist_ok=True)

    output_path = os.path.join(prompt_dir, "收盘速报_Prompt.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(prompt_content)

    print(f"✅ 收盘速报 Prompt 已生成: {output_path}")
    return output_path


if __name__ == "__main__":
    run()
