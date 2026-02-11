"""
Data Masking Utilities for Stock Information
用于对股票代码和名称进行脱敏处理
"""
from pypinyin import lazy_pinyin, Style


def mask_stock_code(code: str) -> str:
    """
    Mask stock code by replacing last 2 digits with **

    Examples:
        513320 -> 5133**
        000001 -> 0000**

    Args:
        code: Stock code string

    Returns:
        Masked stock code
    """
    if not code or len(code) < 2:
        return code
    return code[:-2] + "**"


def mask_stock_name(name: str) -> str:
    """
    Mask stock name by replacing last 2 characters with pinyin abbreviation

    Examples:
        平安银行 -> 平安YH
        贵州茅台 -> 贵州MT
        中国平安 -> 中国PA

    Args:
        name: Stock name string

    Returns:
        Masked stock name
    """
    if not name or len(name) < 2:
        return name

    # Get last 2 characters
    last_two = name[-2:]

    # Convert to pinyin and get first letter of each character
    pinyin_list = lazy_pinyin(last_two, style=Style.FIRST_LETTER)
    abbreviation = ''.join(pinyin_list).upper()

    # Replace last 2 characters with abbreviation
    return name[:-2] + abbreviation


def mask_stock_info(code: str, name: str) -> tuple:
    """
    Mask both stock code and name

    Args:
        code: Stock code
        name: Stock name

    Returns:
        Tuple of (masked_code, masked_name)
    """
    return mask_stock_code(code), mask_stock_name(name)


if __name__ == "__main__":
    # Test cases
    test_cases = [
        ("513320", "平安银行"),
        ("600519", "贵州茅台"),
        ("601318", "中国平安"),
        ("000001", "平安银行"),
        ("300750", "宁德时代"),
    ]

    print("=== Data Masking Test ===\n")
    for code, name in test_cases:
        masked_code, masked_name = mask_stock_info(code, name)
        print(f"Original: {code} {name}")
        print(f"Masked:   {masked_code} {masked_name}")
        print()
