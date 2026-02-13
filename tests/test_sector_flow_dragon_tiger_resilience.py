import os
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from modules.dragon_tiger import dragon_tiger
from modules.sector_flow import sector_flow


class TestSectorFlowResilience(unittest.TestCase):
    def test_sector_flow_uses_dataapi_when_ths_and_push2_fail(self):
        dataapi_payload = {
            "rc": 0,
            "data": {
                "total": 3,
                "diff": [
                    {"f12": "BK1036", "f13": 90, "f14": "半导体", "f62": 3_000_000_000},
                    {"f12": "BK1037", "f13": 90, "f14": "消费电子", "f62": 1_000_000_000},
                    {"f12": "BK0728", "f13": 90, "f14": "煤炭行业", "f62": -500_000_000},
                ],
            },
        }
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = dataapi_payload

        with patch(
            "modules.sector_flow.sector_flow.ak.stock_board_industry_summary_ths",
            side_effect=AttributeError("'NoneType' object has no attribute 'text'"),
        ), patch(
            "modules.sector_flow.sector_flow.ak.stock_sector_fund_flow_rank",
            side_effect=requests.exceptions.ConnectionError("remote closed"),
        ), patch.object(sector_flow, "requests", create=True) as mock_requests:
            mock_requests.get.return_value = mock_response
            result = sector_flow.get_sector_flow("行业资金流")

        self.assertIsNotNone(result)
        inflow, outflow, name_col, flow_col = result
        self.assertEqual(name_col, "名称")
        self.assertEqual(flow_col, "net_flow_billion")
        self.assertEqual(inflow.iloc[0]["名称"], "半导体")
        self.assertAlmostEqual(float(inflow.iloc[0]["net_flow_billion"]), 30.0)
        self.assertEqual(outflow.iloc[0]["名称"], "煤炭行业")
        self.assertAlmostEqual(float(outflow.iloc[0]["net_flow_billion"]), -5.0)

        self.assertTrue(mock_requests.get.called)
        self.assertEqual(mock_requests.get.call_args.kwargs["params"]["code"], "m:90+t:2")
        self.assertEqual(mock_requests.get.call_args.kwargs["params"]["key"], "f62")


class TestDragonTigerResilience(unittest.TestCase):
    def test_dragon_tiger_falls_back_to_previous_date_on_none_result(self):
        fallback_inst = pd.DataFrame([{"name": "测试股份", "net_buy": 123_000_000}])
        fallback_active = pd.DataFrame([{"dept_name": "测试营业部", "buy_total": 456_000_000}])

        def _mock_inst(start_date, end_date):
            if start_date == "20260213":
                raise TypeError("'NoneType' object is not subscriptable")
            return fallback_inst

        def _mock_active(start_date, end_date):
            if start_date == "20260213":
                raise TypeError("'NoneType' object is not subscriptable")
            return fallback_active

        with patch(
            "modules.dragon_tiger.dragon_tiger.ak.stock_lhb_jgmmtj_em",
            side_effect=_mock_inst,
        ) as mock_inst, patch(
            "modules.dragon_tiger.dragon_tiger.ak.stock_lhb_hyyyb_em",
            side_effect=_mock_active,
        ) as mock_active:
            inst_df, active_df, used_date = dragon_tiger.get_dragon_tiger_data(
                "20260213", return_used_date=True
            )

        self.assertIsNotNone(inst_df)
        self.assertIsNotNone(active_df)
        self.assertFalse(inst_df.empty)
        self.assertFalse(active_df.empty)
        self.assertEqual(used_date, "20260212")
        self.assertEqual(mock_inst.call_count, 2)
        self.assertEqual(mock_active.call_count, 2)

    def test_run_uses_effective_date_from_fallback_data(self):
        inst_df = pd.DataFrame([{"name": "测试股份", "net_buy": 123_000_000}])
        active_df = pd.DataFrame([{"dept_name": "测试营业部", "buy_total": 456_000_000}])

        with tempfile.TemporaryDirectory() as tmpdir:
            date_dir = os.path.join(tmpdir, "20260213")
            with patch(
                "modules.dragon_tiger.dragon_tiger.get_dragon_tiger_data",
                return_value=(inst_df, active_df, "20260212"),
            ), patch(
                "modules.dragon_tiger.dragon_tiger.generate_prompt"
            ) as mock_generate_prompt:
                ok = dragon_tiger.run(date_dir=date_dir)

        self.assertTrue(ok)
        self.assertTrue(mock_generate_prompt.called)
        self.assertEqual(mock_generate_prompt.call_args.args[2], "20260212")


if __name__ == "__main__":
    unittest.main()
