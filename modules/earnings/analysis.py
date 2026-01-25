
"""
Analysis Logic for Earnings Module
"""
import pandas as pd

def parse_forecast_value(val_str):
    """
    Parse complex values like "10000万元-12000万元" or "1.5亿元" to float (in 100M/亿 unit).
    Default returns None if parse fails.
    """
    if not val_str or pd.isna(val_str):
        return None
    
    try:
        # Simple cleanup
        clean_str = str(val_str).replace(' ', '')
        
        # Handle ranges "A-B", take average
        if '-' in clean_str:
            parts = clean_str.split('-')
            # Extract numbers from both parts
            v1 = _extract_number(parts[0])
            v2 = _extract_number(parts[1])
            if v1 is not None and v2 is not None:
                return (v1 + v2) / 2
        else:
            return _extract_number(clean_str)
            
    except:
        return None
    return None

def _extract_number(s):
    # Detect unit
    factor = 1.0 # Default Unit ?
    
    if '万' in s:
        factor = 0.0001 # Convert 万 to 亿
    elif '亿' in s:
        factor = 1.0
        
    import re
    nums = re.findall(r"[-+]?\d*\.\d+|\d+", s)
    if nums:
        return float(nums[0]) * factor
    return None

def analyze_earnings(row):
    """
    Analyze a single row of merged earnings data.
    Returns: (Sentiment, Highlight)
    
    Input Row Columns:
    - 股票代码, 股票简称, 业绩变动, 预测数值, 业绩变动幅度, 业绩变动原因, 预告类型...
    """
    # 1. Check Forecast Type (预告类型)
    forecast_type = str(row.get('预告类型', ''))
    change_pct_str = str(row.get('业绩变动幅度', ''))
    
    sentiment = "中性"
    details = []
    
    # --- Logic 1: Forecast Type ---
    if '预增' in forecast_type or '略增' in forecast_type:
        sentiment = "利好"
        details.append(f"业绩{forecast_type}")
    elif '扭亏' in forecast_type:
        sentiment = "利好"
        details.append("扭亏为盈")
    elif '预减' in forecast_type or '略减' in forecast_type or '首亏' in forecast_type or '续亏' in forecast_type:
        sentiment = "利空"
        details.append(f"业绩{forecast_type}")
    
    # --- Logic 2: Change Magnitude ---
    # Try to parse change pct "50%~80%"
    try:
        import re
        nums = re.findall(r"[-+]?\d+", change_pct_str)
        if nums:
            # Calculate avg change
            avg_change = sum(map(float, nums)) / len(nums)
            details.append(f"变动幅度: {avg_change:.0f}%")
            
            if avg_change > 30:
                sentiment = "利好"
            elif avg_change < -30:
                sentiment = "利空"
            # If positive but small (<30%), keep Neutral or existing sentiment
            # If forecast says "Pre-increase" but change is small? Usually Pre-increase implies >0
        else:
            # If no numbers, rely on type
            pass
    except:
        pass

    # --- Logic 3: Keywords in Reason (Optional) ---
    reason = str(row.get('业绩变动原因', ''))
    if '非经常性损益' in reason:
        details.append("(含非经常性损益影响)")
        
    # --- Logic 4: Disclosure Only (No Forecast) ---
    if pd.isna(forecast_type) or forecast_type == 'nan' or not forecast_type:
        sentiment = "待披露"
        return sentiment, "等待正式年报/季报披露"

    summary = " ".join(details)
    return sentiment, summary

def analyze_df(df):
    """
    Apply analysis to the whole dataframe.
    """
    if df.empty:
        return df
        
    results = df.apply(lambda row: analyze_earnings(row), axis=1)
    
    # Unpack results
    df['sentiment'] = [r[0] for r in results]
    df['analysis_summary'] = [r[1] for r in results]
    
    return df
