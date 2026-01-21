from datetime import datetime

def save_to_excel(df, filename="results/fish_basin_report.xlsx"):
    """
    Save the dataframe to an Excel file with conditional formatting.
    Red for Bullish/Positive, Green for Bearish/Negative.
    """
    if df.empty: return
    
    # Ensure directory exists
    import os
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    
    # 1. Create a Styler
    # Helper to color text
    def color_status(val):
        color = 'red' if val == 'YES' else 'green'
        return f'color: {color}'
        
    def color_pct(val):
        # val is string like "+1.23%" or "-0.5%"
        try:
            v = float(val.strip('%'))
            color = 'red' if v > 0 else 'green'
            return f'color: {color}'
        except:
            return ''

    # Apply styles
    # Note: subset needs columns to exist
    try:
        styler = df.style.map(color_status, subset=['状态'])\
                        .map(color_pct, subset=['涨幅%', '偏离率', '区间涨幅%'])

        # Highlight entire row if status changed today
        def highlight_today_row(row):
            today_str = datetime.now().strftime("%y.%m.%d")
            # 兼容可能的空格
            if row['状态变量时间'].strip() == today_str:
                return ['background-color: #FFFFCC'] * len(row) # Light Yellow
            return [''] * len(row)

        styler = styler.apply(highlight_today_row, axis=1)

                         
        # 2. Save
        styler.to_excel(filename, index=False, engine='openpyxl')
        print(f"Excel report saved to: {filename}")
        
        # 3. Post-process for column widths (Optional but nice)
        from openpyxl import load_workbook
        wb = load_workbook(filename)
        ws = wb.active
        for column in ws.columns:
            max_length = 0
            column = [cell for cell in column]
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2)
            ws.column_dimensions[column[0].column_letter].width = adjusted_width
        wb.save(filename)
        
    except Exception as e:
        print(f"Failed to save Excel: {e}")
