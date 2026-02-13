#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Run selected close-time modules on A-share trade days and send email attachments."""

import argparse
import hashlib
import mimetypes
import os
import re
import smtplib
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Callable, Iterable, List, Optional

import akshare as ak
import pandas as pd
from dotenv import load_dotenv

DEFAULT_MODULES = [
    "sector_flow",
    "ladder",
    "sentiment",
    "close_report",
    "dragon",
    "fish_basin",
]
DEFAULT_RECIPIENT = "13522781970@163.com"
REQUIRED_TREND_EXCEL = [
    "趋势模型_指数.xlsx",
    "趋势模型_题材.xlsx",
    "趋势模型_合并.xlsx",
]

ATTACHMENT_NAME_ALIASES = {
    "趋势模型_指数.xlsx": "trend_index.xlsx",
    "趋势模型_题材.xlsx": "trend_sector.xlsx",
    "趋势模型_合并.xlsx": "trend_merged.xlsx",
    "市场情绪_Prompt.txt": "market_sentiment_prompt.txt",
    "收盘速报_Prompt.txt": "close_report_prompt.txt",
    "涨停天梯_Prompt.txt": "limit_up_ladder_prompt.txt",
    "资金流向_Prompt.txt": "capital_flow_prompt.txt",
    "趋势模型_合并_Prompt.txt": "trend_merged_prompt.txt",
    "龙虎榜_Prompt.txt": "dragon_tiger_prompt.txt",
    "异常异动_Prompt.txt": "abnormal_alert_prompt.txt",
}


@dataclass
class MailConfig:
    host: str
    port: int
    user: str
    password: str
    sender: str
    recipient: str
    use_ssl: bool


def _to_bool(value: str, default: bool = True) -> bool:
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


def _parse_date(date_str: Optional[str]) -> date:
    if not date_str:
        return datetime.now().date()
    return datetime.strptime(date_str, "%Y%m%d").date()


def is_a_share_trade_day(
    target_date: date,
    calendar_fetcher: Optional[Callable[[], pd.DataFrame]] = None,
) -> bool:
    """Return True when target_date is in A-share trade calendar."""
    fetcher = calendar_fetcher or ak.tool_trade_date_hist_sina
    try:
        calendar_df = fetcher()
        if calendar_df is None or calendar_df.empty or "trade_date" not in calendar_df.columns:
            return target_date.weekday() < 5
        trade_dates = (
            pd.to_datetime(calendar_df["trade_date"], errors="coerce")
            .dropna()
            .dt.date
            .tolist()
        )
        return target_date in set(trade_dates)
    except Exception:
        # Calendar source unavailable: best-effort fallback to weekday.
        return target_date.weekday() < 5


def run_selected_modules(
    repo_root: Path,
    run_date: str,
    python_executable: Optional[str] = None,
    modules: Optional[Iterable[str]] = None,
) -> int:
    selected = list(modules or DEFAULT_MODULES)
    command = [
        python_executable or sys.executable,
        "main.py",
        "multi",
        "--date",
        run_date,
        *selected,
    ]
    completed = subprocess.run(command, cwd=str(repo_root), check=False)
    return int(completed.returncode)


def collect_attachments(date_dir: Path) -> List[Path]:
    attachments: List[Path] = []
    seen = set()

    for filename in REQUIRED_TREND_EXCEL:
        path = date_dir / filename
        if path.exists() and path.is_file():
            key = str(path.resolve())
            if key not in seen:
                attachments.append(path)
                seen.add(key)

    prompt_dir = date_dir / "AI提示词"
    if prompt_dir.exists() and prompt_dir.is_dir():
        for path in sorted(prompt_dir.rglob("*.txt")):
            if "prompt" not in path.name.lower():
                continue
            key = str(path.resolve())
            if key in seen:
                continue
            attachments.append(path)
            seen.add(key)

    return attachments


def build_attachment_filename(
    path: Path,
    date_str: Optional[str],
    prefix_date: bool = False,
    use_chinese: bool = False,
) -> str:
    filename = path.name
    prefix = f"{date_str}_" if date_str else ""

    if prefix and filename.startswith(prefix):
        raw_name = filename[len(prefix):]
    else:
        raw_name = filename

    if use_chinese:
        normalized = raw_name
    else:
        alias = ATTACHMENT_NAME_ALIASES.get(raw_name)
        if alias:
            normalized = alias
        else:
            stem = Path(raw_name).stem
            ext = Path(raw_name).suffix.lower()
            ascii_stem = (
                unicodedata.normalize("NFKD", stem)
                .encode("ascii", "ignore")
                .decode("ascii")
            )
            ascii_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", ascii_stem).strip("._-")
            if not ascii_stem:
                digest = hashlib.md5(raw_name.encode("utf-8")).hexdigest()[:8]
                ascii_stem = f"file_{digest}"
            normalized = f"{ascii_stem}{ext}"

    if prefix_date and prefix:
        if normalized.startswith(prefix):
            return normalized
        return f"{prefix}{normalized}"
    return normalized


def load_mail_config(recipient: str) -> MailConfig:
    user = (os.getenv("MAIL_SMTP_USER") or "").strip()
    password = (os.getenv("MAIL_SMTP_PASS") or "").strip()
    if not user or not password:
        raise ValueError("MAIL_SMTP_USER / MAIL_SMTP_PASS are required")

    host = (os.getenv("MAIL_SMTP_HOST") or "smtp.163.com").strip()
    port = int((os.getenv("MAIL_SMTP_PORT") or "465").strip())
    sender = (os.getenv("MAIL_FROM") or user).strip()
    use_ssl = _to_bool(os.getenv("MAIL_USE_SSL"), default=True)

    return MailConfig(
        host=host,
        port=port,
        user=user,
        password=password,
        sender=sender,
        recipient=recipient,
        use_ssl=use_ssl,
    )


def send_email_with_attachments(
    config: MailConfig,
    subject: str,
    body: str,
    attachments: Iterable[Path],
    date_str: Optional[str] = None,
    prefix_date: bool = False,
    use_chinese: bool = False,
) -> None:
    msg = EmailMessage()
    msg["From"] = config.sender
    msg["To"] = config.recipient
    msg["Subject"] = subject
    msg.set_content(body)

    for path in attachments:
        mime_type, _ = mimetypes.guess_type(str(path))
        if mime_type:
            maintype, subtype = mime_type.split("/", 1)
        else:
            maintype, subtype = "application", "octet-stream"
        attachment_name = build_attachment_filename(
            path,
            date_str,
            prefix_date=prefix_date,
            use_chinese=use_chinese,
        )
        msg.add_attachment(
            path.read_bytes(),
            maintype=maintype,
            subtype=subtype,
            filename=attachment_name,
        )

    if config.use_ssl:
        with smtplib.SMTP_SSL(config.host, config.port, timeout=30) as smtp:
            smtp.login(config.user, config.password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(config.host, config.port, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(config.user, config.password)
            smtp.send_message(msg)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="After-close workflow + email delivery")
    parser.add_argument("--date", type=str, help="Target date YYYYMMDD (default: today)")
    parser.add_argument("--recipient", type=str, default=DEFAULT_RECIPIENT, help="Email recipient")
    parser.add_argument(
        "--subject-prefix",
        type=str,
        default="A股收盘自动报告",
        help="Email subject prefix",
    )
    parser.add_argument("--dry-run", action="store_true", help="Run workflow without sending email")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    load_dotenv(repo_root / ".env", override=False)

    target_date = _parse_date(args.date)
    date_str = target_date.strftime("%Y%m%d")
    if not is_a_share_trade_day(target_date):
        print(f"⏭️ {date_str} is not an A-share trade day. Skipping.")
        return 0

    print(f"▶ Running close workflow for {date_str} ...")
    exit_code = run_selected_modules(repo_root=repo_root, run_date=date_str)
    if exit_code != 0:
        print(f"⚠️ Workflow returned non-zero code: {exit_code}")

    date_dir = repo_root / "results" / date_str
    attachments = collect_attachments(date_dir)
    if not attachments:
        print(f"❌ No attachments found under: {date_dir}")
        return 1

    subject = f"{args.subject_prefix} {date_str}"
    prefix_date = _to_bool(os.getenv("MAIL_ATTACHMENT_PREFIX_DATE"), default=False)
    use_chinese = _to_bool(os.getenv("MAIL_ATTACHMENT_USE_CHINESE"), default=False)
    attachment_names = [
        build_attachment_filename(
            path,
            date_str,
            prefix_date=prefix_date,
            use_chinese=use_chinese,
        )
        for path in attachments
    ]
    body_lines = [
        f"Date: {date_str}",
        "",
        "Attachments:",
        *[f"- {name}" for name in attachment_names],
    ]
    body = "\n".join(body_lines)

    if args.dry_run:
        print("🧪 Dry run enabled. Skip email sending.")
        print(body)
        return 0

    config = load_mail_config(args.recipient)
    send_email_with_attachments(
        config,
        subject,
        body,
        attachments,
        date_str=date_str,
        prefix_date=prefix_date,
        use_chinese=use_chinese,
    )
    print(f"✅ Email sent to {config.recipient} with {len(attachments)} attachments.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
