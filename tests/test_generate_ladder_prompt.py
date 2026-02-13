import os
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from modules.market_ladder import generate_ladder_prompt


class TestGenerateLadderPrompt(unittest.TestCase):
    def test_failed_stock_marker_requires_brush_x_overlay_over_name_and_industry(self):
        mock_ladder = {
            2: [
                {
                    "name": "强势股A",
                    "industry": "机器人",
                    "time": "09:31",
                    "status": "success",
                },
                {
                    "name": "回落股B",
                    "industry": "AI算力",
                    "time": "10:22",
                    "status": "fried",
                },
            ],
            1: [
                {
                    "name": "首板股C",
                    "industry": "消费电子",
                    "time": "11:01",
                    "status": "success",
                }
            ],
        }

        with tempfile.TemporaryDirectory() as tmpdir, patch.object(
            generate_ladder_prompt,
            "get_limit_up_data",
            return_value=(pd.DataFrame({"代码": ["000001"]}), pd.DataFrame(), pd.DataFrame()),
        ), patch.object(
            generate_ladder_prompt, "repair_board_counts", side_effect=lambda df, _date: df
        ), patch.object(
            generate_ladder_prompt, "process_ladder_data", return_value=mock_ladder
        ), patch.object(
            generate_ladder_prompt, "generate_image_from_text"
        ):
            output_path = generate_ladder_prompt.generate_ladder_prompt("20260212", tmpdir)

            with open(output_path, "r", encoding="utf-8") as f:
                prompt_text = f.read()

        self.assertIn("股票名+题材", prompt_text)
        self.assertIn("不要画在旁边", prompt_text)
        self.assertIn("毛笔", prompt_text)
        self.assertIn("红色毛笔叉", prompt_text)
        self.assertNotIn("浅红", prompt_text)
        self.assertNotIn("light-red", prompt_text)
        self.assertNotIn("LIGHT RED", prompt_text)
        self.assertNotIn("RED cross/X mark over stock name", prompt_text)


if __name__ == "__main__":
    unittest.main()
