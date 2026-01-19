
import akshare as ak
import pandas as pd
import random

from datetime import datetime
import os
import platform


def get_sector_flow(sector_type='行业资金流'):
    """获取板块资金流排名 (返回 Top 10 流入和 Top 10 流出)"""
    try:
        print(f"正在获取 {sector_type} 数据...")
        df = ak.stock_sector_fund_flow_rank(indicator='今日', sector_type=sector_type)
        
        target_col = None
        name_col = None
        
        # 优先寻找 "主力净流入"
        for col in df.columns:
            if "主力" in col and "净流入" in col and "净额" in col:
                target_col = col
                break
        
        # Fallback
        if not target_col:
             for col in df.columns:
                if "净流入" in col and "净额" in col and "今日" in col:
                    target_col = col
                    break

        for col in df.columns:
             if "名称" in col:
                name_col = col
                break
                
        if not target_col or not name_col:
            return None
            
        # 确保数值类型
        df['net_flow_billion'] = pd.to_numeric(df[target_col], errors='coerce') / 100000000
        
        # 排序
        top_inflow = df.sort_values(by='net_flow_billion', ascending=False).head(10)
        top_outflow = df.sort_values(by='net_flow_billion', ascending=True).head(10)
        
        return top_inflow, top_outflow, name_col, 'net_flow_billion'
        
    except Exception as e:
        print(f"获取 {sector_type} 失败: {e}")
        return None


def generate_prompt(industry_inflow, industry_outflow, output_path="results/sector_flow_image_prompt.txt"):
    """
    生成 Nano Banana Pro 优化的 AI 绘画提示词 (手绘风格)
    """
    
    # 获取数据 Top 3 Inflow (Name, Flow)
    top_in_data = []
    for i, (_, row) in enumerate(industry_inflow.head(3).iterrows()):
         val = float(row['net_flow_billion'])
         top_in_data.append({'name': row['名称'], 'flow': f"+{val:.1f}亿"})
    
    # 获取 Top 10 Outflow (Name, Flow)
    top_out_list = []
    for i, (_, row) in enumerate(industry_outflow.head(10).iterrows()):
         val = float(row['net_flow_billion'])
         top_out_list.append(f"{row['名称']} ({val:.1f}亿)")
         
    outflow_text = ", ".join(top_out_list)

    # 动态构建物体描述
    # e.g. "Center object representing [Sector]"
    
    def get_obj_desc(idx):
        if idx < len(top_in_data):
            item = top_in_data[idx]
            return item['name'], item['flow']
        return "Unknown", ""

    name_c, flow_c = get_obj_desc(0)
    name_l, flow_l = get_obj_desc(1)
    name_r, flow_r = get_obj_desc(2)

    # 随机标题库
    titles = ["今日真神", "榜一大哥", "谁在吸金", "资金去哪了", "今日封神榜", "多空大决战"]
    selected_title = random.choice(titles)

    prompt_content = f"""
(masterpiece, best quality), (vertical:1.2), (aspect ratio: 10:16), (hand drawn), (illustration), (vintage style), (surrealism)

**SUBJECT**: A surreal conceptual illustration with the title "**{selected_title}**" written at the top.

**HEADER TEXT**:
- At the very top of the image, write the text "**{selected_title}**" in **Bold Chinese Calligraphy** style. 
- The text should be large, imposing, and possibly glowing (Gold or Red).

1. **THE GIANTS (Top Inflow Sectors)**:
   Three COLOSSAL, SYMBOLIC MONUMENTS towering in the center, representing the top winning industries. (NON-HUMANOID OBJECTS)
   - **CENTER (Largest)**: A giant symbolic object representing **"{name_c}"**. It should be a physical object or structure, NOT A PERSON. 
     **Text label on it**: "{name_c}" (Black Bold) and "{flow_c}" (Small RED text next to it).
   - **LEFT**: A massive symbolic object representing **"{name_l}"**. (Physical object, non-human).
     **Text label on it**: "{name_l}" (Black Bold) and "{flow_l}" (Small RED text).
   - **RIGHT**: A massive symbolic object representing **"{name_r}"**. (Physical object, non-human).
     **Text label on it**: "{name_r}" (Black Bold) and "{flow_r}" (Small RED text).

2. **THE WORSHIPPERS (Top Outflow Sectors)**:
   In the **FOREGROUND**, a group of **LARGE**, kneeling figures (pilgrims) with their backs facing the viewer. 
   - They should be **CLOSE TO THE CAMERA** so their backs take up significant space.
   - **CRITICAL**: The text labels on their backs must be **LARGE and CLEARLY LEGIBLE**.
   - **Labels on backs**: {outflow_text}
   - (Note for Text: The outflow numbers should be in Small GREEN text if possible)


**ART STYLE**: 
- **Vintage Hand-drawn Illustration**: Warm paper texture background, ink lines, watercolor washes.
- **Atmosphere**: Epic, religious scale, slightly dystopian but artistic.
- **Colors**: Sepia, warm brown, faded red (giants), dull green/grey (worshippers).

**TEXT RENDERING**:
- Please ensure the Chinese text labels for sectors are visible.
- Font style: Hand-written Chinese calligraphy or block print.

(Optimized for Nano Banana Pro: Focus on the contrast between the giant objects and the tiny kneeling crowd.)
"""
    
    with open(output_path, "w", encoding='utf-8') as f:
        f.write(prompt_content.strip())
    
    print(f"Image Prompt saved to {output_path}")


def run_daily_analysis(date_dir=None):
    """每日定期运行的入口函数"""
    print(f"\n=== A股板块资金流向统计 ({datetime.now().strftime('%Y-%m-%d')}) ===")
    
    # 1. 获取数据
    res_industry = get_sector_flow('行业资金流')
    res_concept = get_sector_flow('概念资金流')
    
    if res_industry and res_concept:
        # 2. 打印文本表格
        inflow, outflow, name_col, flow_col = res_industry
        
        print("\n🏆 行业板块 - 主力净流入 Top 10")
        for i, (_, row) in enumerate(inflow.iterrows()):
            print(f"{i+1}. {row[name_col]:<10} {row[flow_col]:.2f}亿")

        print("\n😭 行业板块 - 主力净流出 Top 10")
        for i, (_, row) in enumerate(outflow.iterrows()):
            print(f"{i+1}. {row[name_col]:<10} {row[flow_col]:.2f}亿")
            
        # 3. 确定输出路径
        if date_dir:
            if not os.path.exists(date_dir):
                os.makedirs(date_dir, exist_ok=True)
            prompt_path = os.path.join(date_dir, "sector_flow_image_prompt.txt")
        else:
            # 默认路径
            if not os.path.exists("results"):
                os.makedirs("results", exist_ok=True)
            prompt_path = "results/sector_flow_image_prompt.txt"

        # 4. 生成提示词
        generate_prompt(inflow, outflow, output_path=prompt_path)
        
        print("✅ 板块资金流分析已完成")
    else:
        print("⚠️ 数据获取不完整，跳过板块分析")


if __name__ == "__main__":
    run_daily_analysis()
