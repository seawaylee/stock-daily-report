import unittest
from unittest.mock import patch

from common import data_masking


class TestDataMasking(unittest.TestCase):
    def test_mask_stock_name_fallback_without_pypinyin_uses_initials(self):
        with patch.object(data_masking, "_HAS_PYPINYIN", False):
            masked = data_masking.mask_stock_name("贵州茅台")
        self.assertEqual(masked, "贵州MT")

    def test_mask_stock_code(self):
        self.assertEqual(data_masking.mask_stock_code("513320"), "5133**")


if __name__ == "__main__":
    unittest.main()
