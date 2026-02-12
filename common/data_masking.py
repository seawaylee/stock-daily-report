"""
Data Masking Utilities for Stock Information
用于对股票代码和名称进行脱敏处理
"""
try:
    from pypinyin import lazy_pinyin, Style
    _HAS_PYPINYIN = True
except ImportError:  # pragma: no cover - depends on runtime env
    lazy_pinyin = None
    Style = None
    _HAS_PYPINYIN = False


def _fallback_initial(ch: str) -> str:
    """
    Derive an uppercase initial from one character without external deps.

    - ASCII letters/digits: uppercase itself
    - Chinese chars: approximate pinyin initial by GBK code ranges
    - Others: X
    """
    if not ch:
        return "X"

    if ch.isascii():
        return ch.upper()

    try:
        gbk = ch.encode("gbk")
    except Exception:
        return "X"

    if len(gbk) < 2:
        return "X"

    code = gbk[0] * 256 + gbk[1] - 65536
    mapping = (
        (-20319, -20284, "A"),
        (-20283, -19776, "B"),
        (-19775, -19219, "C"),
        (-19218, -18711, "D"),
        (-18710, -18527, "E"),
        (-18526, -18240, "F"),
        (-18239, -17923, "G"),
        (-17922, -17418, "H"),
        (-17417, -16475, "J"),
        (-16474, -16213, "K"),
        (-16212, -15641, "L"),
        (-15640, -15166, "M"),
        (-15165, -14923, "N"),
        (-14922, -14915, "O"),
        (-14914, -14631, "P"),
        (-14630, -14150, "Q"),
        (-14149, -14091, "R"),
        (-14090, -13319, "S"),
        (-13318, -12839, "T"),
        (-12838, -12557, "W"),
        (-12556, -11848, "X"),
        (-11847, -11056, "Y"),
        (-11055, -10247, "Z"),
    )
    for start, end, letter in mapping:
        if start <= code <= end:
            return letter
    return "X"


def _fallback_initials(text: str) -> str:
    return "".join(_fallback_initial(ch) for ch in text)


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

    if _HAS_PYPINYIN:
        # Convert to pinyin and get first letter of each character
        pinyin_list = lazy_pinyin(last_two, style=Style.FIRST_LETTER)
        abbreviation = ''.join(pinyin_list).upper()
    else:
        # Fallback when pypinyin is unavailable: derive initials without third-party deps.
        abbreviation = _fallback_initials(last_two)

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
