import unittest
from unittest.mock import patch

import pandas as pd

from modules.fish_basin import fish_basin


class TestFishBasinHKStrictDataPolicy(unittest.TestCase):
    def test_hk_symbol_returns_none_when_spot_unavailable_and_history_is_stale(self):
        stale_df = pd.DataFrame(
            [
                {
                    "date": "2020-01-01",
                    "open": 100.0,
                    "high": 101.0,
                    "low": 99.0,
                    "close": 100.0,
                    "volume": 12345.0,
                }
            ]
        )

        with patch(
            "modules.fish_basin.fish_basin.ak.stock_hk_index_daily_sina",
            return_value=stale_df,
        ), patch(
            "modules.fish_basin.fish_basin.ak.stock_hk_index_spot_em",
            side_effect=RuntimeError("EM spot unavailable"),
        ), patch(
            "modules.fish_basin.fish_basin.ak.stock_hk_index_spot_sina",
            side_effect=RuntimeError("Sina spot unavailable"),
        ):
            result = fish_basin.fetch_data("恒生科技", "hkHSTECH")

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
