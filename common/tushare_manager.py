"""
Tushare Data Manager
Prioritizes Tushare data for better stability and reliability.
"""
import os
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# --- Pandas 3.0 Compatibility Patch for Tushare ---
import pandas as pd
try:
    if int(pd.__version__.split('.')[0]) >= 3:
        # Monkey patch DataFrame.fillna and Series.fillna to support 'method' argument
        # which was removed in Pandas 3.0 but is used by Tushare
        if not hasattr(pd.DataFrame, '_original_fillna'):
            pd.DataFrame._original_fillna = pd.DataFrame.fillna

            def _fillna_compat_df(self, value=None, method=None, axis=None, inplace=False, limit=None, downcast=None):
                if method == 'ffill':
                    return self.ffill(axis=axis, inplace=inplace, limit=limit) # downcast is also removed/deprecated often
                elif method == 'bfill':
                    return self.bfill(axis=axis, inplace=inplace, limit=limit)
                else:
                    return self._original_fillna(value=value, axis=axis, inplace=inplace, limit=limit)

            pd.DataFrame.fillna = _fillna_compat_df

        if not hasattr(pd.Series, '_original_fillna'):
            pd.Series._original_fillna = pd.Series.fillna

            def _fillna_compat_series(self, value=None, method=None, axis=None, inplace=False, limit=None, downcast=None):
                if method == 'ffill':
                    return self.ffill(axis=axis, inplace=inplace, limit=limit)
                elif method == 'bfill':
                    return self.bfill(axis=axis, inplace=inplace, limit=limit)
                else:
                    return self._original_fillna(value=value, axis=axis, inplace=inplace, limit=limit)

            pd.Series.fillna = _fillna_compat_series

        print("🔧 Applied Pandas 3.0 compatibility patch for Tushare")
except Exception as e:
    print(f"⚠️ Failed to apply Pandas compatibility patch: {e}")
# --------------------------------------------------

class TushareManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TushareManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.token = os.getenv("TUSHARE_TOKEN")
        self.api = None
        self.is_ready = False

        if self.token and self.token != "your_tushare_token_here":
            try:
                import tushare as ts
                ts.set_token(self.token)
                self.api = ts.pro_api()
                self.is_ready = True
                print("✅ Tushare initialized successfully")
            except ImportError:
                print("⚠️ Tushare not installed. Please run: pip install tushare")
            except Exception as e:
                print(f"❌ Tushare initialization failed: {e}")
        else:
            print("ℹ️ Tushare token not found in .env, skipping Tushare initialization")

        self._initialized = True

    def _to_ts_code(self, code: str) -> str:
        """Convert 6-digit code to Tushare format (e.g., 000001 -> 000001.SZ)"""
        if "." in code:
            return code

        # Simple estimation logic, can be improved
        if code.startswith("6"):
            return f"{code}.SH"
        elif code.startswith("0") or code.startswith("3"):
            return f"{code}.SZ"
        elif code.startswith("8") or code.startswith("4"):
            return f"{code}.BJ"
        return code

    def _to_plain_code(self, ts_code: str) -> str:
        """Convert Tushare format to 6-digit code"""
        if "." in ts_code:
            return ts_code.split(".")[0]
        return ts_code

    def get_stock_list(self) -> Optional[pd.DataFrame]:
        """
        Get all stock list with basic info and market cap
        Returns DataFrame with columns: [code, name, market_cap, industry]
        market_cap unit: Billions (亿)
        """
        if not self.is_ready:
            return None

        try:
            # 1. Get basic info
            df_basic = self.api.stock_basic(
                exchange='',
                list_status='L',
                fields='ts_code,symbol,name,industry'
            )

            # 2. Get daily basic (for market cap) - try today, if fails try yesterday
            for days_back in range(5):
                date_str = (datetime.now() - timedelta(days=days_back)).strftime("%Y%m%d")
                try:
                    df_daily = self.api.daily_basic(
                        trade_date=date_str,
                        fields='ts_code,total_mv'
                    )
                    if df_daily is not None and not df_daily.empty:
                        break
                except Exception:
                    continue
            else:
                print("⚠️ Failed to get Tushare daily_basic (market cap) data")
                df_daily = pd.DataFrame(columns=['ts_code', 'total_mv'])

            # 3. Merge
            if df_basic is None or df_basic.empty:
                return None

            merged = pd.merge(df_basic, df_daily, on='ts_code', how='left')

            # 4. Standardize columns to match system requirement
            # total_mv in Tushare is in "Ten Thousands" (万), we need "Billions" (亿)
            # 1 亿 = 10000 万
            merged['market_cap'] = merged['total_mv'] / 10000

            result = pd.DataFrame({
                'code': merged['symbol'],
                'name': merged['name'],
                'market_cap': merged['market_cap'].fillna(0),
                'industry': merged['industry'].fillna('')
            })

            return result

        except Exception as e:
            print(f"❌ Tushare get_stock_list failed: {e}")
            return None

    def get_daily_data(self, code: str, days: int = 300) -> Optional[pd.DataFrame]:
        """
        Get daily data for a specific stock
        Returns DataFrame with columns: [date, open, high, low, close, volume]
        """
        if not self.is_ready:
            return None

        try:
            ts_code = self._to_ts_code(code)
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=days*2)).strftime("%Y%m%d") # *2 to ensure enough trading days

            import tushare as ts
            # Use pro_bar for adjusted price (qfq)
            df = ts.pro_bar(
                ts_code=ts_code,
                api=self.api,
                adj='qfq',
                start_date=start_date,
                end_date=end_date
            )

            if df is None or df.empty:
                return None

            # Rename and select columns
            # Tushare columns: trade_date, open, high, low, close, vol, etc.
            df = df.rename(columns={
                'trade_date': 'date',
                'vol': 'volume'
            })

            df = df[['date', 'open', 'high', 'low', 'close', 'volume']]
            df['date'] = pd.to_datetime(df['date'])

            # Sort by date ascending
            df = df.sort_values('date').reset_index(drop=True)

            # Limit days
            if len(df) > days:
                df = df.tail(days).reset_index(drop=True)

            return df

        except Exception as e:
            print(f"❌ Tushare get_daily_data failed for {code}: {e}")
            return None
