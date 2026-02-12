import os
import tempfile
import unittest
from unittest.mock import patch

from modules.close_report import close_report


def _sample_report_data():
    return {
        "date_str": "20260212",
        "display_date": "2026年2月12日",
        "indices": [
            {"name": "上证指数", "pct_change": 0.05, "close": 4134.02},
            {"name": "沪深300", "pct_change": 0.12, "close": 4719.58},
            {"name": "创业板指", "pct_change": 1.32, "close": 3328.06},
        ],
        "turnover_text": "2.16万亿（较前一日增加1597亿）",
        "favorable_factor": "国务院办公厅日前印发《关于完善全国统一电力市场体系的实施意见》。",
        "unfavorable_factor": "美国1月非农新增就业岗位13万人，失业率为4.3%。",
        "summary": {
            "market_commentary": "今天是春节前倒数第二个交易日，市场继续保持小幅波动。",
            "favorable_commentary": "电力市场化程度将继续提升，电网设备板块相对较强。",
            "unfavorable_commentary": "降息预期回落对风险偏好有压制，短期仍需关注波动。",
        },
    }


class TestCloseReport(unittest.TestCase):
    def test_parse_llm_summary_handles_fenced_json(self):
        content = """下面是总结：
```json
{
  "market_commentary": "市场小幅震荡，题材轮动为主。",
  "favorable_commentary": "政策落地提升了电力链条关注度。",
  "unfavorable_commentary": "海外降息预期回落压制风险偏好。"
}
```"""
        parsed = close_report.parse_llm_summary(content)
        self.assertEqual(parsed["market_commentary"], "市场小幅震荡，题材轮动为主。")
        self.assertIn("电力链条", parsed["favorable_commentary"])
        self.assertIn("降息预期", parsed["unfavorable_commentary"])

    def test_parse_llm_summary_falls_back_when_invalid(self):
        parsed = close_report.parse_llm_summary("not-json")
        self.assertTrue(parsed["market_commentary"])
        self.assertTrue(parsed["favorable_commentary"])
        self.assertTrue(parsed["unfavorable_commentary"])

    def test_parse_llm_summary_compacts_text_length(self):
        content = """{
  "market_commentary": "今天市场整体呈现出明显的结构性分化特征，指数虽然波动不大但资金在不同板块间快速轮动，建议投资者保持耐心并控制节奏。",
  "favorable_commentary": "政策端持续释放积极信号，相关产业链短期景气度仍有望延续。",
  "unfavorable_commentary": "海外不确定性抬升叠加高位分化，追高风险显著增加。"
}"""
        parsed = close_report.parse_llm_summary(content)
        self.assertLessEqual(len(parsed["market_commentary"]), 44)
        self.assertLessEqual(len(parsed["favorable_commentary"]), 28)
        self.assertLessEqual(len(parsed["unfavorable_commentary"]), 28)

    def test_format_turnover_text_only_shows_value(self):
        text = close_report.format_turnover_text(
            {"today_volume": 2.16e12, "yesterday_volume": 2.0e12}
        )
        self.assertEqual(text, "2.16万亿")

    def test_generate_summary_does_not_pass_max_tokens(self):
        raw_summary = """{
  "market_commentary": "市场整体窄幅震荡。",
  "favorable_commentary": "政策支持延续板块景气。",
  "unfavorable_commentary": "海外扰动压制短线风险偏好。"
}"""
        with patch("common.llm_client.chat_completion", return_value=raw_summary) as mocked_chat:
            close_report.generate_summary(_sample_report_data())

        kwargs = mocked_chat.call_args.kwargs
        self.assertNotIn("max_tokens", kwargs)

    def test_build_image_prompt_contains_key_sections(self):
        prompt = close_report.build_image_prompt(_sample_report_data())
        self.assertIn("收盘速报", prompt)
        self.assertIn("2026年2月12日", prompt)
        self.assertIn("上证指数", prompt)
        self.assertIn("2.16万亿", prompt)
        self.assertIn("有利因素", prompt)
        self.assertIn("不利因素", prompt)
        self.assertIn("今天是春节前倒数第二个交易日", prompt)
        self.assertIn("Hand-drawn financial infographic poster", prompt)
        self.assertIn("warm cream paper texture", prompt)
        self.assertIn("--ar 9:16 --style raw --v 6", prompt)
        self.assertIn("总结不易，每天收盘后推送，点赞关注不迷路！", prompt)

    def test_run_writes_prompt_file(self):
        sample = _sample_report_data()
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch.object(close_report, "collect_report_data", return_value=sample):
                output_path = close_report.run("20260212", output_dir=temp_dir)

            self.assertTrue(output_path.endswith("AI提示词/收盘速报_Prompt.txt"))
            self.assertTrue(os.path.exists(output_path))
            with open(output_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("A股收盘速报", content)
            self.assertIn("国务院办公厅日前印发", content)


if __name__ == "__main__":
    unittest.main()
