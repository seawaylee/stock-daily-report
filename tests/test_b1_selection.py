import unittest
import types
import re
from unittest.mock import patch

from modules.stock_selection import b1_selection


def _sample_stocks():
    return [
        {
            "code": "300750",
            "name": "宁德时代",
            "industry": "新能源",
            "signals": ["超卖缩量B", "原始B1"],
            "J": 8.2,
            "RSI": 19.5,
            "near_amplitude": 22.1,
            "far_amplitude": 31.4,
            "raw_data_mock": {"close": 210.5, "volume": 123456.0},
        },
        {
            "code": "600519",
            "name": "贵州茅台",
            "industry": "白酒",
            "signals": ["回踩黄线B"],
            "J": 41.3,
            "RSI": 45.2,
            "near_amplitude": 12.6,
            "far_amplitude": 20.3,
            "raw_data_mock": {"close": 1550.0, "volume": 65432.0},
        },
    ]


def _sample_many_stocks(count=6):
    stocks = []
    for i in range(count):
        code = f"{300750 + i:06d}"
        stocks.append(
            {
                "code": code,
                "name": f"样例股票{i + 1}",
                "industry": "测试行业",
                "signals": ["超卖缩量B"],
                "J": 10 + i,
                "RSI": 20 + i,
                "near_amplitude": 10 + i,
                "far_amplitude": 20 + i,
                "raw_data_mock": {"close": 100.0 + i, "volume": 10000.0 + i},
                "reason": f"理由{i + 1}",
            }
        )
    return stocks


class TestB1SelectionPromptStyle(unittest.TestCase):
    def test_generate_image_prompt_uses_brief_reason_style(self):
        fake_pypinyin = types.SimpleNamespace(
            lazy_pinyin=lambda s, style=None: [ch for ch in s],
            Style=types.SimpleNamespace(FIRST_LETTER="FIRST_LETTER"),
        )
        with patch.dict("sys.modules", {"pypinyin": fake_pypinyin}):
            prompt, _ = b1_selection.generate_image_prompt(
                gemini_analysis="测试分析文本",
                selected_stocks=_sample_stocks(),
                date_dir="results/20260212",
            )

        self.assertIn("选股理由", prompt)
        self.assertNotIn("Buy", prompt)
        self.assertNotIn("买入区间", prompt)
        self.assertNotIn("**操作**", prompt)

    def test_generate_image_prompt_limits_cards_to_top5(self):
        fake_pypinyin = types.SimpleNamespace(
            lazy_pinyin=lambda s, style=None: [ch for ch in s],
            Style=types.SimpleNamespace(FIRST_LETTER="FIRST_LETTER"),
        )
        with patch.dict("sys.modules", {"pypinyin": fake_pypinyin}):
            prompt, _ = b1_selection.generate_image_prompt(
                gemini_analysis="测试分析文本",
                selected_stocks=_sample_many_stocks(6),
                date_dir="results/20260212",
            )

        card_count = len(re.findall(r"^#\d+\s", prompt, flags=re.MULTILINE))
        self.assertEqual(card_count, 5)
        self.assertNotIn("#6 ", prompt)

    def test_generate_image_prompt_uses_llm_industry_without_guess_suffix(self):
        fake_pypinyin = types.SimpleNamespace(
            lazy_pinyin=lambda s, style=None: [ch for ch in s],
            Style=types.SimpleNamespace(FIRST_LETTER="FIRST_LETTER"),
        )
        stocks = [
            {
                "code": "600877",
                "name": "电科芯片",
                "industry": "",
                "signals": ["超卖缩量B"],
                "J": 12.3,
                "RSI": 25.6,
                "near_amplitude": 10.2,
                "far_amplitude": 19.8,
                "raw_data_mock": {"close": 15.2, "volume": 34567.0},
            }
        ]
        gemini_analysis = (
            "1. Top5股票排名\n\n"
            "[电科芯片] (600877) | 半导体芯片 / 信创军工\n"
            "推荐理由：多重买点叠加，芯片超卖区。\n"
        )
        with patch.dict("sys.modules", {"pypinyin": fake_pypinyin}):
            prompt, _ = b1_selection.generate_image_prompt(
                gemini_analysis=gemini_analysis,
                selected_stocks=stocks,
                date_dir="results/20260212",
            )

        self.assertIn("半导体芯片 / 信创军工", prompt)
        self.assertNotIn("(猜)", prompt)

    def test_generate_image_prompt_contains_color_accent_guidelines(self):
        fake_pypinyin = types.SimpleNamespace(
            lazy_pinyin=lambda s, style=None: [ch for ch in s],
            Style=types.SimpleNamespace(FIRST_LETTER="FIRST_LETTER"),
        )
        with patch.dict("sys.modules", {"pypinyin": fake_pypinyin}):
            prompt, _ = b1_selection.generate_image_prompt(
                gemini_analysis="测试分析文本",
                selected_stocks=_sample_stocks(),
                date_dir="results/20260212",
            )

        self.assertIn("COLOR ACCENT GUIDELINES", prompt)
        self.assertIn("soft AI-cyan", prompt)
        self.assertIn("rounded light highlight background", prompt)


if __name__ == "__main__":
    unittest.main()
