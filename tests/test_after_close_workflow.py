import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from scripts import after_close_workflow


class TestAfterCloseWorkflow(unittest.TestCase):
    def test_is_a_share_trade_day_true_when_date_in_calendar(self):
        calendar_df = pd.DataFrame(
            {
                "trade_date": [
                    "2026-02-12",
                    "2026-02-13",
                ]
            }
        )
        target = date(2026, 2, 13)

        self.assertTrue(
            after_close_workflow.is_a_share_trade_day(
                target, calendar_fetcher=lambda: calendar_df
            )
        )

    def test_is_a_share_trade_day_false_when_date_not_in_calendar(self):
        calendar_df = pd.DataFrame({"trade_date": ["2026-02-12"]})
        target = date(2026, 2, 13)

        self.assertFalse(
            after_close_workflow.is_a_share_trade_day(
                target, calendar_fetcher=lambda: calendar_df
            )
        )

    def test_collect_attachments_includes_prompt_files_and_three_excel_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            date_dir = Path(temp_dir) / "results" / "20260213"
            prompt_dir = date_dir / "AI提示词"
            prompt_dir.mkdir(parents=True, exist_ok=True)

            # Required trend model excels
            (date_dir / "趋势模型_指数.xlsx").write_text("x", encoding="utf-8")
            (date_dir / "趋势模型_题材.xlsx").write_text("x", encoding="utf-8")
            (date_dir / "趋势模型_合并.xlsx").write_text("x", encoding="utf-8")
            # Prompt files
            (prompt_dir / "资金流向_Prompt.txt").write_text("x", encoding="utf-8")
            (prompt_dir / "涨停天梯_Prompt.txt").write_text("x", encoding="utf-8")

            attachments = after_close_workflow.collect_attachments(date_dir)
            names = {path.name for path in attachments}

            self.assertIn("趋势模型_指数.xlsx", names)
            self.assertIn("趋势模型_题材.xlsx", names)
            self.assertIn("趋势模型_合并.xlsx", names)
            self.assertIn("资金流向_Prompt.txt", names)
            self.assertIn("涨停天梯_Prompt.txt", names)

    def test_load_mail_config_raises_when_credentials_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                after_close_workflow.load_mail_config(
                    "13522781970@163.com",
                )

    def test_build_attachment_filename_default_without_date_prefix(self):
        filename = after_close_workflow.build_attachment_filename(
            Path("趋势模型_合并.xlsx"),
            "20260213",
        )
        self.assertEqual(filename, "trend_merged.xlsx")

    def test_build_attachment_filename_prefixes_date_when_enabled(self):
        filename = after_close_workflow.build_attachment_filename(
            Path("趋势模型_合并.xlsx"),
            "20260213",
            prefix_date=True,
        )
        self.assertEqual(filename, "20260213_trend_merged.xlsx")

    def test_build_attachment_filename_does_not_double_prefix_when_enabled(self):
        filename = after_close_workflow.build_attachment_filename(
            Path("20260213_trend_merged.xlsx"),
            "20260213",
            prefix_date=True,
        )
        self.assertEqual(filename, "20260213_trend_merged.xlsx")

    def test_build_attachment_filename_is_ascii(self):
        filename = after_close_workflow.build_attachment_filename(
            Path("市场情绪_Prompt.txt"),
            "20260213",
        )
        self.assertTrue(all(ord(ch) < 128 for ch in filename))

    def test_build_attachment_filename_can_use_chinese(self):
        filename = after_close_workflow.build_attachment_filename(
            Path("趋势模型_合并.xlsx"),
            "20260213",
            use_chinese=True,
        )
        self.assertEqual(filename, "趋势模型_合并.xlsx")


if __name__ == "__main__":
    unittest.main()
