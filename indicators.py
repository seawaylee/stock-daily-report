"""
技术指标计算模块 - 东方财富公式兼容实现
实现 SMA、EMA、MA、KDJ、RSI、BBI 等指标
"""
import numpy as np
import pandas as pd
from typing import Union

Series = pd.Series
DataFrame = pd.DataFrame


def ref(series: Series, n: int = 1) -> Series:
    """REF: 引用N周期前的值"""
    return series.shift(n)


def ma(series: Series, n: int) -> Series:
    """MA: 简单移动平均"""
    return series.rolling(window=n, min_periods=1).mean()


def ema(series: Series, n: int) -> Series:
    """EMA: 指数移动平均"""
    return series.ewm(span=n, adjust=False).mean()


def sma(series: Series, n: int, m: int) -> Series:
    """
    SMA: 东财公式的加权移动平均
    公式: SMA(X,N,M) = (M*X + (N-M)*REF(SMA,1)) / N
    注意: 这与 TA-Lib 的 SMA 不同
    """
    result = np.zeros(len(series))
    result[0] = series.iloc[0] if not np.isnan(series.iloc[0]) else 0
    
    for i in range(1, len(series)):
        if np.isnan(series.iloc[i]):
            result[i] = result[i-1]
        else:
            result[i] = (m * series.iloc[i] + (n - m) * result[i-1]) / n
    
    return pd.Series(result, index=series.index)


def hhv(series: Series, n: int) -> Series:
    """HHV: N周期内最高值"""
    return series.rolling(window=n, min_periods=1).max()


def llv(series: Series, n: int) -> Series:
    """LLV: N周期内最低值"""
    return series.rolling(window=n, min_periods=1).min()


def hhvbars(series: Series, n: int) -> Series:
    """HHVBARS: N周期内最高值到当前的周期数"""
    def bars_since_max(x):
        if len(x) == 0:
            return 0
        return len(x) - 1 - np.argmax(x.values)
    return series.rolling(window=n, min_periods=1).apply(bars_since_max, raw=False)


def count(condition: Series, n: int) -> Series:
    """COUNT: 统计N周期内条件成立的次数"""
    return condition.astype(int).rolling(window=n, min_periods=1).sum()


def every(condition: Series, n: int) -> Series:
    """EVERY: N周期内条件是否全部成立"""
    return count(condition, n) == n


def exist(condition: Series, n: int) -> Series:
    """EXIST: N周期内条件是否存在成立"""
    return count(condition, n) > 0


def barslast(condition: Series) -> Series:
    """BARSLAST: 上一次条件成立到当前的周期数"""
    result = np.zeros(len(condition))
    last_true = -1
    
    for i in range(len(condition)):
        if condition.iloc[i]:
            last_true = i
        if last_true == -1:
            result[i] = np.nan
        else:
            result[i] = i - last_true
    
    return pd.Series(result, index=condition.index)


def cross(series1: Series, series2: Union[Series, float]) -> Series:
    """CROSS: series1 上穿 series2"""
    if isinstance(series2, (int, float)):
        series2 = pd.Series([series2] * len(series1), index=series1.index)
    
    prev1 = series1.shift(1)
    prev2 = series2.shift(1)
    
    return (prev1 <= prev2) & (series1 > series2)


def kdj(high: Series, low: Series, close: Series, n: int = 9, m1: int = 3, m2: int = 3) -> tuple:
    """
    KDJ指标计算
    返回: (K, D, J)
    """
    llv_low = llv(low, n)
    hhv_high = hhv(high, n)
    
    rsv = (close - llv_low) / (hhv_high - llv_low) * 100
    rsv = rsv.fillna(50)  # 处理除零情况
    
    k = sma(rsv, m1, 1)
    d = sma(k, m2, 1)
    j = 3 * k - 2 * d
    
    return k, d, j


def rsi(close: Series, n: int = 3) -> Series:
    """
    RSI指标计算 (东财公式版本)
    使用 SMA 而非标准 EMA
    """
    lc = ref(close, 1)
    diff = close - lc
    
    temp1 = diff.clip(lower=0)  # MAX(CLOSE-LC, 0)
    temp2 = diff.abs()          # ABS(CLOSE-LC)
    
    sma_temp1 = sma(temp1, n, 1)
    sma_temp2 = sma(temp2, n, 1)
    
    result = sma_temp1 / sma_temp2 * 100
    result = result.fillna(50)
    
    return result


def bbi(close: Series) -> Series:
    """BBI: 多空指标"""
    return (ma(close, 3) + ma(close, 6) + ma(close, 12) + ma(close, 24)) / 4


def trend_white_line(close: Series) -> Series:
    """趋势白线: EMA(EMA(C,10),10)"""
    return ema(ema(close, 10), 10)


def dage_yellow_line(close: Series) -> Series:
    """大哥黄线: 多周期均线平均"""
    return (ma(close, 14) + ma(close, 28) + ma(close, 57) + ma(close, 114)) / 4


def short_term(close: Series, low: Series) -> Series:
    """短期指标: 100*(C-LLV(L,3))/(HHV(C,3)-LLV(L,3))"""
    llv_low = llv(low, 3)
    hhv_close = hhv(close, 3)
    
    result = 100 * (close - llv_low) / (hhv_close - llv_low)
    return result.fillna(50)


def long_term(close: Series, low: Series) -> Series:
    """长期指标: 100*(C-LLV(L,21))/(HHV(C,21)-LLV(L,21))"""
    llv_low = llv(low, 21)
    hhv_close = hhv(close, 21)
    
    result = 100 * (close - llv_low) / (hhv_close - llv_low)
    return result.fillna(50)


def calculate_all_indicators(df: DataFrame) -> DataFrame:
    """
    计算所有技术指标并添加到DataFrame
    df 需要包含: open, high, low, close, volume 列
    """
    df = df.copy()
    
    # 基础价格列
    o, h, l, c, v = df['open'], df['high'], df['low'], df['close'], df['volume']
    
    # KDJ
    df['K'], df['D'], df['J'] = kdj(h, l, c)
    
    # RSI
    df['RSI'] = rsi(c, 3)
    
    # 趋势线
    df['趋势白线'] = trend_white_line(c)
    df['大哥黄线'] = dage_yellow_line(c)
    
    # BBI
    df['BBI'] = bbi(c)
    
    # 短期/长期
    df['短期'] = short_term(c, l)
    df['长期'] = long_term(c, l)
    
    # MA60
    df['MA60'] = ma(c, 60)
    
    return df
