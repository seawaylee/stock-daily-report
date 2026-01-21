"""
选股信号模块 - 实现东方财富"知行B1选股专用"公式的七种买入信号
"""
import pandas as pd
import numpy as np
from common.indicators import (
    ref, ma, ema, sma, hhv, llv, hhvbars, count, every, exist, barslast, cross,
    kdj, rsi, bbi, trend_white_line, dage_yellow_line, short_term, long_term,
    calculate_all_indicators
)

Series = pd.Series
DataFrame = pd.DataFrame


class StockSignals:
    """选股信号生成器"""
    
    def __init__(self, df: DataFrame, stock_code: str):
        """
        初始化
        df: 包含 open, high, low, close, volume 的日线数据
        stock_code: 股票代码
        """
        self.df = calculate_all_indicators(df)
        self.stock_code = stock_code
        self.N = 20  # 近期振幅周期
        self.M = 50  # 远期振幅周期
        
        # 计算所有中间变量
        self._calculate_all()
    
    def _is_special_board(self) -> bool:
        """判断是否为科创板/创业板/北交所等特殊板块"""
        code = self.stock_code
        return (code.startswith('68') or code.startswith('30') or 
                code.startswith('4') or code.startswith('8') or code.startswith('9'))
    
    def _calculate_all(self):
        """计算所有中间指标"""
        df = self.df
        o, h, l, c, v = df['open'], df['high'], df['low'], df['close'], df['volume']
        
        # 获取已计算的指标
        k, d, j = df['K'], df['D'], df['J']
        rsi_val = df['RSI']
        趋势白线 = df['趋势白线']
        大哥黄线 = df['大哥黄线']
        短期 = df['短期']
        长期 = df['长期']
        bbi_val = df['BBI']
        
        # === 市场环境判定 ===
        # 检查是否曾经涨幅超过15%（判断是否有涨跌幅限制放宽）
        has_big_gain = exist(c / ref(c, 1) > 1.15, 200)
        is_special = self._is_special_board() or has_big_gain
        
        # 判断是否特殊板块（需要处理 Series 类型）
        is_special_val = is_special.iloc[-1] if isinstance(is_special, Series) else is_special
        self.振幅区间 = 8 if is_special_val else 5
        self.放宽系数 = 0.9 if is_special_val else 1
        
        当日振幅 = (h - l) / l * 100
        当日涨跌幅 = abs(c - ref(c, 1)) / ref(c, 1) * 100 * self.放宽系数
        上涨十字星 = (c > ref(c, 1)) & ((abs(c - o) / o * 100 * self.放宽系数) < 1.8)
        
        # === 量能形态判定 ===
        # 大绿棒判定：简化逻辑 - 检查过去40天内最大成交量日是否为绿棒（收盘<开盘 且 收盘<前收）
        # 使用向量化方法避免动态shift问题
        vday = hhvbars(v, 40)
        
        # 简化大绿棒判定：近40天最大成交量那天是否是大阴线
        # 如果是大阴线且距离近（15天内），则不是好的形态
        def check_big_green_bar(df_part, vday_val):
            """检查大绿棒"""
            if vday_val < 0 or vday_val >= len(df_part):
                return True  # 数据不足，默认OK
            idx = len(df_part) - 1 - int(vday_val)
            if idx < 1:
                return True
            c_val = df_part['close'].iloc[idx]
            o_val = df_part['open'].iloc[idx]
            c_prev = df_part['close'].iloc[idx - 1] if idx > 0 else c_val
            # 不是大绿棒：收盘>=前收 或 收盘>=开盘
            return c_val >= c_prev or c_val >= o_val
        
        # 对最后一行应用判断（选股只关心最后一天）
        last_vday = int(vday.iloc[-1]) if not pd.isna(vday.iloc[-1]) else 0
        is_not_big_green = check_big_green_bar(df, last_vday)
        big_green_far = last_vday >= 15
        
        # 创建 Series 以便后续计算
        不是大绿棒 = pd.Series([is_not_big_green] * len(df), index=df.index)
        大绿棒离得远 = pd.Series([big_green_far and not is_not_big_green] * len(df), index=df.index)
        
        缩量 = (v < hhv(v, 20) * 0.416) | (v < hhv(v, 50) / 3)
        回踩缩量 = (v < hhv(v, 20) * 0.45) | (v < hhv(v, 50) / 3)
        适当缩量 = (v < hhv(v, 20) * 0.618) | (v < hhv(v, 50) / 3)
        超缩量 = (v < hhv(v, 30) / 4) | (v < hhv(v, 50) / 6)
        
        OK棒 = 不是大绿棒 | 大绿棒离得远
        
        # === 异动与趋势判定 ===
        lown = llv(l, self.N)
        highn = hhv(h, self.N)
        近期振幅 = (highn - lown) / lown * 100
        近期异动 = (近期振幅 >= 15) | ((hhv(h, 12) - llv(l, 14)) / llv(l, 14) * 100 >= 11)
        
        lowm = llv(l, self.M)
        highm = hhv(h, self.M)
        远期振幅 = (highm - lowm) / lowm * 100
        远期异动 = 远期振幅 >= 30
        超级异动 = 近期振幅 >= 60
        
        单针下20 = ((短期 <= 20) & (长期 >= 75)) | ((长期 - 短期) >= 70)
        聚宝盆 = (count(长期 >= 75, 8) >= 6) & (count(短期 <= 70, 7) >= 4) & (count(短期 <= 50, 8) >= 1)
        双叉戟 = every(长期 >= 75, 8) & (count(短期 <= 50, 6) >= 2) & (count(短期 <= 20, 7) >= 1)
        洗盘异动 = (count(单针下20, 10) >= 2) | 聚宝盆 | 双叉戟
        
        异动 = 近期异动 | 远期异动 | 洗盘异动
        
        红肥绿瘦 = (count(c >= o, 15) > 7) | (count(c > ref(c, 1), 11) > 5)
        
        # === 趋势判定 ===
        做上涨趋势 = (趋势白线 >= 大哥黄线) & ((c >= 大哥黄线) | ((c > 大哥黄线 * 0.975) & (c > o)))
        
        强趋势股 = (every(大哥黄线 >= ref(大哥黄线, 1) * 0.999, 13) & 
                   (趋势白线 >= ref(趋势白线, 1)) & 
                   every(趋势白线 > 大哥黄线, 20) & 
                   every(趋势白线 >= ref(趋势白线, 1), 11) & 
                   红肥绿瘦)
        
        超牛股 = ((every(bbi_val >= ref(bbi_val, 1) * 0.999, 20) | (count(bbi_val >= ref(bbi_val, 1), 25) >= 23)) & 
                 ((近期振幅 >= 30) | (远期振幅 > 80)) & 
                 (barslast(cross(c, 大哥黄线)) > 12))
        
        # === 距离与回踩判定 ===
        距离白线 = abs(c - 趋势白线) / c * 100
        L距离白线 = abs(l - 趋势白线) / 趋势白线 * 100
        距离BBI = abs(c - bbi_val) / c * 100
        L距离BBI = abs(l - bbi_val) / bbi_val * 100
        距离黄线 = abs(c - 大哥黄线) / 大哥黄线 * 100
        
        回踩白线 = ((c >= 趋势白线) & (距离白线 <= 2)) | \
                  ((c < 趋势白线) & (距离白线 < 0.8)) | \
                  ((c >= bbi_val) & (距离BBI < 2.5) & (L距离BBI < 1) & (距离白线 <= 3) & (当日涨跌幅 < 1) & (c > ref(c, 1)))
        
        白线支撑 = (c >= 趋势白线) & (距离白线 < 1.5)
        强势回踩不破 = ((L距离白线 < 1) | (L距离BBI < 0.5)) & (c > 趋势白线) & (距离白线 <= 3.5)
        
        回踩黄线 = ((c >= 大哥黄线) & ((距离黄线 <= 1.5) | ((距离黄线 <= 2) & (当日涨跌幅 < 1)))) | \
                  ((c < 大哥黄线) & (距离黄线 <= 0.8))
        
        # === 七种买入信号 ===
        # 1. 超卖缩量拐头B
        self.超卖缩量拐头B = (做上涨趋势 & 
                            ((rsi_val - 15) >= ref(rsi_val, 1)) & 
                            ((ref(rsi_val, 1) < 20) | (ref(j, 1) < 14)) & 
                            (当日振幅 < (self.振幅区间 + 0.5)) & 
                            ((当日涨跌幅 < 2.3) | 上涨十字星) & 
                            OK棒 & 异动 & (c >= 大哥黄线))
        
        # 2. 超卖缩量B
        self.超卖缩量B = (做上涨趋势 & 
                        ((j < 14) | (rsi_val < 23)) & 
                        ((rsi_val + j < 55) | (j == llv(j, 20))) & 
                        (当日振幅 < self.振幅区间) & 
                        ((当日涨跌幅 < 2.5) | 上涨十字星) & 
                        OK棒 & 
                        (缩量 | (适当缩量 & (当日涨跌幅 < 1))) & 
                        异动)
        
        # 3. 原始B1
        self.原始B1 = ((趋势白线 > 大哥黄线) & 
                      (c >= 大哥黄线 * 0.99) & 
                      (大哥黄线 >= ref(大哥黄线, 1)) & 
                      ((j < 13) | (rsi_val < 21)) & 
                      ((rsi_val + j) < llv(rsi_val + j, 15) * 1.5) & 
                      适当缩量 & OK棒 & 
                      ((abs(c - o) * 100 / o < 1.5) | 超缩量 | (适当缩量 & ((距离白线 < 1.8) | (距离BBI < 1.5) | (距离黄线 < 2.8)))) & 
                      异动)
        
        # 4. 超卖超缩量B
        self.超卖超缩量B = (做上涨趋势 & 
                          ((j < 14) | (rsi_val < 23)) & 
                          (rsi_val + j < 60) & 
                          (远期振幅 >= 45) & 
                          ((当日振幅 < self.振幅区间) | (超级异动 & (当日振幅 < self.振幅区间 + 3.2) & (c > o) & (c > 趋势白线))) & 
                          (((c < o) & (v < ref(v, 1)) & (c >= 大哥黄线)) | (c >= o)) & 
                          ((当日涨跌幅 < 2) | 上涨十字星) & 
                          OK棒 & 超缩量 & 异动)
        
        # 5. 回踩白线B
        self.回踩白线B = (强趋势股 & 
                        ((j < 30) | (rsi_val < 40) | 洗盘异动) & 
                        (rsi_val + j < 70) & 
                        ((当日振幅 < self.振幅区间 + 0.5) | (距离白线 < 1) | (距离BBI < 1)) & 
                        回踩白线 & 
                        ((当日涨跌幅 < 2) | ((当日涨跌幅 < 5) & 白线支撑)) & 
                        OK棒 & 回踩缩量 & 异动 & (l <= ref(c, 1)))
        
        # 6. 回踩超级B
        self.回踩超级B = (超牛股 & 
                        ((j < 35) | (rsi_val < 45) | 洗盘异动) & 
                        (rsi_val + j < 80) & 
                        ((rsi_val + j) == llv(rsi_val + j, 25)) & 
                        (当日振幅 < self.振幅区间 + 1) & 
                        ((当日涨跌幅 < 2.5) | (距离白线 < 2)) & 
                        强势回踩不破 & OK棒 & 异动 & 适当缩量)
        
        # 7. 回踩黄线B
        self.回踩黄线B = ((趋势白线 >= 大哥黄线) & 
                        (c >= 大哥黄线 * 0.975) & 
                        ((j < 13) | (rsi_val < 18)) & 
                        回踩黄线 & OK棒 & 
                        (缩量 | (适当缩量 & ((j == llv(j, 20)) | (rsi_val == llv(rsi_val, 14))))) & 
                        (大哥黄线 >= ref(大哥黄线, 1) * 0.997) & 
                        (df['MA60'] >= ref(df['MA60'], 1)) & 
                        (近期振幅 >= 11.9) & (远期振幅 >= 19.5))
        
        # 综合信号
        self.XG = (self.超卖缩量拐头B | self.超卖缩量B | self.原始B1 | 
                   self.超卖超缩量B | self.回踩白线B | self.回踩超级B | self.回踩黄线B)
        
        # 保存用于调试
        self.近期振幅 = 近期振幅
        self.远期振幅 = 远期振幅
    
    def get_latest_signal(self) -> dict:
        """获取最新一天的信号"""
        if len(self.df) == 0:
            return {'signal': False, 'signals': []}
        
        idx = -1  # 最后一行
        
        signals = []
        if self.超卖缩量拐头B.iloc[idx]:
            signals.append('超卖缩量拐头B')
        if self.超卖缩量B.iloc[idx]:
            signals.append('超卖缩量B')
        if self.原始B1.iloc[idx]:
            signals.append('原始B1')
        if self.超卖超缩量B.iloc[idx]:
            signals.append('超卖超缩量B')
        if self.回踩白线B.iloc[idx]:
            signals.append('回踩白线B')
        if self.回踩超级B.iloc[idx]:
            signals.append('回踩超级B')
        if self.回踩黄线B.iloc[idx]:
            signals.append('回踩黄线B')
        
        return {
            'signal': self.XG.iloc[idx],
            'signals': signals,
            'code': self.stock_code,
            'close': self.df['close'].iloc[idx],
            'K': self.df['K'].iloc[idx],
            'D': self.df['D'].iloc[idx],
            'J': self.df['J'].iloc[idx],
            'RSI': self.df['RSI'].iloc[idx],
            '近期振幅': self.近期振幅.iloc[idx],
            '远期振幅': self.远期振幅.iloc[idx]
        }


def check_stock_signal(df: DataFrame, stock_code: str) -> dict:
    """检查单只股票的信号"""
    try:
        signals = StockSignals(df, stock_code)
        return signals.get_latest_signal()
    except Exception as e:
        return {'signal': False, 'signals': [], 'error': str(e)}
