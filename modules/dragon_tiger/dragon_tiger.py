
import akshare as ak
import pandas as pd
import os
from datetime import datetime, timedelta
import sys


def _has_rows(df):
    return df is not None and isinstance(df, pd.DataFrame) and not df.empty


def get_dragon_tiger_data(date_str=None, max_fallback_days=5, return_used_date=False):
    """
    Fetch Dragon Tiger List data:
    1. Institutional Seat Tracking (机构席位追踪)
    2. Active Business Departments (活跃营业部)
    当目标日期无数据时，自动回退最近交易日。
    """
    if not date_str:
        date_str = datetime.now().strftime('%Y%m%d')

    try:
        base_date = datetime.strptime(date_str, "%Y%m%d")
    except ValueError:
        base_date = datetime.now()
        date_str = base_date.strftime('%Y%m%d')

    last_error = None
    for offset in range(max_fallback_days + 1):
        candidate_date = (base_date - timedelta(days=offset)).strftime('%Y%m%d')
        print(f"Fetching Dragon Tiger data for {candidate_date}...")

        df_inst = None
        df_active = None
        inst_error = None
        active_error = None

        try:
            df_inst = ak.stock_lhb_jgmmtj_em(start_date=candidate_date, end_date=candidate_date)
        except Exception as e:
            inst_error = e

        try:
            df_active = ak.stock_lhb_hyyyb_em(start_date=candidate_date, end_date=candidate_date)
        except Exception as e:
            active_error = e

        if _has_rows(df_inst) or _has_rows(df_active):
            if offset > 0:
                print(f"ℹ️ 当日无可用龙虎榜数据，回退至 {candidate_date}")
            if return_used_date:
                return df_inst, df_active, candidate_date
            return df_inst, df_active

        last_error = inst_error or active_error

    if last_error is not None:
        print(f"Error fetching Dragon Tiger data: {last_error}")
    if return_used_date:
        return None, None, date_str
    return None, None

def generate_prompt(inst_df, active_df, date_str, output_path):
    """
    Generate AI Prompt in "Vintage Paper/Hand-drawn Infographic" style
    """
    display_date = f"{date_str[4:6]}月{date_str[6:8]}日"

    # Prepare Data Text (Units: Yi / Billions)
    inst_buy_lines = []
    inst_sell_lines = []

    if inst_df is not None and 'name' in inst_df.columns:
        # Sort by Net Buy
        inst_df['net_buy'] = pd.to_numeric(inst_df['net_buy'], errors='coerce')

        # Aggregate duplicates (groupby Name) to merge multiple entries for same stock
        inst_df = inst_df.groupby('name', as_index=False)['net_buy'].sum()

        # Top 5 Buy
        top_buy = inst_df.sort_values(by='net_buy', ascending=False).head(5)
        for _, row in top_buy.iterrows():
             val = row['net_buy'] / 100000000 # Yuan -> Yi
             inst_buy_lines.append(f"{row['name']} (+{val:.2f}亿)")

        # Top 5 Sell (if negative)
        top_sell = inst_df.sort_values(by='net_buy', ascending=True).head(5)
        for _, row in top_sell.iterrows():
             val = row['net_buy'] / 100000000 # Yuan -> Yi
             if val < 0:
                 inst_sell_lines.append(f"{row['name']} ({val:.2f}亿)")

    inst_text = ", ".join(inst_buy_lines)
    sell_text = ", ".join(inst_sell_lines)

    active_lines = []
    if active_df is not None and 'dept_name' in active_df.columns:
         # Ensure numeric
         if 'buy_total' in active_df.columns:
             active_df['buy_total'] = pd.to_numeric(active_df['buy_total'], errors='coerce')
         if 'net_total' in active_df.columns:
             active_df['net_total'] = pd.to_numeric(active_df['net_total'], errors='coerce')

         top = active_df.sort_values(by='buy_total', ascending=False).head(8) # Show top 8
         for i, (_, row) in enumerate(top.iterrows()):
             name = row['dept_name']
             # Cleanup name
             name = name.replace("证券股份有限公司", "").replace("股份有限公司", "").replace("有限责任公司", "")
             if len(name) > 10: name = name[:9] + "."

             val_buy = row['buy_total'] / 100000000 # Yuan -> Yi

             # Enrich with Net and Stock
             extra_info = ""
             if 'net_total' in row and pd.notnull(row['net_total']):
                 val_net = row['net_total'] / 100000000
                 extra_info += f", 净 {val_net:+.1f}亿"

             if 'stocks' in row and pd.notnull(row['stocks']):
                 # stocks might be "StockA|StockB" or just string
                 s = str(row['stocks']).split('|')[0] # Take first one
                 if s and s != 'nan':
                     extra_info += f", 主攻: {s}"

             active_lines.append(f"{i+1}. {name} (买 {val_buy:.1f}亿{extra_info})")

    active_text = ", ".join(active_lines)

    prompt_content = f"""
Hand-drawn infographic poster, Chinese A-share Dragon Tiger List (龙虎榜), {display_date}.

**Style**: Warm cream paper texture (#F5E6C8), vintage notebook aesthetic, handwritten Chinese fonts.

**Visual Layout**:
1. **Top Section**: "Institutional Funds Divergence" (机构资金分歧)
   - **Chart Type**: **Diverging Bar Chart** (Center axis).
   - **Left Side (Red)**: Top Net Buy Institutions.
   - **Right Side (Green)**: Top Net Sell Institutions.
   - **Data**:
     - BUY: {inst_text}
     - SELL: {sell_text}

2. **Bottom Section**: "Active Hot Money Seats" (活跃游资)
   - **List Style**: Ranked list with Medal/Badge icons for Top 3.
   - **Content**: {active_text}
   - **Details**: Shows Buy Amount (买), Net Amount (净), and Top Focus Stock (主攻).
   - **Color**: Gold/Black text for names, Red for money.

**Title**: "{display_date} 龙虎榜资金动向" (Bold Calligraphy).
**Background**: Paper texture with ink splatter effects. Professional financial analysis atmosphere.

--ar 9:16 --style raw --v 6
"""
    with open(output_path, "w", encoding='utf-8') as f:
        f.write(prompt_content.strip())
    print(f"AI Prompt saved to {output_path} (Units: Billions, Rich Layout)")


def run(date_dir=None):
    print(f"\n=== 龙虎榜分析 (Dragon Tiger) ===")

    if not date_dir:
        today_dir = datetime.now().strftime('%Y%m%d')
        date_dir = os.path.join("results", today_dir)

    if not os.path.exists(date_dir):
        os.makedirs(date_dir, exist_ok=True)

    # Use the date from the directory path if possible, or today
    # Assuming date_dir is like "results/20260210"
    try:
        date_str = os.path.basename(date_dir)
        if not (len(date_str) == 8 and date_str.isdigit()):
            date_str = datetime.now().strftime('%Y%m%d')
    except:
        date_str = datetime.now().strftime('%Y%m%d')

    inst_df, active_df, used_date = get_dragon_tiger_data(date_str, return_used_date=True)

    if inst_df is not None or active_df is not None:
        # Generate AI Prompt
        prompt_dir = os.path.join(date_dir, "AI提示词")
        os.makedirs(prompt_dir, exist_ok=True)
        prompt_path = os.path.join(prompt_dir, "龙虎榜_Prompt.txt")

        # Standardize columns again for prompt gen if needed
        # (draw function did rename in local scope, so we might need to do it again or pass the modified df)
        # To be safe, just do a quick rename if cols missing
        if inst_df is not None and '名称' in inst_df.columns:
             inst_df = inst_df.rename(columns={'名称': 'name', '机构买入净额': 'net_buy'})
        if active_df is not None and '营业部名称' in active_df.columns:
             active_df = active_df.rename(columns={
                 '营业部名称': 'dept_name',
                 '买入总金额': 'buy_total',
                 '总买卖净额': 'net_total',
                 '买入股票': 'stocks'
             })

        # Ensure numeric
        if inst_df is not None and 'net_buy' in inst_df.columns:
            inst_df['net_buy'] = pd.to_numeric(inst_df['net_buy'], errors='coerce')
        if active_df is not None and 'buy_total' in active_df.columns:
             active_df['buy_total'] = pd.to_numeric(active_df['buy_total'], errors='coerce')

        generate_prompt(inst_df, active_df, used_date, prompt_path)

        return True
    else:
        print("未获取到龙虎榜数据")
        return False

if __name__ == "__main__":
    run()
